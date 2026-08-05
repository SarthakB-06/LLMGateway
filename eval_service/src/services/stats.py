"""
stats.py — Bootstrap confidence intervals for eval score aggregation.

Pure stdlib implementation — no numpy/scipy dependency.
Uses random.choices() for resampling (Python 3.6+).
"""
import random
import statistics
from typing import Optional


def bootstrap_ci(
    values: list,
    n_resamples: int = 1000,
    lower_pct: float = 5.0,
    upper_pct: float = 95.0,
    seed: Optional[int] = None,
) -> dict:
    """
    Compute a bootstrap confidence interval for the mean of `values`.

    Args:
        values:      List of numeric scores.
        n_resamples: Number of bootstrap resamples (default 1000).
        lower_pct:   Lower percentile for the CI (default 5 → 5th/95th = 90% CI).
        upper_pct:   Upper percentile for the CI.
        seed:        Optional RNG seed for reproducibility.

    Returns:
        {
            "mean":  float,   # mean of original sample
            "lower": float,   # lower_pct-th percentile of bootstrap means
            "upper": float,   # upper_pct-th percentile of bootstrap means
            "n":     int,     # original sample size
        }
    
    Raises:
        ValueError: if values is empty.
    """
    if not values:
        raise ValueError("Cannot compute CI on an empty list.")

    if seed is not None:
        random.seed(seed)

    n = len(values)
    mean = statistics.mean(values)

    if n == 1:
        # Degenerate case — no spread possible
        return {"mean": mean, "lower": mean, "upper": mean, "n": n}

    # Bootstrap: resample with replacement n_resamples times, compute mean each time
    boot_means = sorted(
        statistics.mean(random.choices(values, k=n))
        for _ in range(n_resamples)
    )

    lower_idx = max(0, int((lower_pct / 100.0) * n_resamples) - 1)
    upper_idx = min(n_resamples - 1, int((upper_pct / 100.0) * n_resamples) - 1)

    return {
        "mean":  round(mean, 4),
        "lower": round(boot_means[lower_idx], 4),
        "upper": round(boot_means[upper_idx], 4),
        "n":     n,
    }


def composite_score(correctness: Optional[float], completeness: Optional[float], clarity: Optional[float]) -> Optional[float]:
    """Compute the unweighted mean of available judge dimensions."""
    scores = [s for s in [correctness, completeness, clarity] if s is not None]
    if not scores:
        return None
    return statistics.mean(scores)

