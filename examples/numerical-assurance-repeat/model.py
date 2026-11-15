"""Closed two-store Euler teaching model; days, kilograms, inverse days."""

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
    """Apply one simultaneous transfer per step, retaining the exact endpoint."""
    if not all(math.isfinite(x) for x in (a0, b0, rate, duration, dt)):
        raise ValueError("inputs must be finite")
    if min(a0, b0, rate, duration) < 0 or dt <= 0:
        raise ValueError("masses, rate, duration must be nonnegative; dt positive")
    if rate * dt > 1:
        raise ValueError("rate * dt must not exceed one")
    if not math.isfinite(a0 + b0):
        raise ValueError("total mass must be finite")
    # Exact ratios avoid overflow/underflow and rounded division at the step cap.
    span, stride = Fraction(duration), Fraction(dt)
    quotient, remainder = divmod(span, stride)
    count = quotient + bool(remainder)
    if count <= 100001 and count > 0 and (count - 1) * dt >= duration:
        count -= 1
    if count > 100000:
        raise ValueError("at most 100000 steps are permitted")
    samples = [Sample(0.0, a0, b0)]
    a, b = a0, b0
    for index in range(1, count + 1):
        last = index == count
        step = min(dt, float(span - (count - 1) * stride)) if last else dt
        transfer = a * (rate * step)
        a, b = a - transfer, b + transfer
        samples.append(Sample(duration if last else index * dt, a, b))
    return samples


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    for name, default in (
        ("a0", 1000),
        ("b0", 0),
        ("rate", 0.2),
        ("duration", 10),
        ("dt", 0.1),
    ):
        parser.add_argument(f"--{name}", type=float, default=default)
    args = parser.parse_args()
    try:
        values = simulate(args.a0, args.b0, args.rate, args.duration, args.dt)
        with args.output.open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(("time_days", "a_kg", "b_kg", "total_tonnes"))
            writer.writerows(
                (s.time_days, s.a_kg, s.b_kg, s.total_tonnes) for s in values
            )
    except (ValueError, OSError) as exc:
        parser.exit(1, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
