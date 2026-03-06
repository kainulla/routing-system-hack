from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean
from app.db.base import Base


class RoadNode(Base):
    __tablename__ = "road_nodes"
    id = Column(Integer, primary_key=True)
    lon = Column(Float, nullable=False)
    lat = Column(Float, nullable=False)


class RoadEdge(Base):
    __tablename__ = "road_edges"
    id = Column(Integer, primary_key=True)
    from_node = Column(Integer, nullable=False)
    to_node = Column(Integer, nullable=False)
    weight = Column(Float, nullable=False)  # meters


class Well(Base):
    __tablename__ = "wells"
    id = Column(Integer, primary_key=True)
    uwi = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=True)
    lon = Column(Float, nullable=False)
    lat = Column(Float, nullable=False)
    nearest_node = Column(Integer, nullable=True)


class WialonSnapshot(Base):
    __tablename__ = "wialon_snapshots"
    id = Column(Integer, primary_key=True)
    vehicle_id = Column(String, nullable=False)
    vehicle_name = Column(String, nullable=False)
    vehicle_type = Column(String, nullable=False)
    lon = Column(Float, nullable=False)
    lat = Column(Float, nullable=False)
    speed = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    snapshot_number = Column(Integer, nullable=False)


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    task_id = Column(String, nullable=False, unique=True)
    task_type = Column(String, nullable=False)
    priority = Column(String, nullable=False)
    destination_uwi = Column(String, nullable=False)
    planned_start = Column(DateTime, nullable=False)
    duration_hours = Column(Float, nullable=False)
    shift = Column(String, nullable=False)
    assigned_vehicle = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")


class Compatibility(Base):
    __tablename__ = "compatibility"
    id = Column(Integer, primary_key=True)
    vehicle_type = Column(String, nullable=False)
    task_type = Column(String, nullable=False)
    compatible = Column(Boolean, nullable=False, default=True)
