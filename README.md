# VRP Routing Service

Vehicle routing and task optimization for oilfield operations.

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, NetworkX, scipy, OR-Tools
- **Frontend**: Single-page HTML/JS with Leaflet maps
- **Database**: SQLite (synthetic), swappable to PostgreSQL via `DATABASE_URL`

## Project Structure

```
app/
  main.py              # FastAPI entry + lifespan init
  config.py            # Settings (DB URL, weights, speeds)
  db/                  # SQLAlchemy models, engine, repository
  graph/               # Road network graph + shortest path (Dijkstra)
  fleet/               # Vehicle positions, availability, skills
  optimizer/           # Scoring, recommendations, routing, multitask (OR-Tools)
  api/                 # Pydantic schemas + FastAPI routes
  viz/                 # Folium map generation
static/
  index.html           # Frontend (RU locale)
scripts/
  generate_data.py     # Synthetic data generator
tests/                 # pytest suite
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Generate Synthetic Data

```bash
python scripts/generate_data.py
```

Creates `data/synthetic.db` with ~2500 road nodes, ~12000 edges, 80 wells, 40 vehicles, 30 tasks.

## Run Server

```bash
uvicorn app.main:app --reload
```

Open http://localhost:8000 for the web UI.

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### List Data
```bash
curl http://localhost:8000/api/tasks
curl http://localhost:8000/api/vehicles
curl http://localhost:8000/api/wells
```

### Recommend Vehicles for a Task
```bash
curl -X POST http://localhost:8000/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "T-2025-0001",
    "priority": "high",
    "destination_uwi": "05-0076-745",
    "planned_start": "2025-02-20T08:00:00",
    "duration_hours": 4.5
  }'
```

### Compute Route Between Points
```bash
curl -X POST http://localhost:8000/api/route \
  -H "Content-Type: application/json" \
  -d '{
    "from_lon": 68.1,
    "from_lat": 51.6,
    "to_lon": 68.3,
    "to_lat": 51.8
  }'
```

### Optimize Multiple Tasks for a Vehicle
```bash
curl -X POST http://localhost:8000/api/multitask \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "V-007",
    "tasks": [
      {"task_id": "T-2025-0001", "destination_uwi": "05-0076-745", "priority": "high", "duration_hours": 4.5},
      {"task_id": "T-2025-0002", "destination_uwi": "05-0052-904", "priority": "medium", "duration_hours": 2.0}
    ]
  }'
```

### Visualization
- **Web UI**: http://localhost:8000 — interactive map with task/vehicle selection
- **Folium map**: http://localhost:8000/api/viz/route — static overview of wells and vehicles

## Run Tests

```bash
pytest tests/ -v
```

## DB Swap to PostgreSQL

Change `DATABASE_URL` in `.env`:
```
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```
Everything else stays the same — SQLAlchemy handles dialect differences.
