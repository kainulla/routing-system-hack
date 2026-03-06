"""Vehicle fleet state management."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.db.repository import SQLAlchemyRepository
from app.graph.loader import RoadGraph


@dataclass
class VehicleState:
    vehicle_id: str
    vehicle_name: str
    vehicle_type: str
    lon: float
    lat: float
    nearest_node: int
    snap_distance_m: float
    speed: float
    free_at: datetime
    compatible_tasks: list[str] = field(default_factory=list)


class FleetState:
    def __init__(self):
        self.vehicles: dict[str, VehicleState] = {}
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
                end_time = t.planned_start + timedelta(hours=t.duration_hours)
                if t.assigned_vehicle not in assigned_end or end_time > assigned_end[t.assigned_vehicle]:
                    assigned_end[t.assigned_vehicle] = end_time

        for snap in snapshots:
            node_id, snap_dist = road_graph.snap_to_node(snap.lon, snap.lat)
            free_at = assigned_end.get(snap.vehicle_id, snap.timestamp)
            compat = self._compat_map.get(snap.vehicle_type, [])

            self.vehicles[snap.vehicle_id] = VehicleState(
                vehicle_id=snap.vehicle_id,
                vehicle_name=snap.vehicle_name,
                vehicle_type=snap.vehicle_type,
                lon=snap.lon,
                lat=snap.lat,
                nearest_node=node_id,
                snap_distance_m=snap_dist,
                speed=snap.speed or 0,
                free_at=free_at,
                compatible_tasks=compat,
            )

    def get_compatible_vehicles(self, task_type: str) -> list[VehicleState]:
        return [
            v for v in self.vehicles.values()
            if task_type in v.compatible_tasks
        ]

    def get_vehicle(self, vehicle_id: str) -> VehicleState | None:
        return self.vehicles.get(vehicle_id)
