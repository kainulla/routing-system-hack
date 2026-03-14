"""Single route computation."""
from app.api.schemas import RouteRequest, RouteResponse
from app.config import settings
from app.db.repository import SQLAlchemyRepository
from app.graph.loader import RoadGraph
from app.graph.shortest_path import ShortestPathService


def compute_route(
    req: RouteRequest,
    road_graph: RoadGraph,
    path_service: ShortestPathService,
    repo: SQLAlchemyRepository | None = None,
) -> RouteResponse | None:
    from_node, _ = road_graph.snap_to_node(req.from_point.lon, req.from_point.lat)

    to_lon = req.to.lon
    to_lat = req.to.lat
    if (to_lon is None or to_lat is None) and req.to.uwi and repo:
        well = repo.get_well_by_uwi(req.to.uwi)
        if well and well.longitude is not None and well.latitude is not None:
            to_lon = well.longitude
            to_lat = well.latitude
    if to_lon is None or to_lat is None:
        return None
    to_node, _ = road_graph.snap_to_node(to_lon, to_lat)

    path = path_service.find_path(from_node, to_node)
    if path is None:
        return None

    speed_kmh = settings.AVG_SPEED_KMH
    time_min = (path.distance_m / 1000) / speed_kmh * 60

    return RouteResponse(
        distance_km=round(path.distance_m / 1000, 2),
        time_minutes=round(time_min, 1),
        nodes=path.nodes,
        coords=[[c[0], c[1]] for c in path.coords],
    )
