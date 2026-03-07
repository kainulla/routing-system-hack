"""Tests for graph module."""
import numpy as np
from app.graph.loader import RoadGraph
from app.graph.shortest_path import ShortestPathService


def _make_small_graph() -> RoadGraph:
    rg = RoadGraph()
    # 4-node square: 0--1
    #                |  |
    #                2--3
    for nid, lon, lat in [(0, 68.0, 51.5), (1, 68.1, 51.5), (2, 68.0, 51.6), (3, 68.1, 51.6)]:
        rg.graph.add_node(nid, lon=lon, lat=lat)
        rg.coords[nid] = (lon, lat)
    rg.graph.add_edge(0, 1, weight=1000)
    rg.graph.add_edge(0, 2, weight=1000)
    rg.graph.add_edge(1, 3, weight=1000)
    rg.graph.add_edge(2, 3, weight=1000)

    rg._node_ids = [0, 1, 2, 3]
    rg._node_coords = np.array([[51.5, 68.0], [51.5, 68.1], [51.6, 68.0], [51.6, 68.1]])
    from scipy.spatial import KDTree
    rg.kdtree = KDTree(rg._node_coords)
    return rg


def test_snap_to_node():
    rg = _make_small_graph()
    node_id, dist = rg.snap_to_node(68.0, 51.5)
    assert node_id == 0
    assert dist < 500


def test_shortest_path():
    rg = _make_small_graph()
    svc = ShortestPathService(rg)
    result = svc.find_path(0, 3)
    assert result is not None
    assert result.distance_m == 2000
    assert len(result.nodes) == 3


def test_no_path():
    rg = _make_small_graph()
    rg.graph.add_node(99, lon=69.0, lat=52.0)
    rg.coords[99] = (69.0, 52.0)
    svc = ShortestPathService(rg)
    result = svc.find_path(0, 99)
    assert result is None


def test_distance_matrix():
    rg = _make_small_graph()
    svc = ShortestPathService(rg)
    mat = svc.compute_distance_matrix([0, 1], [2, 3])
    assert mat.shape == (2, 2)
    assert mat[0, 0] == 1000  # 0->2
    assert mat[0, 1] == 2000  # 0->3
