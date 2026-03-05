# Implementation Plan (High-Level)

## Tech Stack
- **Python 3.11+**, **FastAPI**, **PostgreSQL** (provided DB)
- **NetworkX** or **igraph** for graph operations
- **scipy.spatial.KDTree** for map-matching (snap coords to nearest graph node)
- **OR-Tools** (Google) for VRP solver
- **Leaflet/Folium** for map visualization

## Architecture: 5 Modules

```
[DB: PostgreSQL] --> [1. Graph Loader] --> [2. Shortest Path Service]
                                                  |
[DB: Wialon snapshots] --> [3. Fleet State] ----> |
                                                  v
[DB: Tasks/Wells] -----------------------> [4. Optimization Engine]
                                                  |
                                                  v
                                           [5. REST API + Viz]
```

## Step-by-Step

### Step 1: Data Layer & Graph Loading
- Connect to provided PostgreSQL DB
- Load `road_nodes` and `road_edges` into an in-memory graph (NetworkX/igraph)
- Build KDTree from node coordinates for `snap_to_node(lon, lat) -> node_id`
- Load wells, snap each well to nearest graph node
- Load Wialon snapshots, snap each vehicle position to nearest graph node

### Step 2: Shortest Path Service + Distance Matrix
- Implement Dijkstra (or use library) on the loaded graph
- For a pair `(start_node, end_node)` return: distance (sum of weights), path (list of node_ids), coords (list of lon/lat)
- Build distance/time matrix for batch queries: all vehicle positions x all task destinations
- Time = distance / avg_speed (avg_speed per vehicle type, ~20-40 km/h for oilfield roads)

### Step 3: Fleet State Module
- For each vehicle from latest snapshot: current position (node), status (free/busy)
- Cross-reference with existing task assignments to compute `free_at` (when vehicle finishes current task)
- Determine vehicle skills (compatible work types) from compatibility dictionary
- Expose: `get_available_vehicles(at_time)` -> list of vehicles with position, status, ETA to freedom

### Step 4: Optimization Engine (Core)
Three modes as required by API:

**a) Single recommendation (`POST /api/recommendations`)**
- For given task: find compatible vehicles, compute distance/ETA from each, score them
- Scoring formula: `score = w1 * (1/distance) + w2 * (1/wait_time) + w3 * priority_match + w4 * compatibility`
- Return top-3 ranked candidates with score + reason

**b) Route building (`POST /api/route`)**
- Snap from/to to graph nodes
- Run shortest path, return distance, time, node list, coordinate list

**c) Multi-task grouping (`POST /api/multitask`)**
- For given task set: compute pairwise distances between task locations
- Greedy clustering: merge tasks within `max_detour_ratio` constraint
- For each group: compute TSP route (optimal visit order), total distance/time
- Compare with baseline (each task separately), return savings %
- Use OR-Tools VRP solver for better results if time allows

**Baseline for comparison**: greedy nearest-free-vehicle assignment (no grouping, no priority logic)

### Step 5: REST API + Visualization
- FastAPI with 3 endpoints: `/api/recommendations`, `/api/route`, `/api/multitask`
- Folium-based map page: show vehicle positions, task locations, routes as polylines
- Return GeoJSON-compatible coords in API responses for easy frontend rendering

## Priority Order for Development
1. Steps 1-2 first (graph + shortest paths) -- foundation for everything
2. Step 3 (fleet state) -- needed for recommendations
3. Step 4a + 4b (single recommendation + route) -- core deliverable, demo scenarios 1 & 2
4. Step 4c (multi-task) -- demo scenario 3
5. Step 5 viz (Folium map) -- polish for demo day

## What Makes It Score Well (per criteria)
- **Algorithm quality (35%)**: OR-Tools VRP > naive greedy, show savings comparison
- **Technical execution (25%)**: modular FastAPI, clean separation of graph/fleet/optimizer
- **Innovation (20%)**: LLM-generated reason field, priority-aware scoring with tunable weights
- **Practical use (15%)**: clear API responses with explanations, map visualization
- **Data processing (10%)**: proper map-matching, distance matrix precomputation
