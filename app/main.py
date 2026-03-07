"""FastAPI application entry point with lifespan initialization."""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db.base import SessionLocal
from app.db.repository import SQLAlchemyRepository
from app.graph.loader import RoadGraph
from app.graph.shortest_path import ShortestPathService
from app.fleet.state import FleetState
from app.api.routes import router

logger = logging.getLogger("vrp")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing VRP backend...")

    session = SessionLocal()
    repo = SQLAlchemyRepository(session)

    # Load road graph
    road_graph = RoadGraph()
    road_graph.load(repo)
    logger.info(f"Graph loaded: {road_graph.num_nodes} nodes, {road_graph.num_edges} edges")

    # Build fleet state
    fleet = FleetState()
    fleet.load(repo, road_graph)
    logger.info(f"Fleet loaded: {len(fleet.vehicles)} vehicles")

    # Path service
    path_service = ShortestPathService(road_graph)

    # Well count
    wells = repo.get_wells()
    well_count = len(wells)
    logger.info(f"Wells loaded: {well_count}")

    # Store on app state
    app.state.repo = repo
    app.state.road_graph = road_graph
    app.state.fleet = fleet
    app.state.path_service = path_service
    app.state.well_count = well_count

    yield

    session.close()
    logger.info("VRP backend shut down.")


app = FastAPI(
    title="VRP Routing Service",
    description="Vehicle routing and task optimization for oilfield operations",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)

static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
