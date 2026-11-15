"""Explicit Euler diffusion on a periodic ring; see REQUIREMENTS.md for units."""

from __future__ import annotations

import argparse
import csv
import math
from collections.abc import Sequence
from dataclasses import dataclass
from numbers import Real
from pathlib import Path


@dataclass(frozen=True)
class Solution:
    """A final field in kelvin, spacing in metres, and elapsed seconds."""

    temperature_K: tuple[float, ...]
    dx_m: float
    time_s: float


def _bounded_real(value: object, name: str, lower: float, upper: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a real number, not a boolean")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name} cannot be represented as a finite float") from exc
    if not math.isfinite(number) or not lower <= number <= upper:
        raise ValueError(f"{name} must be finite and in [{lower}, {upper}]")
    return number


def simulate(
    initial: Sequence[float],
    *,
    diffusivity_m2_s: float,
    dx_m: float,
    dt_s: float,
    steps: int,
) -> Solution:
    """Copy a valid field, then advance exactly ``steps`` simultaneous updates."""
    if not 3 <= len(initial) <= 256:
        raise ValueError("initial must contain 3..256 cells")
    temperatures = tuple(_bounded_real(v, "temperature_K", 0, 1e6) for v in initial)
    diffusivity = _bounded_real(diffusivity_m2_s, "diffusivity_m2_s", 0, 1e6)
    dx = _bounded_real(dx_m, "dx_m", 1e-6, 1e6)
    dt = _bounded_real(dt_s, "dt_s", 1e-6, 1e6)
    if isinstance(steps, bool) or not isinstance(steps, int) or not 0 <= steps <= 10000:
        raise ValueError("steps must be an integer in [0, 10000]")
    r = diffusivity * dt / (dx * dx)
    if r > 0.5:
        raise ValueError("explicit Euler requires D*dt/dx² <= 0.5")
    n = len(temperatures)
    for _ in range(steps):
        temperatures = tuple(
            temperatures[i]
            + r
            * (
                temperatures[(i - 1) % n]
                - 2 * temperatures[i]
                + temperatures[(i + 1) % n]
            )
            for i in range(n)
        )
    return Solution(temperatures, dx, steps * dt)


def write_csv(solution: Solution, path: str | Path) -> None:
    """Write standard float representations; I/O failures propagate to callers."""
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("x_m", "time_s", "temperature_K"))
        for i, value in enumerate(solution.temperature_K):
            writer.writerow((i * solution.dx_m, solution.time_s, value))


def main() -> None:
    """Write one second of diffusion from a 400 K cell on a 300 K ring."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    solution = simulate(
        [400, 300, 300, 300], diffusivity_m2_s=0.25, dx_m=1, dt_s=1, steps=1
    )
    write_csv(solution, args.output)


if __name__ == "__main__":
    main()
