"""Scoring formula for vehicle-task matching."""
from datetime import datetime

from app.config import settings


def compute_score(
    distance_m: float,
    eta_minutes: float,
    priority: str,
    is_compatible: bool,
    free_at: datetime,
    planned_start: datetime,
    max_distance_m: float = 50_000,
    max_eta_min: float = 120,
) -> tuple[float, str]:
    """Compute normalized score [0,1] for a vehicle-task pair. Higher = better."""
    w = settings.SCORING_WEIGHTS

    # Distance: closer is better (inverted normalized)
    dist_norm = 1.0 - min(distance_m / max_distance_m, 1.0)

    # ETA: faster is better
    eta_norm = 1.0 - min(eta_minutes / max_eta_min, 1.0)

    # Priority alignment: high priority tasks get higher weight boost
    priority_weights = settings.PRIORITY_WEIGHTS
    priority_norm = priority_weights.get(priority, 0.1)

    # Compatibility: binary
    compat_norm = 1.0 if is_compatible else 0.0

    # Availability: ready sooner is better
    wait_hours = max(0, (free_at - planned_start).total_seconds() / 3600)
    avail_norm = 1.0 - min(wait_hours / 4.0, 1.0)

    score = (
        w["distance"] * dist_norm
        + w["eta"] * eta_norm
        + w["priority"] * priority_norm
        + w["compatibility"] * compat_norm
        + w["availability"] * avail_norm
    )
    score = round(min(max(score, 0), 1), 4)

    reason = build_reason(distance_m, eta_minutes, priority, is_compatible, wait_hours)
    return score, reason


PRIORITY_LABELS = {"high": "высокий", "medium": "средний", "low": "низкий"}


def build_reason(
    distance_m: float,
    eta_minutes: float,
    priority: str,
    is_compatible: bool,
    wait_hours: float,
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

    if is_compatible:
        parts.append("совместим")
    else:
        parts.append("НЕ совместим")

    if wait_hours <= 0:
        parts.append("доступен сейчас")
    else:
        parts.append(f"доступен через {wait_hours:.1f} ч")

    priority_label = PRIORITY_LABELS.get(priority, priority)
    parts.append(f"приоритет: {priority_label}")
    return "; ".join(parts)
