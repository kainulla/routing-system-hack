"""FastAPI application entry point with lifespan initialization."""
import logging
import os
import threading
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app.db.base import SessionLocal
from app.db.repository import SQLAlchemyRepository
from app.graph.loader import RoadGraph
from app.graph.shortest_path import ShortestPathService
from app.fleet.state import FleetState
from app.api.routes import router

logger = logging.getLogger("vrp")
logging.basicConfig(level=logging.INFO)

_ready = threading.Event()


def _load_data(app: FastAPI):
    """Load graph, fleet, wells in background so the port opens immediately."""
    try:
        logger.info("Initializing VRP backend...")

        session = SessionLocal()
        repo = SQLAlchemyRepository(session)

        road_graph = RoadGraph()
        road_graph.load(repo)
        logger.info(f"Graph loaded: {road_graph.num_nodes} nodes, {road_graph.num_edges} edges")

        fleet = FleetState()
        fleet.load(repo, road_graph)
        logger.info(f"Fleet loaded: {len(fleet.vehicles)} vehicles")

        path_service = ShortestPathService(road_graph)

        wells = repo.get_wells()
        well_count = len(wells)
        logger.info(f"Wells loaded: {well_count}")

        session.close()

        app.state.road_graph = road_graph
        app.state.fleet = fleet
        app.state.path_service = path_service
        app.state.well_count = well_count

        _ready.set()
        logger.info("VRP backend ready.")
    except Exception as e:
        logger.error(f"Failed to initialize: {e}\n{traceback.format_exc()}")
        app.state._init_error = str(e)
        _ready.set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    thread = threading.Thread(target=_load_data, args=(app,), daemon=True)
    thread.start()
    yield
    logger.info("VRP backend shut down.")


app = FastAPI(
    title="VRP Routing Service",
    description="Vehicle routing and task optimization for oilfield operations",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
def health_check():
    if not _ready.is_set():
        return {"status": "loading"}
    if not hasattr(app.state, "road_graph"):
        from app.config import settings
        db_type = "postgresql" if "postgresql" in settings.DATABASE_URL else "sqlite"
        err = getattr(app.state, "_init_error", "unknown")
        raise HTTPException(status_code=503, detail=f"Failed to initialize ({db_type}): {err}")
    return {
        "status": "ok",
        "nodes": app.state.road_graph.num_nodes,
        "edges": app.state.road_graph.num_edges,
        "vehicles": len(app.state.fleet.vehicles),
        "wells": app.state.well_count,
    }


static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
