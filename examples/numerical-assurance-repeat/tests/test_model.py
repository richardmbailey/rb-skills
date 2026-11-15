import csv
import math
import subprocess
import sys
from dataclasses import FrozenInstanceError
from itertools import pairwise
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from model import Sample, simulate


def test_exact_steps():
    assert simulate(8, 2, 0.5, 1.5, 1) == [
        Sample(0, 8, 2),
        Sample(1, 4, 6),
        Sample(1.5, 3, 7),
    ]
    assert Sample(0, 750, 500).total_tonnes == 1.25
    with pytest.raises(FrozenInstanceError):
        Sample(0, 1, 2).a_kg = 3


@pytest.mark.parametrize("index", range(5))
@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, -1.0])
def test_invalid(index, bad):
    args = [10, 2, 0.25, 2, 0.5]
    args[index] = bad
    with pytest.raises(ValueError):
        simulate(*args)


@pytest.mark.parametrize(
    "args",
    [
        (1, 0, 1, 1, 0),
        (1, 0, 2, 1, 1),
        (1e308, 1e308, 0, 1, 1),
        (1, 0, 0, 100001, 1),
        (1, 0, 0, 1e308, 1e-308),
    ],
)
def test_invalid_combinations(args):
    with pytest.raises(ValueError):
        simulate(*args)


def test_boundaries():
    assert simulate(2, 3, 1, 0, 1) == [Sample(0, 2, 3)]
    assert simulate(2, 3, 0, 2, 1)[-1] == Sample(2, 2, 3)
    assert simulate(2, 3, 1, 1, 1)[-1] == Sample(1, 0, 5)
    with pytest.raises(ValueError):
        simulate(2, 3, math.nextafter(1, math.inf), 1, 1)
    assert simulate(2, 3, math.nextafter(1, 0), 1, 1)[-1].a_kg >= 0
    assert len(simulate(1, 0, 0, 100000, 1)) == 100001
    tiny = math.ulp(0.0)
    assert simulate(1, 0, 0, tiny, 1)[-1].time_days == tiny
    # Multiplication order must not overflow a finite transfer.
    assert simulate(1e308, 0, 1e308, 1e-308, 1e-308)[-1].b_kg > 9e307
    # A near-integer endpoint must not create a negative stability-boundary step.
    end = math.nextafter(10 * 0.1, math.inf)
    values = simulate(1, 0, 10, end, 0.1)
    assert values[-1].time_days == end
    assert all(v.a_kg >= 0 for v in values)


def test_analytic_and_convergence():
    exact = 1000 * math.exp(-2)
    errors = [
        abs(simulate(1000, 0, 0.2, 10, dt)[-1].a_kg - exact) for dt in [0.2, 0.1, 0.05]
    ]
    assert errors[1] <= 3
    assert all(1.9 <= a / b <= 2.1 for a, b in pairwise(errors))
    endpoint = simulate(1000, 0, 0.2, 10, 0.1)[-1]
    assert endpoint.a_kg <= exact
    assert abs(endpoint.b_kg - (1000 - exact)) <= 3


@given(
    a=st.floats(0, 1e8),
    b=st.floats(0, 1e8),
    fraction=st.floats(0, 1),
    steps=st.integers(1, 100),
    tail=st.sampled_from([0.0, 0.25, 0.5]),
)
@settings(max_examples=150, derandomize=True, deadline=None)
def test_properties(a, b, fraction, steps, tail):
    values = simulate(a, b, fraction, steps + tail, 1)
    assert values[0] == Sample(0, a, b)
    assert values[-1].time_days == steps + tail
    for previous, current in pairwise(values):
        assert 0 <= current.a_kg <= previous.a_kg
        assert current.b_kg >= previous.b_kg
        assert current.time_days > previous.time_days
        assert abs(current.a_kg + current.b_kg - a - b) <= 1e-12 * max(1, a + b)


def cli(*args):
    return subprocess.run(
        [sys.executable, str(Path(__file__).parents[1] / "model.py"), *map(str, args)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_cli_roundtrip(tmp_path):
    output = tmp_path / "result.csv"
    result = cli(
        "--output",
        output,
        "--a0",
        8,
        "--b0",
        2,
        "--rate",
        0.5,
        "--duration",
        1.5,
        "--dt",
        1,
    )
    assert result.returncode == 0, result.stderr
    with output.open() as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == ["time_days", "a_kg", "b_kg", "total_tonnes"]
        rows = [{key: float(value) for key, value in row.items()} for row in reader]
    assert rows == [
        {"time_days": t, "a_kg": a, "b_kg": b, "total_tonnes": 0.01}
        for t, a, b in [(0, 8, 2), (1, 4, 6), (1.5, 3, 7)]
    ]


def test_cli_default_and_errors(tmp_path):
    output = tmp_path / "result.csv"
    assert cli("--output", output).returncode == 0
    with output.open() as stream:
        rows = list(csv.DictReader(stream))
    assert float(rows[-1]["time_days"]) == 10
    assert abs(float(rows[-1]["a_kg"]) - 1000 * math.exp(-2)) <= 3
    absent = tmp_path / "absent.csv"
    assert cli("--output", absent, "--dt", -1).returncode != 0
    assert not absent.exists()
    assert cli("--output", tmp_path).returncode != 0
