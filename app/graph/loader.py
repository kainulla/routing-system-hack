"""Load road network into NetworkX graph with KDTree for map-matching."""
import numpy as np
import networkx as nx
from scipy.spatial import KDTree

from app.db.repository import SQLAlchemyRepository


class RoadGraph:
    def __init__(self):
        self.graph: nx.Graph = nx.Graph()
        self.coords: dict[int, tuple[float, float]] = {}
        self.kdtree: KDTree | None = None
        self._node_ids: list[int] = []
        self._node_coords: np.ndarray | None = None

    def load(self, repo: SQLAlchemyRepository):
        nodes = repo.get_road_nodes()
        edges = repo.get_road_edges()

        for n in nodes:
            self.graph.add_node(n.node_id, lon=n.lon, lat=n.lat)
            self.coords[n.node_id] = (n.lon, n.lat)

        for e in edges:
            self.graph.add_edge(e.source, e.target, weight=e.weight)

        self._node_ids = sorted(self.coords.keys())
        self._node_coords = np.array(
            [(self.coords[nid][1], self.coords[nid][0]) for nid in self._node_ids]
        )
        self.kdtree = KDTree(self._node_coords)

    def snap_to_node(self, lon: float, lat: float) -> tuple[int, float]:
        """Find nearest road node to (lon, lat). Returns (node_id, distance_m)."""
        dist, idx = self.kdtree.query([lat, lon])
        node_id = self._node_ids[idx]
        approx_m = dist * 111_000
        return node_id, round(approx_m, 2)

    @property
    def num_nodes(self) -> int:
        return self.graph.number_of_nodes()

    @property
    def num_edges(self) -> int:
        return self.graph.number_of_edges()
