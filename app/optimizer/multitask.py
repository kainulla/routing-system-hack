"""Multitask optimization: group tasks, compute TSP within groups."""
import numpy as np

from app.api.schemas import MultitaskRequest, MultitaskResponse
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
    max_detour = req.constraints.max_detour_ratio if req.constraints and req.constraints.max_detour_ratio else settings.DETOUR_RATIO_MAX

    # Resolve task_ids to task objects and their destination nodes
    task_nodes: list[tuple[str, int]] = []  # (task_id, node_id)
    for tid in req.task_ids:
        try:
            task_obj = repo.get_task_by_id(tid)
        except Exception:
            repo.session.rollback()
            task_obj = None
        if not task_obj:
            # Treat task_id as a well UWI directly
            well = repo.get_well_by_uwi(tid)
            if well and well.longitude is not None and well.latitude is not None:
                node, _ = road_graph.snap_to_node(well.longitude, well.latitude)
                task_nodes.append((tid, node))
            continue
        well = repo.get_well_by_uwi(task_obj.destination_uwi)
        if not well or well.longitude is None or well.latitude is None:
            continue
        node, _ = road_graph.snap_to_node(well.longitude, well.latitude)
        task_nodes.append((tid, node))

    if not task_nodes:
        return MultitaskResponse(
            groups=[],
            strategy_summary="Задачи не найдены",
            total_distance_km=0,
            total_time_minutes=0,
            baseline_distance_km=0,
            baseline_time_minutes=0,
            savings_percent=0,
            reason="Не удалось найти указанные задачи или их точки назначения",
        )

    # Pick a reference vehicle (first compatible or first available)
    try:
        first_task = repo.get_task_by_id(req.task_ids[0])
    except Exception:
        repo.session.rollback()
        first_task = None
    candidates = fleet.get_compatible_vehicles(first_task.task_type) if first_task else []
    if not candidates:
        candidates = list(fleet.vehicles.values())
    if not candidates:
        return MultitaskResponse(
            groups=[req.task_ids],
            strategy_summary="Нет доступных ТС, все задачи в одной группе",
            total_distance_km=0,
            total_time_minutes=0,
            baseline_distance_km=0,
            baseline_time_minutes=0,
            savings_percent=0,
            reason="Нет доступных транспортных средств",
        )

    vehicle = candidates[0]
    vehicle_node = vehicle.nearest_node

    all_nodes = [vehicle_node] + [tn[1] for tn in task_nodes]
    dist_matrix = path_service.compute_distance_matrix(all_nodes, all_nodes)

    # Baseline: individual trips from vehicle to each task
    n_tasks = len(task_nodes)
    baseline_total = 0.0
    for i in range(n_tasks):
        d = dist_matrix[0, i + 1]
        if np.isfinite(d):
            baseline_total += d

    # Greedy clustering with detour ratio constraint
    assigned = [False] * n_tasks
    groups: list[list[str]] = []

    while not all(assigned):
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

        for i in range(n_tasks):
            if assigned[i]:
                continue
            trial = cluster + [i]
            trial_nodes_idx = [0] + [t + 1 for t in trial]

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

        ordered_task_ids = []
        for step in tour[1:]:
            orig_task_idx = cluster[step - 1] if step > 0 else 0
            ordered_task_ids.append(task_nodes[orig_task_idx][0])

        groups.append(ordered_task_ids)

    # Compute optimized total
    optimized_total = 0.0
    for group in groups:
        group_nodes = [vehicle_node]
        for tid in group:
            for tn_id, tn_node in task_nodes:
                if tn_id == tid:
                    group_nodes.append(tn_node)
                    break
        for k in range(len(group_nodes) - 1):
            si = all_nodes.index(group_nodes[k])
            ei = all_nodes.index(group_nodes[k + 1])
            d = dist_matrix[si, ei]
            if np.isfinite(d):
                optimized_total += d

    speed_kmh = settings.AVG_SPEED_KMH
    savings = 0.0
    if baseline_total > 0:
        savings = round((1 - optimized_total / baseline_total) * 100, 1)

    n_groups = len(groups)
    strategy = f"Задачи сгруппированы в {n_groups} маршрут(ов) с учётом ограничения объезда {max_detour:.1f}x"
    reason_parts = [
        f"Оптимизировано {n_tasks} задач",
        f"экономия {max(savings, 0):.1f}%",
        f"базовый пробег {baseline_total/1000:.1f} км",
        f"оптимизированный {optimized_total/1000:.1f} км",
    ]

    return MultitaskResponse(
        groups=groups,
        strategy_summary=strategy,
        total_distance_km=round(optimized_total / 1000, 2),
        total_time_minutes=round((optimized_total / 1000) / speed_kmh * 60, 1),
        baseline_distance_km=round(baseline_total / 1000, 2),
        baseline_time_minutes=round((baseline_total / 1000) / speed_kmh * 60, 1),
        savings_percent=max(savings, 0),
        reason="; ".join(reason_parts),
    )
