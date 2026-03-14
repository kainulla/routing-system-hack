"""Tests for fleet state."""
from app.fleet.state import VehicleState, parse_vehicle_type
from datetime import datetime


def test_vehicle_state_creation():
    v = VehicleState(
        wialon_id=1001,
        name="АЦН-001",
        vehicle_type="ACN",
        lon=68.1,
        lat=51.6,
        nearest_node=42,
        snap_distance_m=15.0,
        free_at=datetime(2025, 2, 20, 8, 0),
        compatible_tasks=["transport_fluid", "steam_injection"],
    )
    assert v.wialon_id == 1001
    assert "transport_fluid" in v.compatible_tasks
    assert v.nearest_node == 42


def test_parse_vehicle_type():
    assert parse_vehicle_type("АЦН-001") == "ACN"
    assert parse_vehicle_type("ЦА-005") == "CA"
    assert parse_vehicle_type("АПШ-010") == "APSH"
    assert parse_vehicle_type("АДПМ-020") == "ADPM"
    assert parse_vehicle_type("ППУ-030") == "PPU"
    assert parse_vehicle_type("Unknown") == "UNKNOWN"
