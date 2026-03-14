# Official Spec Summary — Key Gaps vs Current Implementation

## DB Connection (Real PostgreSQL)
- Host: 95.47.96.41:5432, DB: mock_uto, User: readonly_user, Pass: Eh092P72se.)
- Schemas: references, stm, dcm, dct

## Real Table Schemas (vs our synthetic)

### references.road_nodes
| Field | Type | Note |
|-------|------|------|
| id | serial PK | technical key |
| node_id | integer unique | logical ID for graph |
| lon | numeric(12,8) | |
| lat | numeric(12,8) | |

**GAP**: our model uses `id` as node_id. Real DB has separate `node_id` field.

### references.road_edges
| Field | Type | Note |
|-------|------|------|
| id | serial PK | |
| source | integer | -> road_nodes.node_id |
| target | integer | -> road_nodes.node_id |
| weight | numeric(12,6) | meters |

**GAP**: our model uses `from_node`/`to_node`. Real DB uses `source`/`target`.

### references.wells
| Field | Type | Note |
|-------|------|------|
| id | serial PK | |
| uwi | varchar(50) unique | |
| latitude | numeric(12,8) | |
| longitude | numeric(12,8) | |
| well_name | varchar(255) | |

**GAP**: our model uses `lon`/`lat`, real uses `longitude`/`latitude`. No `nearest_node` column in real DB.

### references.wialon_units_snapshot_1/2/3
| Field | Type | Note |
|-------|------|------|
| wialon_id | bigint | vehicle ID |
| nm | text | vehicle name |
| cls, mu | integer | ignore |
| pos_t | bigint | Unix timestamp |
| pos_y | double | latitude |
| pos_x | double | longitude |
| registration_plate | text | |
| payload_json | jsonb | |

**GAP**: our model uses vehicle_id/vehicle_name/vehicle_type/lon/lat/speed/timestamp/snapshot_number. Real uses wialon_id/nm/pos_x/pos_y/pos_t. No explicit vehicle_type — must be parsed from `nm`.

### Tasks (loaded from CSV into DB)
| Field | Type |
|-------|------|
| task_id | string |
| priority | enum (low/medium/high) |
| planned_start | datetime |
| planned_duration_hours | float |
| destination_uwi | string |
| task_type | string |
| shift | enum (day/night) |
| start_day | date |

**GAP**: our model has `duration_hours`, real has `planned_duration_hours`. Real has `start_day` field. Our model has `assigned_vehicle`/`status` (not in spec).

### Compatibility Dictionary
From stm/dct schemas — need to find actual table mapping vehicle types to task types.

## API Format Gaps

### POST /api/recommendations
**Spec output**: `units[]` with `wialon_id`, `name`, `eta_minutes`, `distance_km`, `score`, `reason`
**Ours**: `recommendations[]` with `vehicle_id`, `vehicle_name`, `vehicle_type`, `score`, `distance_m`, `eta_minutes`, `reason`

Key diffs: spec uses `wialon_id` not `vehicle_id`, `distance_km` not `distance_m`, field name `units` not `recommendations`.

### POST /api/route
**Spec input**: `from: {wialon_id, lon, lat}`, `to: {uwi, lon, lat}`
**Ours**: `from_lon`, `from_lat`, `to_lon`, `to_lat`

**Spec output**: `distance_km`, `time_minutes`, `nodes[]`, `coords[]`
**Ours**: `distance_m`, `duration_minutes`, `path_coords[]`, `from_node`, `to_node`

Key diffs: spec expects `nodes` list + `coords` list separately, distance in km.

### POST /api/multitask
**Spec input**: `task_ids[]`, `constraints: {max_total_time_minutes, max_detour_ratio}`
**Ours**: `vehicle_id`, `tasks[]`

**Spec output**: `groups[]` (arrays of task_ids), `strategy_summary`, `total_distance_km`, `total_time_minutes`, `baseline_distance_km`, `baseline_time_minutes`, `savings_percent`, `reason`
**Ours**: `groups[]` (objects with stops), `baseline_total_m`, `optimized_total_m`, `savings_percent`

Key diffs: spec doesn't take vehicle_id (system should decide), groups are arrays of task_ids not objects, has strategy_summary and reason, uses km not m.

## Scoring Formula (from spec slide 06)
score(vk, jl) = 1 - (ωd * D/Dmax + ωt * ETA/ETAmax + ωw * wait/waitmax + ωp * penaltySLA)

Weights: ωd=0.30, ωt=0.30, ωw=0.15, ωp=0.25

**GAP**: our formula uses distance(0.30), eta(0.25), priority(0.20), compatibility(0.15), availability(0.10). Spec uses distance(0.30), ETA(0.30), wait/idle(0.15), SLA_penalty(0.25). Different components and weights.

## Objective Function
min Z = α * Σ(route distances) + β * Σ(wl * τl) + γ * Σ(δk)
- α: total mileage
- β: weighted lateness (priority-weighted)
- γ: idle time

## SLA Rules
- Priority weights: high=55%, medium=35%, low=10%
- Deadline from planned_start: high=+2h, medium=+5h, low=+12h
- Shifts: day 08:00-20:00, night 20:00-08:00

## Constraints
1. Each task assigned to exactly one vehicle
2. Compatibility: vehicle type must match task type
3. Routes on graph only
4. Open-end (no return to base)
5. Time availability: work starts after vehicle arrives
6. Time windows (soft, penalty)
7. SLA deadline (soft, penalty)
8. Multi-stop detour ratio constraint
