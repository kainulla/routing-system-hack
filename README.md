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
    "planned_duration_hours": 4.5
  }'
```

Response returns `units[]` with `wialon_id`, `name`, `distance_km`, `eta_minutes`, `score`, `reason`.

### Compute Route Between Points
```bash
curl -X POST http://localhost:8000/api/route \
  -H "Content-Type: application/json" \
  -d '{
    "from": {"lon": 68.1, "lat": 51.6},
    "to": {"uwi": "05-0076-745", "lon": 68.3, "lat": 51.8}
  }'
```

Response returns `distance_km`, `time_minutes`, `nodes[]`, `coords[]`.

### Optimize Multiple Tasks
```bash
curl -X POST http://localhost:8000/api/multitask \
  -H "Content-Type: application/json" \
  -d '{
    "task_ids": ["T-2025-0001", "T-2025-0002", "T-2025-0003"],
    "constraints": {
      "max_detour_ratio": 1.5
    }
  }'
```

Response returns `groups[]` (arrays of task_ids), `strategy_summary`, `total_distance_km`, `total_time_minutes`, `baseline_distance_km`, `baseline_time_minutes`, `savings_percent`, `reason`.

### Visualization
- **Web UI**: http://localhost:8000 — interactive map with task/vehicle selection
- **Folium map**: http://localhost:8000/api/viz/route — static overview of wells and vehicles

## Scoring Formula

```
score(vk, jl) = 1 - (ωd * D/Dmax + ωt * ETA/ETAmax + ωw * wait/waitmax + ωp * penaltySLA)
```

Weights: ωd=0.30, ωt=0.30, ωw=0.15, ωp=0.25

## Run Tests

```bash
pytest tests/ -v
```

## DB Swap to PostgreSQL

Change `DATABASE_URL` in `.env`:
```
DATABASE_URL=postgresql://readonly_user:Eh092P72se.)@95.47.96.41:5432/mock_uto
```
Everything else stays the same — SQLAlchemy handles dialect differences.
