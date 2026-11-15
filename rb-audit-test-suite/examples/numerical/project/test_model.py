"""Oracles come from REQUIREMENTS.md, never from a mutated implementation."""
import csv
import math
import subprocess
import sys
from pathlib import Path

import model
from model import simulate

# An unexpected installed module must fail collection, not masquerade as a kill.
assert Path(model.__file__).resolve() == Path(__file__).with_name("model.py").resolve()


def test_direction():
    last = simulate(100, 20, .5, 1, 1)[-1]
    assert last.a_kg < 100 and last.b_kg > 20


def test_conservation():
    rows = simulate(100, 20, .5, 2, 1)
    assert all(row.a_kg + row.b_kg == 120 for row in rows)


def test_specified_rate():
    # One Euler step: transfer = .5/day * 1 day * 100 kg = 50 kg.
    last = simulate(100, 20, .5, 1, 1)[-1]
    assert (last.a_kg, last.b_kg) == (50, 70)


def test_fractional_endpoint():
    rows = simulate(100, 20, .5, 1.5, 1)
    assert [(r.time_days, r.a_kg, r.b_kg) for r in rows] == [
        (0, 100, 20), (1, 50, 70), (1.5, 37.5, 82.5)
    ]


def test_exported_units(tmp_path):
    output = tmp_path / "mass.csv"
    completed = subprocess.run(
        [sys.executable, str(Path(model.__file__)), "--output", str(output)],
        capture_output=True, text=True, timeout=5, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    with output.open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 101
    # Closed 1000 kg system is exactly 1 tonne, allowing accumulated rounding.
    assert all(abs(float(row["total_tonnes"]) - 1) < 1e-12 for row in rows)


def test_stability_rejected():
    rejected = False
    try:
        simulate(100, 20, 2, 1, 1)
    except ValueError:
        rejected = True
    assert rejected, "Euler steps with k*dt > 1 must be rejected"


def test_rounded_step_nonnegative():
    rows = simulate(1, 0, math.nextafter(10, 0), .5, .1)
    assert all(r.a_kg >= 0 and r.b_kg >= 0 for r in rows)


def test_underflow_final_time():
    rows = simulate(1, 0, 0, 1e-308, 1e308)
    assert len(rows) == 2
    assert rows[-1].time_days == 1e-308
    assert (rows[-1].a_kg, rows[-1].b_kg) == (1, 0)
