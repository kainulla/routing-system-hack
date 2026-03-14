"""FastAPI route definitions."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.api.schemas import (
    RecommendationRequest, RecommendationResponse,
    RouteRequest, RouteResponse, RouteFrom, RouteTo,
    MultitaskRequest, MultitaskResponse,
    HealthResponse,
)
from app.optimizer.recommender import recommend_vehicles
from app.optimizer.router import compute_route
from app.optimizer.multitask import optimize_multitask
from app.viz.map_builder import build_route_map

router = APIRouter()


@router.get("/api/tasks")
def list_tasks(request: Request):
    state = request.app.state
    tasks = state.repo.get_tasks()
    return [
        {
            "task_id": t.task_id,
            "task_type": t.task_type,
            "priority": t.priority,
            "destination_uwi": t.destination_uwi,
            "planned_start": t.planned_start.isoformat(),
            "planned_duration_hours": t.planned_duration_hours,
            "shift": t.shift,
            "start_day": t.start_day.isoformat() if t.start_day else None,
            "assigned_vehicle": t.assigned_vehicle,
            "status": t.status,
        }
        for t in tasks
    ]


@router.get("/api/vehicles")
def list_vehicles(request: Request):
    state = request.app.state
    return [
        {
            "wialon_id": v.wialon_id,
            "name": v.name,
            "vehicle_type": v.vehicle_type,
            "lon": v.lon,
            "lat": v.lat,
            "compatible_tasks": v.compatible_tasks,
        }
        for v in state.fleet.vehicles.values()
    ]


@router.get("/api/wells")
def list_wells(request: Request):
    state = request.app.state
    wells = state.repo.get_wells()
    return [
        {
            "uwi": w.uwi,
            "well_name": w.well_name,
            "longitude": w.longitude,
            "latitude": w.latitude,
        }
        for w in wells
    ]


@router.get("/health", response_model=HealthResponse)
def health_check(request: Request):
    state = request.app.state
    return HealthResponse(
        status="ok",
        nodes=state.road_graph.num_nodes,
        edges=state.road_graph.num_edges,
        vehicles=len(state.fleet.vehicles),
        wells=state.well_count,
    )


@router.post("/api/recommendations", response_model=RecommendationResponse)
def get_recommendations(req: RecommendationRequest, request: Request):
    state = request.app.state
    result = recommend_vehicles(
        req=req,
        repo=state.repo,
        road_graph=state.road_graph,
        fleet=state.fleet,
        path_service=state.path_service,
    )
    if not result.units:
        raise HTTPException(status_code=404, detail="No suitable vehicles found")
    return result


@router.post("/api/route")
async def get_route(request: Request):
    state = request.app.state
    body = await request.json()
    # Handle "from" key (reserved word in Python)
    from_data = body.get("from", body.get("from_point", {}))
    to_data = body.get("to", {})
    req = RouteRequest(
        from_point=RouteFrom(**from_data),
        to=RouteTo(**to_data),
    )
    result = compute_route(
        req=req,
        road_graph=state.road_graph,
        path_service=state.path_service,
        repo=state.repo,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="No path found between points")
    return result


@router.post("/api/multitask", response_model=MultitaskResponse)
def get_multitask(req: MultitaskRequest, request: Request):
    state = request.app.state
    result = optimize_multitask(
        req=req,
        repo=state.repo,
        road_graph=state.road_graph,
        fleet=state.fleet,
        path_service=state.path_service,
    )
    return result


@router.get("/api/viz/route", response_class=HTMLResponse)
def viz_route(request: Request):
    state = request.app.state
    html = build_route_map(state.road_graph, state.fleet, state.repo)
    return HTMLResponse(content=html)
