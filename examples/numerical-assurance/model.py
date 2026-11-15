"""Forward Euler transfer between two closed stores; kg and days."""

import argparse
import csv
import math
from dataclasses import dataclass
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
    """Integrate dA/dt=-k*A, dB/dt=k*A with nonnegative Euler steps."""
    if not all(math.isfinite(x) for x in (a0, b0, rate, duration, dt, a0 + b0)):
        raise ValueError("inputs and total mass must be finite")
    if min(a0, b0, rate, duration) < 0 or dt <= 0:
        raise ValueError("masses, rate and duration must be nonnegative; dt positive")
    if rate * dt > 1:
        raise ValueError("nonnegative Euler steps require rate * dt <= 1")
    steps = duration / dt
    if not math.isfinite(steps) or steps > 100000:
        raise ValueError("requested integration exceeds the 100000-step limit")
    rows = [Sample(0.0, a0, b0)]
    count = 0 if duration == 0 else max(1, math.ceil(steps))
    for index in range(1, count + 1):
        previous = rows[-1]
        time = duration if index == count else min(index * dt, duration)
        if time == previous.time_days:
            continue
        step = min(dt, time - previous.time_days)
        transfer = rate * step * previous.a_kg
        rows.append(Sample(time, previous.a_kg - transfer, previous.b_kg + transfer))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a0", type=float, default=1000)
    parser.add_argument("--b0", type=float, default=0)
    parser.add_argument("--rate", type=float, default=0.2)
    parser.add_argument("--duration", type=float, default=10)
    parser.add_argument("--dt", type=float, default=0.1)
    parser.add_argument("--output", type=Path, default=Path("result.csv"))
    args = parser.parse_args()
    try:
        rows = simulate(args.a0, args.b0, args.rate, args.duration, args.dt)
        with args.output.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(("time_days", "a_kg", "b_kg", "total_tonnes"))
            for row in rows:
                writer.writerow((row.time_days, row.a_kg, row.b_kg, row.total_tonnes))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
