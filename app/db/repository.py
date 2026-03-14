from typing import Protocol
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import (
    RoadNode, RoadEdge, Well, WialonSnapshot, Task, Compatibility,
)


class DataRepository(Protocol):
    def get_road_nodes(self) -> list[RoadNode]: ...
    def get_road_edges(self) -> list[RoadEdge]: ...
    def get_wells(self) -> list[Well]: ...
    def get_latest_snapshot(self) -> list[WialonSnapshot]: ...
    def get_tasks(self) -> list[Task]: ...
    def get_compatibility(self) -> list[Compatibility]: ...


class SQLAlchemyRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_road_nodes(self) -> list[RoadNode]:
        return self.session.query(RoadNode).all()

    def get_road_edges(self) -> list[RoadEdge]:
        return self.session.query(RoadEdge).all()

    def get_wells(self) -> list[Well]:
        return self.session.query(Well).all()

    def get_latest_snapshot(self) -> list[WialonSnapshot]:
        return self.session.query(WialonSnapshot).all()

    def get_tasks(self) -> list[Task]:
        return self.session.query(Task).all()

    def get_task_by_id(self, task_id: str) -> Task | None:
        return self.session.query(Task).filter(Task.task_id == task_id).first()

    def get_compatibility(self) -> list[Compatibility]:
        return self.session.query(Compatibility).all()

    def get_well_by_uwi(self, uwi: str) -> Well | None:
        return self.session.query(Well).filter(Well.uwi == uwi).first()
