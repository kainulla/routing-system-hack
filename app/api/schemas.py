"""Pydantic request/response models."""
from datetime import datetime
from pydantic import BaseModel


# --- Recommendation ---
class RecommendationRequest(BaseModel):
    task_id: str
    priority: str
    destination_uwi: str
    planned_start: datetime
    duration_hours: float


class ScoredVehicle(BaseModel):
    vehicle_id: str
    vehicle_name: str
    vehicle_type: str
    score: float
    distance_m: float
    eta_minutes: float
    reason: str


class RecommendationResponse(BaseModel):
    task_id: str
    destination_uwi: str
    recommendations: list[ScoredVehicle]


# --- Route ---
class RouteRequest(BaseModel):
    from_lon: float
    from_lat: float
    to_lon: float
    to_lat: float


class RouteResponse(BaseModel):
    distance_m: float
    duration_minutes: float
    path_coords: list[list[float]]
    from_node: int
    to_node: int


# --- Multitask ---
class TaskInput(BaseModel):
    task_id: str
    destination_uwi: str
    priority: str
    duration_hours: float


class MultitaskRequest(BaseModel):
    vehicle_id: str
    tasks: list[TaskInput]


class TaskStop(BaseModel):
    task_id: str
    destination_uwi: str
    distance_from_prev_m: float
    cumulative_distance_m: float


class TaskGroup(BaseModel):
    group_id: int
    vehicle_id: str
    stops: list[TaskStop]
    total_distance_m: float
    total_duration_minutes: float


class MultitaskResponse(BaseModel):
    vehicle_id: str
    groups: list[TaskGroup]
    baseline_total_m: float
    optimized_total_m: float
    savings_percent: float


# --- Health ---
class HealthResponse(BaseModel):
    status: str
    nodes: int
    edges: int
    vehicles: int
    wells: int
