"""Transparent descriptive analysis for sandpile avalanche measurements."""

from __future__ import annotations

from collections import Counter
import math
from typing import Iterable


def _validated_sizes(values: Iterable[int]) -> list[int]:
    sizes = list(values)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in sizes):
        raise TypeError("avalanche sizes must be integers")
    if any(value < 0 for value in sizes):
        raise ValueError("avalanche sizes cannot be negative")
    return sizes


def frequency_table(values: Iterable[int]) -> list[dict[str, int | float]]:
    positive = [value for value in _validated_sizes(values) if value > 0]
    counts = Counter(positive)
    total = len(positive)
    return [
        {"size": size, "count": count, "frequency": count / total}
        for size, count in sorted(counts.items())
    ] if total else []


def complementary_cdf(values: Iterable[int]) -> list[dict[str, int | float]]:
    positive = sorted(value for value in _validated_sizes(values) if value > 0)
    if not positive:
        return []
    counts = Counter(positive)
    total = len(positive)
    remaining = total
    result: list[dict[str, int | float]] = []
    for size in sorted(counts):
        result.append({"size": size, "count_at_least": remaining, "probability": remaining / total})
        remaining -= counts[size]
    return result


def logarithmic_bins(values: Iterable[int], base: int = 2) -> list[dict[str, int | float]]:
    if isinstance(base, bool) or not isinstance(base, int) or base < 2:
        raise ValueError("base must be an integer of at least two")
    positive = [value for value in _validated_sizes(values) if value > 0]
    if not positive:
        return []
    total = len(positive)
    largest = max(positive)
    lower = 1
    bins: list[dict[str, int | float]] = []
    while lower <= largest:
        upper = lower * base - 1
        count = sum(lower <= value <= upper for value in positive)
        bins.append(
            {
                "lower": lower,
                "upper": upper,
                "midpoint": math.sqrt(lower * upper),
                "count": count,
                "frequency": count / total,
            }
        )
        lower *= base
    return bins


def fit_power_law(
    values: Iterable[int],
    xmin: int = 1,
    minimum_tail: int = 25,
) -> dict[str, int | float | str | None]:
    """Return an approximate discrete-tail MLE and a descriptive KS distance."""

    if isinstance(xmin, bool) or not isinstance(xmin, int) or xmin < 1:
        raise ValueError("xmin must be a positive integer")
    if isinstance(minimum_tail, bool) or not isinstance(minimum_tail, int) or minimum_tail < 2:
        raise ValueError("minimum_tail must be an integer of at least two")
    tail = sorted(value for value in _validated_sizes(values) if value >= xmin)
    result: dict[str, int | float | str | None] = {
        "status": "insufficient_data",
        "method": "approximate discrete MLE with continuity correction",
        "n": len(tail),
        "xmin": xmin,
        "alpha": None,
        "ks_distance": None,
        "minimum_tail": minimum_tail,
    }
    if len(tail) < minimum_tail:
        return result

    denominator = sum(math.log(value / (xmin - 0.5)) for value in tail)
    if denominator <= 0:
        return result
    alpha = 1.0 + len(tail) / denominator
    counts = Counter(tail)
    cumulative = 0
    ks_distance = 0.0
    for value in sorted(counts):
        cumulative += counts[value]
        empirical_cdf = cumulative / len(tail)
        model_cdf = 1.0 - ((value + 0.5) / (xmin - 0.5)) ** (1.0 - alpha)
        model_cdf = min(1.0, max(0.0, model_cdf))
        ks_distance = max(ks_distance, abs(empirical_cdf - model_cdf))

    result.update(status="estimated", alpha=alpha, ks_distance=ks_distance)
    return result


def summarize_avalanches(values: Iterable[int], xmin: int = 1) -> dict[str, object]:
    sizes = _validated_sizes(values)
    positive = [value for value in sizes if value > 0]
    return {
        "recorded_additions": len(sizes),
        "positive_avalanches": len(positive),
        "zero_fraction": (len(sizes) - len(positive)) / len(sizes) if sizes else 0.0,
        "largest_avalanche": max(positive, default=0),
        "frequency": frequency_table(sizes),
        "ccdf": complementary_cdf(sizes),
        "logarithmic_bins": logarithmic_bins(sizes),
        "power_law_fit": fit_power_law(sizes, xmin=xmin),
        "interpretation": (
            "This is a descriptive finite-sample diagnostic. A straight-looking log-log plot "
            "or an estimated exponent does not by itself establish a power law."
        ),
    }
