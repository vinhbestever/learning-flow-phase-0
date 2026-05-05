import math

from . import config


def forgetting_score(days_since: int, stability: float | None = None) -> float:
    """
    Proportion of memory forgotten: 1 - e^(-t/S).
    With a single prior exposure and default stability ≈1 day, anything
    older than ~7 days scores ≥ 0.999 (effectively fully forgotten).
    Returns 0.0–1.0; higher = more forgotten.
    """
    if stability is None:
        stability = config.EBBINGHAUS_STABILITY_DAYS
    if days_since <= 0:
        return 0.0
    return round(1.0 - math.exp(-days_since / stability), 4)


def retention_score(days_since: int, stability: float | None = None) -> float:
    """Complement of forgetting_score. 1.0 = fully retained."""
    if stability is None:
        stability = config.EBBINGHAUS_STABILITY_DAYS
    return round(1.0 - forgetting_score(days_since, stability), 4)
