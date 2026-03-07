"""Tests for fleet state."""
from app.fleet.state import VehicleState
from datetime import datetime


def test_vehicle_state_creation():
    v = VehicleState(
        vehicle_id="V-001",
        vehicle_name="ACN-001",
        vehicle_type="ACN",
        lon=68.1,
        lat=51.6,
        nearest_node=42,
        snap_distance_m=15.0,
        speed=30.0,
        free_at=datetime(2025, 2, 20, 8, 0),
        compatible_tasks=["transport_fluid", "steam_injection"],
    )
    assert v.vehicle_id == "V-001"
    assert "transport_fluid" in v.compatible_tasks
    assert v.nearest_node == 42
