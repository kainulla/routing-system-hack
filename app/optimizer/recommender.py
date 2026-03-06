"""Vehicle recommendation logic for a single task."""
from app.api.schemas import RecommendationRequest, RecommendationResponse, ScoredVehicle
from app.config import settings
from app.db.repository import SQLAlchemyRepository
from app.fleet.state import FleetState
from app.graph.loader import RoadGraph
from app.graph.shortest_path import ShortestPathService
from app.optimizer.scoring import compute_score


def recommend_vehicles(
    req: RecommendationRequest,
    repo: SQLAlchemyRepository,
    road_graph: RoadGraph,
    fleet: FleetState,
    path_service: ShortestPathService,
) -> RecommendationResponse:
    well = repo.get_well_by_uwi(req.destination_uwi)
    if not well:
        return RecommendationResponse(
            task_id=req.task_id,
            destination_uwi=req.destination_uwi,
            recommendations=[],
        )

    dest_node = well.nearest_node
    if dest_node is None:
        dest_node, _ = road_graph.snap_to_node(well.lon, well.lat)

    task_obj = repo.get_task_by_id(req.task_id)
    task_type = task_obj.task_type if task_obj else "transport_fluid"

    candidates = fleet.get_compatible_vehicles(task_type)
    if not candidates:
        candidates = list(fleet.vehicles.values())

    scored = []
    speed_kmh = settings.AVG_SPEED_KMH

    for v in candidates:
        path = path_service.find_path(v.nearest_node, dest_node)
        if path is None:
            continue

        eta_min = (path.distance_m / 1000) / speed_kmh * 60
        is_compat = task_type in v.compatible_tasks

        score, reason = compute_score(
            distance_m=path.distance_m,
            eta_minutes=eta_min,
            priority=req.priority,
            is_compatible=is_compat,
            free_at=v.free_at,
            planned_start=req.planned_start,
        )

        scored.append(ScoredVehicle(
            vehicle_id=v.vehicle_id,
            vehicle_name=v.vehicle_name,
            vehicle_type=v.vehicle_type,
            score=score,
            distance_m=round(path.distance_m, 2),
            eta_minutes=round(eta_min, 1),
            reason=reason,
        ))

    scored.sort(key=lambda x: x.score, reverse=True)

    return RecommendationResponse(
        task_id=req.task_id,
        destination_uwi=req.destination_uwi,
        recommendations=scored[:3],
    )
