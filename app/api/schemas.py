"""Pydantic request/response models aligned with official spec."""
from datetime import datetime
from pydantic import BaseModel


# --- Recommendation ---
class RecommendationRequest(BaseModel):
    task_id: str
    priority: str
    destination_uwi: str
    planned_start: datetime
    planned_duration_hours: float


class ScoredUnit(BaseModel):
    wialon_id: int
    name: str
    eta_minutes: float
    distance_km: float
    score: float
    reason: str


class RecommendationResponse(BaseModel):
    task_id: str
    destination_uwi: str
    units: list[ScoredUnit]


# --- Route ---
class RouteFrom(BaseModel):
    wialon_id: int | None = None
    lon: float
    lat: float


class RouteTo(BaseModel):
    uwi: str | None = None
    lon: float | None = None
    lat: float | None = None


class RouteRequest(BaseModel):
    from_point: RouteFrom  # aliased as "from" in JSON
    to: RouteTo

    model_config = {"populate_by_name": True}

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        if isinstance(obj, dict) and "from" in obj:
            obj = {**obj, "from_point": obj.pop("from")}
        return super().model_validate(obj, *args, **kwargs)


class RouteResponse(BaseModel):
    distance_km: float
    time_minutes: float
    nodes: list[int]
    coords: list[list[float]]


# --- Multitask ---
class MultitaskConstraints(BaseModel):
    max_total_time_minutes: float | None = None
    max_detour_ratio: float | None = None


class MultitaskRequest(BaseModel):
    task_ids: list[str]
    constraints: MultitaskConstraints | None = None


class MultitaskResponse(BaseModel):
    groups: list[list[str]]
    strategy_summary: str
    total_distance_km: float
    total_time_minutes: float
    baseline_distance_km: float
    baseline_time_minutes: float
    savings_percent: float
    reason: str


# --- Health ---
class HealthResponse(BaseModel):
    status: str
    nodes: int
    edges: int
    vehicles: int
    wells: int
