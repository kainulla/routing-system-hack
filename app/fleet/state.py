"""Vehicle fleet state management."""
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.db.repository import SQLAlchemyRepository
from app.graph.loader import RoadGraph


# Parse vehicle type from nm field (e.g., "АЦН-001" -> "ACN")
TYPE_MAP_RU = {
    "АЦН": "ACN",
    "ЦА": "CA",
    "АПШ": "APSH",
    "АДПМ": "ADPM",
    "ППУ": "PPU",
}


def parse_vehicle_type(nm: str) -> str:
    """Extract vehicle type from name like 'АЦН-001'."""
    for ru_prefix, eng_type in TYPE_MAP_RU.items():
        if nm.startswith(ru_prefix):
            return eng_type
    return "UNKNOWN"


@dataclass
class VehicleState:
    wialon_id: int
    name: str
    vehicle_type: str
    lon: float
    lat: float
    nearest_node: int
    snap_distance_m: float
    free_at: datetime
    compatible_tasks: list[str] = field(default_factory=list)


class FleetState:
    def __init__(self):
        self.vehicles: dict[int, VehicleState] = {}
        self._compat_map: dict[str, list[str]] = {}

    def load(self, repo: SQLAlchemyRepository, road_graph: RoadGraph):
        compat_rows = repo.get_compatibility()
        for c in compat_rows:
            if c.compatible:
                self._compat_map.setdefault(c.vehicle_type, []).append(c.task_type)

        snapshots = repo.get_latest_snapshot()
        tasks = repo.get_tasks()

        assigned_end: dict[str, datetime] = {}
        for t in tasks:
            if t.assigned_vehicle and t.status in ("assigned", "in_progress"):
                end_time = t.planned_start + timedelta(hours=t.planned_duration_hours)
                if t.assigned_vehicle not in assigned_end or end_time > assigned_end[t.assigned_vehicle]:
                    assigned_end[t.assigned_vehicle] = end_time

        for snap in snapshots:
            lon = snap.pos_x
            lat = snap.pos_y
            node_id, snap_dist = road_graph.snap_to_node(lon, lat)
            vehicle_type = parse_vehicle_type(snap.nm)
            ts = datetime.fromtimestamp(snap.pos_t)
            free_at = assigned_end.get(str(snap.wialon_id), ts)
            compat = self._compat_map.get(vehicle_type, [])

            self.vehicles[snap.wialon_id] = VehicleState(
                wialon_id=snap.wialon_id,
                name=snap.nm,
                vehicle_type=vehicle_type,
                lon=lon,
                lat=lat,
                nearest_node=node_id,
                snap_distance_m=snap_dist,
                free_at=free_at,
                compatible_tasks=compat,
            )

    def get_compatible_vehicles(self, task_type: str) -> list[VehicleState]:
        return [
            v for v in self.vehicles.values()
            if task_type in v.compatible_tasks
        ]

    def get_vehicle(self, wialon_id: int) -> VehicleState | None:
        return self.vehicles.get(wialon_id)
