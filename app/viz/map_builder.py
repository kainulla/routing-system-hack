"""Folium map generation for route visualization."""
import folium

from app.db.repository import SQLAlchemyRepository
from app.fleet.state import FleetState
from app.graph.loader import RoadGraph


def build_route_map(
    road_graph: RoadGraph,
    fleet: FleetState,
    repo: SQLAlchemyRepository,
) -> str:
    # Auto-center on vehicle positions
    if fleet.vehicles:
        lats = [v.lat for v in fleet.vehicles.values()]
        lons = [v.lon for v in fleet.vehicles.values()]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
    else:
        center_lat, center_lon = 49.6, 59.2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10)

    # Wells
    wells = repo.get_wells()
    for w in wells:
        if w.latitude is None or w.longitude is None:
            continue
        folium.CircleMarker(
            location=[w.latitude, w.longitude],
            radius=4,
            color="green",
            fill=True,
            fill_opacity=0.7,
            popup=f"{w.uwi} ({w.well_name})",
        ).add_to(m)

    # Vehicles
    for wid, v in fleet.vehicles.items():
        folium.Marker(
            location=[v.lat, v.lon],
            popup=f"{v.name} ({v.vehicle_type})",
            icon=folium.Icon(color="blue", icon="truck", prefix="fa"),
        ).add_to(m)

    return m._repr_html_()


def build_path_map(
    coords: list[tuple[float, float]],
    center_lat: float | None = None,
    center_lon: float | None = None,
    stops: list[dict] | None = None,
) -> str:
    if not coords:
        return "<p>No path to display</p>"

    if center_lat is None:
        center_lat = sum(c[1] for c in coords) / len(coords)
    if center_lon is None:
        center_lon = sum(c[0] for c in coords) / len(coords)

    m = folium.Map(location=[center_lat, center_lon], zoom_start=11)

    # Route polyline (coords are lon,lat — folium needs lat,lon)
    path_latlon = [[c[1], c[0]] for c in coords]
    folium.PolyLine(path_latlon, color="red", weight=4, opacity=0.8).add_to(m)

    # Start marker
    folium.Marker(
        location=path_latlon[0],
        popup="Start",
        icon=folium.Icon(color="green", icon="play"),
    ).add_to(m)

    # End marker
    folium.Marker(
        location=path_latlon[-1],
        popup="End",
        icon=folium.Icon(color="red", icon="stop"),
    ).add_to(m)

    # Numbered stops
    if stops:
        for i, stop in enumerate(stops):
            folium.Marker(
                location=[stop["lat"], stop["lon"]],
                popup=f"Stop {i + 1}: {stop.get('label', '')}",
                icon=folium.DivIcon(
                    html=f'<div style="background:orange;color:white;border-radius:50%;width:24px;height:24px;text-align:center;line-height:24px;font-weight:bold;">{i + 1}</div>'
                ),
            ).add_to(m)

    return m._repr_html_()
