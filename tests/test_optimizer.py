"""Tests for scoring logic."""
from datetime import datetime
from app.optimizer.scoring import compute_score


def test_score_range():
    score, reason = compute_score(
        distance_m=5000,
        eta_minutes=10,
        priority="high",
        is_compatible=True,
        free_at=datetime(2025, 2, 20, 7, 0),
        planned_start=datetime(2025, 2, 20, 8, 0),
    )
    assert 0 <= score <= 1
    assert "compatible" in reason


def test_incompatible_lowers_score():
    score_compat, _ = compute_score(
        distance_m=5000,
        eta_minutes=10,
        priority="medium",
        is_compatible=True,
        free_at=datetime(2025, 2, 20, 8, 0),
        planned_start=datetime(2025, 2, 20, 8, 0),
    )
    score_incompat, _ = compute_score(
        distance_m=5000,
        eta_minutes=10,
        priority="medium",
        is_compatible=False,
        free_at=datetime(2025, 2, 20, 8, 0),
        planned_start=datetime(2025, 2, 20, 8, 0),
    )
    assert score_compat > score_incompat


def test_closer_is_better():
    score_close, _ = compute_score(
        distance_m=2000,
        eta_minutes=5,
        priority="medium",
        is_compatible=True,
        free_at=datetime(2025, 2, 20, 8, 0),
        planned_start=datetime(2025, 2, 20, 8, 0),
    )
    score_far, _ = compute_score(
        distance_m=40000,
        eta_minutes=80,
        priority="medium",
        is_compatible=True,
        free_at=datetime(2025, 2, 20, 8, 0),
        planned_start=datetime(2025, 2, 20, 8, 0),
    )
    assert score_close > score_far
