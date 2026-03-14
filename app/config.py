from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///data/synthetic.db"
    AVG_SPEED_KMH: float = 30.0

    PRIORITY_WEIGHTS: dict[str, float] = {
        "high": 0.55,
        "medium": 0.35,
        "low": 0.10,
    }
    SLA_HOURS: dict[str, float] = {
        "high": 2.0,
        "medium": 5.0,
        "low": 12.0,
    }
    SHIFT_HOURS: dict[str, tuple[int, int]] = {
        "day": (8, 20),
        "night": (20, 8),
    }

    # Spec scoring weights: ωd=0.30, ωt=0.30, ωw=0.15, ωp=0.25
    SCORING_WEIGHTS: dict[str, float] = {
        "distance": 0.30,
        "eta": 0.30,
        "wait": 0.15,
        "sla_penalty": 0.25,
    }

    DETOUR_RATIO_MAX: float = 1.4

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
