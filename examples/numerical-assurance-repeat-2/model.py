"""Closed two-store forward Euler teaching model; days and kilograms."""

import argparse
import csv
import math
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


@dataclass(frozen=True)
class Sample:
    time_days: float
    a_kg: float
    b_kg: float

    @property
    def total_tonnes(self) -> float:
        return (self.a_kg + self.b_kg) / 1000


def simulate(
    a0: float, b0: float, rate: float, duration: float, dt: float
) -> list[Sample]:
    """Return initial and Euler states, with a shortened final interval."""
    if not all(math.isfinite(x) for x in (a0, b0, rate, duration, dt)):
        raise ValueError("All inputs must be finite")
    if min(a0, b0, rate, duration) < 0 or dt <= 0:
        raise ValueError("Mass, rate and duration must be nonnegative; dt positive")
    if rate * dt > 1:
        raise ValueError("Euler stability requires rate * dt <= 1")
    if not math.isfinite(a0 + b0):
        raise ValueError("Total mass must be finite")
    # Exact binary-float ratio avoids overflow/underflow in duration / dt.
    steps = math.ceil(Fraction(duration) / Fraction(dt))
    if steps > 100000:
        raise ValueError("At most 100000 steps are allowed")
    values = [Sample(0, a0, b0)]
    a, b = a0, b0
    for index in range(steps):
        h = min(dt, duration - index * dt)
        fraction = rate * h
        transfer = a * fraction
        a, b = a * (1 - fraction), b + transfer
        time = duration if index == steps - 1 else (index + 1) * dt
        values.append(Sample(time, a, b))
        # A rounded regular timestamp can already equal the requested endpoint.
        if time >= duration:
            break
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    for name, default in [
        ("a0", 1000),
        ("b0", 0),
        ("rate", 0.2),
        ("duration", 10),
        ("dt", 0.1),
    ]:
        parser.add_argument(f"--{name}", type=float, default=default)
    args = parser.parse_args()
    try:
        samples = simulate(args.a0, args.b0, args.rate, args.duration, args.dt)
        with args.output.open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["time_days", "a_kg", "b_kg", "total_tonnes"])
            for sample in samples:
                writer.writerow(
                    [sample.time_days, sample.a_kg, sample.b_kg, sample.total_tonnes]
                )
    except (ValueError, OSError) as error:
        parser.exit(1, f"{error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
