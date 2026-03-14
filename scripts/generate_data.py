"""Generate spatially coherent synthetic data for VRP demo."""
import math
import os
import random
import sys
from datetime import datetime, timedelta, date

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set DATABASE_URL to SQLite before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///data/synthetic.db"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import (
    RoadNode, RoadEdge, Well, WialonSnapshot, Task, Compatibility,
)


def haversine(lon1, lat1, lon2, lat2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def generate():
    random.seed(42)
    np.random.seed(42)

    db_path = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)

    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # --- Road Nodes: grid with noise ---
    LON_MIN, LON_MAX = 68.0, 68.5
    LAT_MIN, LAT_MAX = 51.5, 52.0
    GRID = 50  # 50x50 = 2500 nodes
    lons = np.linspace(LON_MIN, LON_MAX, GRID)
    lats = np.linspace(LAT_MIN, LAT_MAX, GRID)

    nodes = []
    node_counter = 0
    coords = {}
    for i, lon in enumerate(lons):
        for j, lat in enumerate(lats):
            nlon = lon + np.random.normal(0, 0.001)
            nlat = lat + np.random.normal(0, 0.001)
            nid = node_counter
            nodes.append(RoadNode(id=node_counter, node_id=nid, lon=round(nlon, 6), lat=round(nlat, 6)))
            coords[nid] = (round(nlon, 6), round(nlat, 6))
            node_counter += 1
    session.bulk_save_objects(nodes)
    print(f"Created {len(nodes)} road nodes")

    # --- Road Edges: 4-neighbor + some diagonals ---
    edges = []
    edge_id = 0

    def nid(i, j):
        return i * GRID + j

    for i in range(GRID):
        for j in range(GRID):
            current = nid(i, j)
            neighbors = []
            if j + 1 < GRID:
                neighbors.append(nid(i, j + 1))
            if i + 1 < GRID:
                neighbors.append(nid(i + 1, j))
            if i + 1 < GRID and j + 1 < GRID and random.random() < 0.3:
                neighbors.append(nid(i + 1, j + 1))
            if i + 1 < GRID and j - 1 >= 0 and random.random() < 0.3:
                neighbors.append(nid(i + 1, j - 1))

            for nb in neighbors:
                c1 = coords[current]
                c2 = coords[nb]
                w = haversine(c1[0], c1[1], c2[0], c2[1])
                edges.append(RoadEdge(id=edge_id, source=current, target=nb, weight=round(w, 2)))
                edge_id += 1
                edges.append(RoadEdge(id=edge_id, source=nb, target=current, weight=round(w, 2)))
                edge_id += 1
    session.bulk_save_objects(edges)
    print(f"Created {len(edges)} road edges")

    # --- Wells: ~80 near road nodes ---
    well_node_ids = random.sample(list(coords.keys()), 80)
    wells = []
    for idx, wn_id in enumerate(well_node_ids):
        c = coords[wn_id]
        uwi = f"05-{idx:04d}-{random.randint(1, 999):03d}"
        wells.append(Well(
            id=idx,
            uwi=uwi,
            well_name=f"Скважина-{idx + 1}",
            longitude=c[0] + np.random.normal(0, 0.0005),
            latitude=c[1] + np.random.normal(0, 0.0005),
        ))
    session.bulk_save_objects(wells)
    print(f"Created {len(wells)} wells")

    # --- Vehicles: 40 with 3 snapshots ---
    VEHICLE_TYPES = ["ACN", "CA", "APSH", "ADPM", "PPU"]
    TYPE_NAMES_RU = {
        "ACN": "АЦН",
        "CA": "ЦА",
        "APSH": "АПШ",
        "ADPM": "АДПМ",
        "PPU": "ППУ",
    }
    snapshots = []
    snap_id = 0
    base_time = datetime(2025, 2, 20, 6, 0, 0)

    for v in range(40):
        vtype = VEHICLE_TYPES[v % len(VEHICLE_TYPES)]
        vname = f"{TYPE_NAMES_RU[vtype]}-{v + 1:03d}"
        wialon_id = 1000 + v
        base_node = random.choice(list(coords.keys()))
        base_lon, base_lat = coords[base_node]

        for snap_num in range(1, 4):
            drift_lon = base_lon + np.random.normal(0, 0.005) * snap_num
            drift_lat = base_lat + np.random.normal(0, 0.005) * snap_num
            ts = base_time + timedelta(hours=snap_num * 2)
            snapshots.append(WialonSnapshot(
                id=snap_id,
                wialon_id=wialon_id,
                nm=vname,
                pos_x=round(drift_lon, 6),
                pos_y=round(drift_lat, 6),
                pos_t=int(ts.timestamp()),
                registration_plate=f"{random.randint(100, 999)}ABC{random.randint(10, 99)}",
                snapshot_number=snap_num,
            ))
            snap_id += 1
    session.bulk_save_objects(snapshots)
    print(f"Created {len(snapshots)} wialon snapshots")

    # --- Tasks: ~30 over 3 days ---
    TASK_TYPES = ["transport_fluid", "cement_job", "well_service", "drilling_support", "steam_injection"]
    PRIORITIES = ["high", "medium", "low"]
    tasks = []
    well_uwis = [w.uwi for w in wells]

    for t in range(30):
        day_offset = t // 10
        hour = random.choice([8, 10, 12, 14, 16, 20, 22])
        planned = datetime(2025, 2, 20 + day_offset, hour, 0, 0)
        shift = "day" if 8 <= hour < 20 else "night"
        priority = random.choices(PRIORITIES, weights=[0.3, 0.5, 0.2])[0]
        task_type = random.choice(TASK_TYPES)
        dest_uwi = random.choice(well_uwis)
        start_day = date(2025, 2, 20 + day_offset)

        assigned = None
        status = "pending"
        if t < 10 and random.random() < 0.4:
            assigned = str(1000 + random.randint(0, 39))
            status = "assigned"

        tasks.append(Task(
            id=t,
            task_id=f"T-2025-{t + 1:04d}",
            task_type=task_type,
            priority=priority,
            destination_uwi=dest_uwi,
            planned_start=planned,
            planned_duration_hours=round(random.uniform(1.5, 8.0), 1),
            shift=shift,
            start_day=start_day,
            assigned_vehicle=assigned,
            status=status,
        ))
    session.bulk_save_objects(tasks)
    print(f"Created {len(tasks)} tasks")

    # --- Compatibility Matrix ---
    compat = []
    compat_id = 0
    compat_map = {
        "ACN": ["transport_fluid", "steam_injection"],
        "CA": ["cement_job", "well_service"],
        "APSH": ["well_service", "drilling_support"],
        "ADPM": ["drilling_support", "transport_fluid"],
        "PPU": ["steam_injection", "well_service"],
    }
    for vtype in VEHICLE_TYPES:
        for ttype in TASK_TYPES:
            is_compat = ttype in compat_map[vtype]
            compat.append(Compatibility(
                id=compat_id,
                vehicle_type=vtype,
                task_type=ttype,
                compatible=is_compat,
            ))
            compat_id += 1
    session.bulk_save_objects(compat)
    print(f"Created {len(compat)} compatibility entries")

    session.commit()
    session.close()
    print(f"\nDatabase written to: {os.path.abspath(db_path)}")


if __name__ == "__main__":
    generate()
