"""Requirement-only tests designed before viewing or importing the candidate."""

import csv
import importlib.util
import math
import subprocess
import sys
from itertools import pairwise
from pathlib import Path

import pytest

MODEL = Path(__file__).resolve().parents[1] / "model.py"


@pytest.fixture(scope="module")
def candidate():
    spec = importlib.util.spec_from_file_location("independent_repeat_model", MODEL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_exact_simultaneous_transfer_and_short_final_step(candidate):
    samples = candidate.simulate(8, 3, 0.5, 1.25, 0.5)
    assert [(s.time_days, s.a_kg, s.b_kg) for s in samples] == [
        (0, 8, 3),
        (0.5, 6, 5),
        (1, 4.5, 6.5),
        (1.25, 3.9375, 7.0625),
    ]
    assert all(s.total_tonnes == 0.011 for s in samples)
    with pytest.raises((AttributeError, TypeError)):
        samples[0].a_kg = 99


def test_continuous_reference_and_first_order_convergence(candidate):
    # Integrate A'=-kA; conservation then gives B. No candidate-derived oracle.
    exact_a = 1000 * math.exp(-2)
    errors = []
    for dt in (0.2, 0.1, 0.05):
        end = candidate.simulate(1000, 7, 0.2, 10, dt)[-1]
        assert end.time_days == 10
        error = exact_a - end.a_kg
        assert error > 0  # Euler depletes A faster than the exponential.
        assert abs(end.b_kg - (1007 - exact_a)) == pytest.approx(error, abs=1e-9)
        errors.append(error)
    assert errors[1] <= 3
    assert all(1.9 <= coarse / fine <= 2.1 for coarse, fine in pairwise(errors))


@pytest.mark.parametrize(
    "a0,b0,rate,duration,dt",
    [(123.5, 7.25, 0.4, 3.125, 0.25), (0, 90, 2, 1, 0.5), (8, 3, 2, 1.25, 0.5)],
)
def test_physical_invariants(candidate, a0, b0, rate, duration, dt):
    samples = candidate.simulate(a0, b0, rate, duration, dt)
    tolerance = 1e-12 * max(1, a0 + b0)
    assert samples[0].time_days == 0
    assert samples[-1].time_days == duration
    for sample in samples:
        assert sample.a_kg >= 0 and sample.b_kg >= 0
        assert abs(sample.a_kg + sample.b_kg - (a0 + b0)) <= tolerance
    for left, right in pairwise(samples):
        assert right.time_days > left.time_days
        assert right.a_kg <= left.a_kg and right.b_kg >= left.b_kg


def test_zero_limits_and_stability_boundary(candidate):
    assert len(candidate.simulate(8, 3, 0.5, 0, 0.5)) == 1
    idle = candidate.simulate(8, 3, 0, 1.25, 0.5)
    assert [(s.a_kg, s.b_kg) for s in idle] == [(8, 3)] * 4
    boundary = candidate.simulate(8, 3, 2, 1, 0.5)
    assert [(s.a_kg, s.b_kg) for s in boundary] == [(8, 3), (0, 11), (0, 11)]


@pytest.mark.parametrize("index", range(5))
@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_all_inputs_must_be_finite(candidate, index, bad):
    values = [8, 3, 0.5, 1, 0.5]
    values[index] = bad
    with pytest.raises(ValueError):
        candidate.simulate(*values)


@pytest.mark.parametrize("index", range(5))
def test_negative_inputs_rejected(candidate, index):
    values = [8, 3, 0.5, 1, 0.5]
    values[index] = -0.25
    with pytest.raises(ValueError):
        candidate.simulate(*values)


@pytest.mark.parametrize(
    "values",
    [
        (8, 3, 0.5, 1, 0),
        (8, 3, 2.01, 1, 0.5),
        (1e308, 1e308, 0, 1, 1),
        (8, 3, 0, 100001, 1),
        (8, 3, 0, 1e308, 1e-308),
    ],
)
def test_invalid_total_stability_and_step_budget(candidate, values):
    with pytest.raises(ValueError):
        candidate.simulate(*values)


def test_exact_step_cap_supported(candidate):
    samples = candidate.simulate(0, 3, 0, 100000, 1)
    assert len(samples) == 100001
    assert samples[-1].time_days == 100000


def test_decimal_grid_does_not_add_spurious_step(candidate):
    samples = candidate.simulate(8, 3, 0.5, 0.3, 0.1)
    assert len(samples) == 4
    assert samples[-1].time_days == 0.3


def test_finite_large_mass_does_not_overflow_transfer(candidate):
    end = candidate.simulate(1e308, 0, 2, 0.25, 0.25)[-1]
    assert end.a_kg == pytest.approx(5e307)
    assert end.b_kg == pytest.approx(5e307)


def test_real_cli_round_trip(candidate, tmp_path):
    del candidate  # Ensure import was possible, but exercise the script separately.
    output = tmp_path / "result.csv"
    result = subprocess.run(
        [
            sys.executable,
            str(MODEL),
            "--a0",
            "8",
            "--b0",
            "3",
            "--rate",
            "0.5",
            "--duration",
            "1.25",
            "--dt",
            "0.5",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    with output.open(newline="") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == ["time_days", "a_kg", "b_kg", "total_tonnes"]
        rows = list(reader)
    assert [float(row["time_days"]) for row in rows] == [0, 0.5, 1, 1.25]
    assert [float(row["a_kg"]) for row in rows] == [8, 6, 4.5, 3.9375]
    assert [float(row["b_kg"]) for row in rows] == [3, 5, 6.5, 7.0625]
    assert [float(row["total_tonnes"]) for row in rows] == [0.011] * 4


def test_cli_rejects_before_creation_and_reports_io_error(tmp_path):
    output = tmp_path / "absent.csv"
    rejected = subprocess.run(
        [sys.executable, str(MODEL), "--rate", "-1", "--output", str(output)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert rejected.returncode != 0
    assert not output.exists()
    io_error = subprocess.run(
        [sys.executable, str(MODEL), "--output", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert io_error.returncode != 0


def test_post_inspection_rounded_grid_endpoint_has_no_duplicate_time(candidate):
    """Review regression: exact-ratio counting can add a rounded duplicate."""
    duration = 3 * 0.1
    samples = candidate.simulate(8, 3, 0.5, duration, 0.1)
    assert samples[-1].time_days == duration
    assert all(left.time_days < right.time_days for left, right in pairwise(samples))
