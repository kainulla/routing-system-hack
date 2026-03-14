"""Tests for scoring logic."""
from datetime import datetime
from app.optimizer.scoring import compute_score


def test_score_range():
    score, reason = compute_score(
        distance_m=5000,
        eta_minutes=10,
        priority="high",
        free_at=datetime(2025, 2, 20, 7, 0),
        planned_start=datetime(2025, 2, 20, 8, 0),
    )
    assert 0 <= score <= 1
    assert "SLA" in reason


def test_closer_is_better():
    score_close, _ = compute_score(
        distance_m=2000,
        eta_minutes=5,
        priority="medium",
        free_at=datetime(2025, 2, 20, 8, 0),
        planned_start=datetime(2025, 2, 20, 8, 0),
    )
    score_far, _ = compute_score(
        distance_m=40000,
        eta_minutes=80,
        priority="medium",
        free_at=datetime(2025, 2, 20, 8, 0),
        planned_start=datetime(2025, 2, 20, 8, 0),
    )
    assert score_close > score_far


def test_sla_penalty_high_priority():
    # Vehicle arrives way after SLA deadline (high = +2h)
    score_late, reason = compute_score(
        distance_m=5000,
        eta_minutes=10,
        priority="high",
        free_at=datetime(2025, 2, 20, 12, 0),  # 4h after planned_start
        planned_start=datetime(2025, 2, 20, 8, 0),
    )
    score_ontime, _ = compute_score(
        distance_m=5000,
        eta_minutes=10,
        priority="high",
        free_at=datetime(2025, 2, 20, 8, 0),
        planned_start=datetime(2025, 2, 20, 8, 0),
    )
    assert score_ontime > score_late
    assert "риск SLA" in reason
