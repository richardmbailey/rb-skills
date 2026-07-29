"""Repeatable multi-seed benchmark for conservation, tail summaries, and speed."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys
import time


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from sandpile.analysis import summarize_avalanches  # noqa: E402
from sandpile.model import SandpileModel  # noqa: E402


DEFAULT_SIZES = (16, 24, 32)
DEFAULT_SEEDS = (7, 23, 41, 59, 83)


def compact_summary(summary: dict[str, object]) -> dict[str, object]:
    """Keep benchmark evidence useful without repeating unbounded raw tables."""

    return {
        key: value
        for key, value in summary.items()
        if key not in {"frequency", "ccdf"}
    }


def positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def run_case(size: int, seed: int, burn_in: int, samples: int, xmin: int) -> dict[str, object]:
    model = SandpileModel(size=size, seed=seed)
    started = time.perf_counter()
    model.add_grains(burn_in)
    model.clear_avalanche_history()
    model.add_grains(samples)
    elapsed = time.perf_counter() - started
    residual = model.mass_balance_residual
    if residual != 0:
        raise RuntimeError(f"mass conservation failed for size={size}, seed={seed}: residual={residual}")
    if any(height < 0 or height >= 4 for row in model.grid for height in row):
        raise RuntimeError(f"unstable or negative final lattice for size={size}, seed={seed}")
    summary = compact_summary(
        summarize_avalanches((event.size for event in model.avalanches), xmin=xmin)
    )
    return {
        "size": size,
        "seed": seed,
        "burn_in": burn_in,
        "samples": samples,
        "elapsed_seconds": elapsed,
        "grains_per_second": (burn_in + samples) / elapsed,
        "mass": {
            "added": model.total_added,
            "retained": model.retained_mass,
            "lost": model.total_lost,
            "residual": residual,
        },
        "summary": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--burn-in", type=positive_integer, default=5_000)
    parser.add_argument("--samples", type=positive_integer, default=20_000)
    parser.add_argument("--xmin", type=positive_integer, default=4)
    parser.add_argument("--sizes", type=positive_integer, nargs="+", default=list(DEFAULT_SIZES))
    parser.add_argument("--seeds", type=int, nargs="+", default=list(DEFAULT_SEEDS))
    args = parser.parse_args()
    if any(not SandpileModel.MIN_SIZE <= size <= SandpileModel.MAX_SIZE for size in args.sizes):
        parser.error(f"sizes must be between {SandpileModel.MIN_SIZE} and {SandpileModel.MAX_SIZE}")

    benchmark_started = time.perf_counter()
    runs = [
        run_case(size=size, seed=seed, burn_in=args.burn_in, samples=args.samples, xmin=args.xmin)
        for size in args.sizes
        for seed in args.seeds
    ]
    rates = [run["grains_per_second"] for run in runs]
    alphas = [
        run["summary"]["power_law_fit"]["alpha"]
        for run in runs
        if run["summary"]["power_law_fit"]["status"] == "estimated"
    ]
    output = {
        "configuration": {
            "model": "two-dimensional open-boundary Bak-Tang-Wiesenfeld sandpile",
            "sizes": args.sizes,
            "seeds": args.seeds,
            "burn_in": args.burn_in,
            "samples": args.samples,
            "xmin": args.xmin,
        },
        "aggregate": {
            "run_count": len(runs),
            "total_seconds": time.perf_counter() - benchmark_started,
            "median_grains_per_second": statistics.median(rates),
            "minimum_grains_per_second": min(rates),
            "estimated_alpha_run_count": len(alphas),
            "median_estimated_alpha": statistics.median(alphas) if alphas else None,
            "all_mass_balances_exact": all(run["mass"]["residual"] == 0 for run in runs),
        },
        "runs": runs,
        "interpretation": (
            "The reported power-law quantities are exploratory finite-sample diagnostics, "
            "not proof that the avalanche distribution follows a power law."
        ),
    }
    print(json.dumps(output, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
