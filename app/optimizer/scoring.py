"""Scoring formula aligned with official spec slide 06.

score(vk, jl) = 1 - (ωd * D/Dmax + ωt * ETA/ETAmax + ωw * wait/waitmax + ωp * penaltySLA)
Weights: ωd=0.30, ωt=0.30, ωw=0.15, ωp=0.25
"""
from datetime import datetime

from app.config import settings


def compute_sla_penalty(
    priority: str,
    eta_minutes: float,
    planned_start: datetime,
    free_at: datetime,
) -> float:
    """Compute SLA penalty based on whether vehicle can meet the deadline."""
    sla_hours = settings.SLA_HOURS.get(priority, 12.0)
    sla_deadline_minutes = sla_hours * 60

    wait_minutes = max(0, (free_at - planned_start).total_seconds() / 60)
    arrival_minutes = wait_minutes + eta_minutes

    if arrival_minutes <= sla_deadline_minutes:
        return 0.0
    overshoot = (arrival_minutes - sla_deadline_minutes) / sla_deadline_minutes
    return min(overshoot, 1.0)


def compute_score(
    distance_m: float,
    eta_minutes: float,
    priority: str,
    free_at: datetime,
    planned_start: datetime,
    max_distance_m: float = 200_000,
    max_eta_min: float = 400,
    max_wait_min: float = 480,
) -> tuple[float, str]:
    """Compute spec-aligned score [0,1]. Higher = better."""
    w = settings.SCORING_WEIGHTS

    d_norm = min(distance_m / max_distance_m, 1.0)
    eta_norm = min(eta_minutes / max_eta_min, 1.0)

    wait_minutes = max(0, (free_at - planned_start).total_seconds() / 60)
    wait_norm = min(wait_minutes / max_wait_min, 1.0)

    sla_penalty = compute_sla_penalty(priority, eta_minutes, planned_start, free_at)

    score = 1.0 - (
        w["distance"] * d_norm
        + w["eta"] * eta_norm
        + w["wait"] * wait_norm
        + w["sla_penalty"] * sla_penalty
    )
    score = round(min(max(score, 0), 1), 4)

    reason = build_reason(distance_m, eta_minutes, priority, wait_minutes, sla_penalty)
    return score, reason


PRIORITY_LABELS = {"high": "высокий", "medium": "средний", "low": "низкий"}


def build_reason(
    distance_m: float,
    eta_minutes: float,
    priority: str,
    wait_minutes: float,
    sla_penalty: float,
) -> str:
    parts = []
    dist_km = distance_m / 1000
    if dist_km < 10:
        parts.append(f"близко ({dist_km:.1f} км)")
    elif dist_km < 25:
        parts.append(f"среднее расстояние ({dist_km:.1f} км)")
    else:
        parts.append(f"далеко ({dist_km:.1f} км)")

    if eta_minutes < 20:
        parts.append(f"быстрое прибытие ({eta_minutes:.0f} мин)")
    else:
        parts.append(f"прибытие {eta_minutes:.0f} мин")

    if wait_minutes <= 0:
        parts.append("доступен сейчас")
    else:
        parts.append(f"ожидание {wait_minutes:.0f} мин")

    if sla_penalty > 0:
        parts.append(f"риск SLA ({sla_penalty:.0%})")
    else:
        parts.append("SLA в норме")

    priority_label = PRIORITY_LABELS.get(priority, priority)
    parts.append(f"приоритет: {priority_label}")
    return "; ".join(parts)
