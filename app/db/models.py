from sqlalchemy import Column, Integer, BigInteger, Float, String, DateTime, Boolean, Date, Text
from sqlalchemy.types import JSON
from app.db.base import Base
from app.config import settings

# Use schema prefix for PostgreSQL, none for SQLite
_pg = "postgresql" in settings.DATABASE_URL
_ref_schema = "references" if _pg else None


class RoadNode(Base):
    __tablename__ = "road_nodes"
    __table_args__ = {"schema": _ref_schema} if _ref_schema else {}
    id = Column(Integer, primary_key=True)
    node_id = Column(Integer, unique=True, nullable=False)
    lon = Column(Float, nullable=False)
    lat = Column(Float, nullable=False)


class RoadEdge(Base):
    __tablename__ = "road_edges"
    __table_args__ = {"schema": _ref_schema} if _ref_schema else {}
    id = Column(Integer, primary_key=True)
    source = Column(Integer, nullable=False)
    target = Column(Integer, nullable=False)
    weight = Column(Float, nullable=False)  # meters


class Well(Base):
    __tablename__ = "wells"
    __table_args__ = {"schema": _ref_schema} if _ref_schema else {}
    id = Column(Integer, primary_key=True)
    uwi = Column(String(50), nullable=False, unique=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    well_name = Column(String(255), nullable=True)


class WialonSnapshot(Base):
    __tablename__ = "wialon_units_snapshot_3"
    __table_args__ = {"schema": _ref_schema} if _ref_schema else {}
    id = Column(Integer, primary_key=True)
    wialon_id = Column(BigInteger, nullable=False)
    nm = Column(Text, nullable=False)
    pos_x = Column(Float, nullable=False)  # longitude
    pos_y = Column(Float, nullable=False)  # latitude
    pos_t = Column(BigInteger, nullable=False)  # unix timestamp
    registration_plate = Column(Text, nullable=True)
    snapshot_number = Column(Integer, nullable=True)


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    task_id = Column(String, nullable=False, unique=True)
    task_type = Column(String, nullable=False)
    priority = Column(String, nullable=False)
    destination_uwi = Column(String, nullable=False)
    planned_start = Column(DateTime, nullable=False)
    planned_duration_hours = Column(Float, nullable=False)
    shift = Column(String, nullable=False)
    start_day = Column(Date, nullable=True)
    assigned_vehicle = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")


class Compatibility(Base):
    __tablename__ = "compatibility"
    id = Column(Integer, primary_key=True)
    vehicle_type = Column(String, nullable=False)
    task_type = Column(String, nullable=False)
    compatible = Column(Boolean, nullable=False, default=True)
