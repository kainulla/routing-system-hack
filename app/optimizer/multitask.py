"""Multitask optimization: group tasks, compute TSP within groups."""
import numpy as np

from app.api.schemas import (
    MultitaskRequest, MultitaskResponse, TaskGroup, TaskStop,
)
from app.config import settings
from app.db.repository import SQLAlchemyRepository
from app.fleet.state import FleetState
from app.graph.loader import RoadGraph
from app.graph.shortest_path import ShortestPathService


def _solve_tsp_greedy(dist_matrix: np.ndarray, start_idx: int = 0) -> list[int]:
    """Greedy nearest-neighbor TSP."""
    n = dist_matrix.shape[0]
    if n <= 1:
        return list(range(n))
    visited = [False] * n
    tour = [start_idx]
    visited[start_idx] = True

    for _ in range(n - 1):
        current = tour[-1]
        best_next = -1
        best_dist = np.inf
        for j in range(n):
            if not visited[j] and dist_matrix[current, j] < best_dist:
                best_dist = dist_matrix[current, j]
                best_next = j
        if best_next == -1:
            break
        tour.append(best_next)
        visited[best_next] = True
    return tour


def _try_or_tools_tsp(dist_matrix: np.ndarray) -> list[int] | None:
    """Attempt OR-Tools TSP if available. Returns ordered indices or None."""
    try:
        from ortools.constraint_solver import routing_enums_pb2, pywrapcp

        n = dist_matrix.shape[0]
        if n <= 2:
            return None

        int_matrix = (dist_matrix * 100).astype(int)

        manager = pywrapcp.RoutingIndexManager(n, 1, 0)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int_matrix[from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = 2

        solution = routing.SolveWithParameters(search_parameters)
        if not solution:
            return None

        tour = []
        index = routing.Start(0)
        while not routing.IsEnd(index):
            tour.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))
        return tour
    except Exception:
        return None


def optimize_multitask(
    req: MultitaskRequest,
    repo: SQLAlchemyRepository,
    road_graph: RoadGraph,
    fleet: FleetState,
    path_service: ShortestPathService,
) -> MultitaskResponse:
    vehicle = fleet.get_vehicle(req.vehicle_id)
    if not vehicle:
        return MultitaskResponse(
            vehicle_id=req.vehicle_id,
            groups=[],
            baseline_total_m=0,
            optimized_total_m=0,
            savings_percent=0,
        )

    # Resolve task destinations to nodes
    task_nodes: list[tuple[str, str, int]] = []  # (task_id, uwi, node_id)
    for t in req.tasks:
        well = repo.get_well_by_uwi(t.destination_uwi)
        if well:
            node = well.nearest_node
            if node is None:
                node, _ = road_graph.snap_to_node(well.lon, well.lat)
            task_nodes.append((t.task_id, t.destination_uwi, node))

    if not task_nodes:
        return MultitaskResponse(
            vehicle_id=req.vehicle_id,
            groups=[],
            baseline_total_m=0,
            optimized_total_m=0,
            savings_percent=0,
        )

    vehicle_node = vehicle.nearest_node
    all_nodes = [vehicle_node] + [tn[2] for tn in task_nodes]

    # Compute pairwise distance matrix
    dist_matrix = path_service.compute_distance_matrix(all_nodes, all_nodes)

    # Greedy clustering with detour ratio constraint
    max_detour = settings.DETOUR_RATIO_MAX
    n_tasks = len(task_nodes)
    assigned = [False] * n_tasks
    groups: list[TaskGroup] = []
    group_id = 0

    # Baseline: individual trips from vehicle to each task
    baseline_total = 0.0
    for i in range(n_tasks):
        d = dist_matrix[0, i + 1]
        if np.isfinite(d):
            baseline_total += d

    while not all(assigned):
        # Find next unassigned task closest to vehicle
        best_idx = -1
        best_dist = np.inf
        for i in range(n_tasks):
            if not assigned[i] and dist_matrix[0, i + 1] < best_dist:
                best_dist = dist_matrix[0, i + 1]
                best_idx = i
        if best_idx == -1:
            break

        cluster = [best_idx]
        assigned[best_idx] = True

        # Try adding more tasks to this cluster
        for i in range(n_tasks):
            if assigned[i]:
                continue
            # Check if adding this task keeps detour ratio acceptable
            trial = cluster + [i]
            trial_nodes_idx = [0] + [t + 1 for t in trial]

            # Compute simple chain distance
            sub_matrix = dist_matrix[np.ix_(trial_nodes_idx, trial_nodes_idx)]
            tour = _try_or_tools_tsp(sub_matrix)
            if tour is None:
                tour = _solve_tsp_greedy(sub_matrix)

            chain_dist = sum(
                sub_matrix[tour[k], tour[k + 1]] for k in range(len(tour) - 1)
            )
            direct_sum = sum(dist_matrix[0, t + 1] for t in trial)

            if np.isfinite(chain_dist) and np.isfinite(direct_sum) and direct_sum > 0:
                ratio = chain_dist / direct_sum
                if ratio <= max_detour:
                    cluster.append(i)
                    assigned[i] = True

        # Build optimized route for this cluster
        cluster_node_indices = [0] + [c + 1 for c in cluster]
        sub_matrix = dist_matrix[np.ix_(cluster_node_indices, cluster_node_indices)]
        tour = _try_or_tools_tsp(sub_matrix)
        if tour is None:
            tour = _solve_tsp_greedy(sub_matrix)

        stops = []
        cumulative = 0.0
        prev_sub = tour[0]  # vehicle position in sub-matrix
        for step in tour[1:]:
            seg_dist = sub_matrix[prev_sub, step]
            if not np.isfinite(seg_dist):
                seg_dist = 0
            cumulative += seg_dist
            # Map sub-matrix index back to task
            orig_task_idx = cluster[step - 1] if step > 0 else 0
            tn = task_nodes[orig_task_idx]
            stops.append(TaskStop(
                task_id=tn[0],
                destination_uwi=tn[1],
                distance_from_prev_m=round(seg_dist, 2),
                cumulative_distance_m=round(cumulative, 2),
            ))
            prev_sub = step

        speed_kmh = settings.AVG_SPEED_KMH
        total_dist = cumulative
        duration_min = (total_dist / 1000) / speed_kmh * 60

        groups.append(TaskGroup(
            group_id=group_id,
            vehicle_id=req.vehicle_id,
            stops=stops,
            total_distance_m=round(total_dist, 2),
            total_duration_minutes=round(duration_min, 1),
        ))
        group_id += 1

    optimized_total = sum(g.total_distance_m for g in groups)
    savings = 0.0
    if baseline_total > 0:
        savings = round((1 - optimized_total / baseline_total) * 100, 1)

    return MultitaskResponse(
        vehicle_id=req.vehicle_id,
        groups=groups,
        baseline_total_m=round(baseline_total, 2),
        optimized_total_m=round(optimized_total, 2),
        savings_percent=max(savings, 0),
    )
