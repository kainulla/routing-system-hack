"""Single route computation."""
from app.api.schemas import RouteRequest, RouteResponse
from app.config import settings
from app.graph.loader import RoadGraph
from app.graph.shortest_path import ShortestPathService


def compute_route(
    req: RouteRequest,
    road_graph: RoadGraph,
    path_service: ShortestPathService,
) -> RouteResponse | None:
    from_node, _ = road_graph.snap_to_node(req.from_lon, req.from_lat)
    to_node, _ = road_graph.snap_to_node(req.to_lon, req.to_lat)

    path = path_service.find_path(from_node, to_node)
    if path is None:
        return None

    speed_kmh = settings.AVG_SPEED_KMH
    duration_min = (path.distance_m / 1000) / speed_kmh * 60

    return RouteResponse(
        distance_m=path.distance_m,
        duration_minutes=round(duration_min, 1),
        path_coords=[[c[0], c[1]] for c in path.coords],
        from_node=from_node,
        to_node=to_node,
    )
