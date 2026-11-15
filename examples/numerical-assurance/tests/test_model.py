"""Behavioural tests derived from the example's frozen requirements."""

import csv
import math
import subprocess
import sys
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from model import simulate

ROOT = Path(__file__).resolve().parents[1]


def test_single_step_and_fractional_endpoint():
    rows = simulate(100.0, 20.0, 0.5, 1.5, 1.0)
    assert [(r.time_days, r.a_kg, r.b_kg) for r in rows] == [
        (0.0, 100.0, 20.0),
        (1.0, 50.0, 70.0),
        (1.5, 37.5, 82.5),
    ]


def test_zero_duration_rate_and_positivity_boundary():
    assert len(simulate(100.0, 20.0, 0.5, 0.0, 1.0)) == 1
    assert all(r.a_kg == 100 and r.b_kg == 20 for r in simulate(100, 20, 0, 2, 1))
    last = simulate(100, 20, 1, 1, 1)[-1]
    assert (last.a_kg, last.b_kg) == (0, 120)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("position", range(5))
def test_nonfinite_inputs_rejected(position, value):
    inputs = [100.0, 20.0, 0.5, 1.5, 1.0]
    inputs[position] = value
    with pytest.raises(ValueError):
        simulate(*inputs)


@pytest.mark.parametrize(
    "inputs",
    [
        (-1, 0, 0.1, 1, 1),
        (1, -1, 0.1, 1, 1),
        (1, 0, -0.1, 1, 1),
        (1, 0, 0.1, -1, 1),
        (1, 0, 0.1, 1, 0),
        (1, 0, 0.1, 1, -1),
        (1, 0, 2, 1, 1),
        (1, 0, 0, 100001, 1),
        (1, 0, 0, 1e308, 1e-308),
        (1e308, 1e308, 0, 1, 1),
    ],
)
def test_invalid_parameters_rejected(inputs):
    with pytest.raises(ValueError):
        simulate(*inputs)


@settings(max_examples=150, derandomize=True, deadline=None)
@given(
    a=st.floats(0, 1e6, allow_nan=False, allow_infinity=False),
    b=st.floats(0, 1e6, allow_nan=False, allow_infinity=False),
    rate=st.floats(0, 1, allow_nan=False, allow_infinity=False),
    dt=st.floats(0.01, 1, allow_nan=False, allow_infinity=False),
    steps=st.integers(1, 100),
)
def test_conservation_direction_and_nonnegativity(a, b, rate, dt, steps):
    rows = simulate(a, b, rate, steps * dt, dt)
    tolerance = 1e-12 * max(1, a + b)
    assert rows[-1].time_days == steps * dt
    for row in rows:
        assert row.a_kg >= 0 and row.b_kg >= 0
        assert abs(row.a_kg + row.b_kg - (a + b)) <= tolerance
    for previous, row in zip(rows, rows[1:], strict=False):
        assert row.time_days > previous.time_days
        assert row.a_kg <= previous.a_kg
        assert row.b_kg >= previous.b_kg


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(ROOT / "model.py"), *args],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def test_csv_round_trip_and_exported_units(tmp_path):
    output = tmp_path / "path with spaces.csv"
    result = run_cli("--output", str(output))
    assert result.returncode == 0, result.stderr
    with output.open(newline="") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == ["time_days", "a_kg", "b_kg", "total_tonnes"]
        rows = list(reader)
    assert len(rows) == 101
    assert float(rows[0]["a_kg"]) == 1000
    assert float(rows[-1]["time_days"]) == 10
    assert abs(float(rows[-1]["a_kg"]) - 1000 * math.exp(-2)) < 3
    assert all(abs(float(row["total_tonnes"]) - 1) < 1e-12 for row in rows)


def test_invalid_cli_does_not_create_output(tmp_path):
    output = tmp_path / "must-not-exist.csv"
    result = run_cli("--output", str(output), "--dt", "-1")
    assert result.returncode != 0
    assert not output.exists()


def test_cli_output_error_is_nonzero(tmp_path):
    assert run_cli("--output", str(tmp_path)).returncode != 0


def test_decimal_step_rounding_does_not_duplicate_endpoint():
    rows = simulate(100, 0, 0.2, 0.07, 0.01)
    assert rows[-1].time_days == 0.07
    assert all(a.time_days < b.time_days for a, b in zip(rows, rows[1:], strict=False))
