"""Shortest path and distance/time matrix computation."""
from dataclasses import dataclass

import networkx as nx
import numpy as np

from app.graph.loader import RoadGraph


@dataclass
class PathResult:
    distance_m: float
    nodes: list[int]
    coords: list[tuple[float, float]]


class ShortestPathService:
    def __init__(self, road_graph: RoadGraph):
        self.rg = road_graph

    def find_path(self, start_node: int, end_node: int) -> PathResult | None:
        try:
            nodes = nx.dijkstra_path(self.rg.graph, start_node, end_node, weight="weight")
            dist = nx.dijkstra_path_length(self.rg.graph, start_node, end_node, weight="weight")
            coords = [self.rg.coords[n] for n in nodes]
            return PathResult(distance_m=round(dist, 2), nodes=nodes, coords=coords)
        except nx.NetworkXNoPath:
            return None

    def compute_distance_matrix(
        self, sources: list[int], targets: list[int]
    ) -> np.ndarray:
        n_src = len(sources)
        n_tgt = len(targets)
        matrix = np.full((n_src, n_tgt), np.inf)

        target_set = set(targets)
        for i, src in enumerate(sources):
            try:
                lengths = nx.single_source_dijkstra_path_length(
                    self.rg.graph, src, weight="weight"
                )
                for j, tgt in enumerate(targets):
                    if tgt in lengths:
                        matrix[i, j] = lengths[tgt]
            except nx.NodeNotFound:
                continue
        return matrix

    def compute_time_matrix(
        self, dist_matrix: np.ndarray, speed_kmh: float
    ) -> np.ndarray:
        speed_ms = speed_kmh * 1000 / 3600
        with np.errstate(divide="ignore", invalid="ignore"):
            time_matrix = dist_matrix / speed_ms
        return time_matrix
