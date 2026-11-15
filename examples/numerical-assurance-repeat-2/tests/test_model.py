import csv
import math
import subprocess
import sys
from itertools import pairwise
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from model import Sample, simulate


def test_euler_and_short_final_step():
    assert simulate(8, 2, 0.5, 1.5, 1) == [
        Sample(0, 8, 2),
        Sample(1, 4, 6),
        Sample(1.5, 3, 7),
    ]


def test_immutable_and_units():
    sample = Sample(0, 750, 250)
    assert sample.total_tonnes == 1
    with pytest.raises(AttributeError):
        sample.a_kg = 0


@pytest.mark.parametrize("index", range(5))
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), -1])
def test_invalid(index, value):
    inputs = [10, 2, 0.1, 1, 0.5]
    inputs[index] = value
    with pytest.raises(ValueError):
        simulate(*inputs)


@pytest.mark.parametrize(
    "inputs",
    [
        (1, 1, 1, 1, 0),
        (1, 1, 2, 1, 1),
        (1e308, 1e308, 0, 1, 1),
        (1, 0, 0, 100001, 1),
        (1, 0, 0, 1e308, 1e-308),
    ],
)
def test_rejected_boundaries(inputs):
    with pytest.raises(ValueError):
        simulate(*inputs)


def test_supported_boundaries():
    assert simulate(2, 3, 0, 0, 1) == [Sample(0, 2, 3)]
    assert simulate(2, 3, 0, 1.5, 1)[-1] == Sample(1.5, 2, 3)
    assert simulate(2, 3, 1, 1, 1)[-1] == Sample(1, 0, 5)
    assert len(simulate(0, 0, 0, 100000, 1)) == 100001
    tiny = math.ulp(0.0)
    assert simulate(1, 0, 0, tiny, 1)[-1].time_days == tiny
    with pytest.raises(ValueError):
        simulate(1, 0, math.nextafter(1, math.inf), 1, 1)


@settings(max_examples=100, derandomize=True, deadline=None)
@given(
    a=st.floats(0, 1e6, allow_nan=False, allow_infinity=False),
    b=st.floats(0, 1e6, allow_nan=False, allow_infinity=False),
    rate=st.floats(0, 1, allow_nan=False, allow_infinity=False),
    duration=st.floats(0, 20, allow_nan=False, allow_infinity=False),
)
def test_trajectory_properties(a, b, rate, duration):
    values = simulate(a, b, rate, duration, 0.25)
    tolerance = 1e-12 * max(1, a + b)
    assert values[-1].time_days == duration
    for value in values:
        assert value.a_kg >= 0 and value.b_kg >= 0
        assert abs(value.a_kg + value.b_kg - a - b) <= tolerance
    for left, right in pairwise(values):
        assert left.time_days < right.time_days
        assert left.a_kg >= right.a_kg
        assert left.b_kg <= right.b_kg


def test_analytic_accuracy_and_convergence():
    exact = 1000 * math.exp(-2)
    errors = [
        abs(simulate(1000, 0, 0.2, 10, dt)[-1].a_kg - exact) for dt in [0.2, 0.1, 0.05]
    ]
    assert errors[1] <= 3
    assert all(1.9 <= x / y <= 2.1 for x, y in pairwise(errors))
    final = simulate(1000, 0, 0.2, 10, 0.1)[-1]
    assert abs(final.b_kg - (1000 - exact)) <= 3


def test_cli_roundtrip(tmp_path):
    output = tmp_path / "result.csv"
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "model.py"),
            "--output",
            str(output),
            "--a0",
            "8",
            "--b0",
            "2",
            "--rate",
            "0.5",
            "--duration",
            "1.5",
            "--dt",
            "1",
        ],
        check=False,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    with output.open() as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == ["time_days", "a_kg", "b_kg", "total_tonnes"]
        rows = list(reader)
    assert [[float(row[key]) for key in reader.fieldnames] for row in rows] == [
        [0, 8, 2, 0.01],
        [1, 4, 6, 0.01],
        [1.5, 3, 7, 0.01],
    ]


@pytest.mark.parametrize("failure", ["invalid", "io"])
def test_cli_failure(tmp_path, failure):
    output = tmp_path / "absent.csv" if failure == "invalid" else tmp_path
    args = ["--dt", "0"] if failure == "invalid" else []
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "model.py"),
            "--output",
            str(output),
            *args,
        ],
        check=False,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode != 0
    if failure == "invalid":
        assert not output.exists()


def test_runtime_identity(record_testsuite_property):
    import hashlib

    import model

    origin = Path(model.__file__).resolve()
    assert origin == Path(__file__).resolve().parents[1] / "model.py"
    record_testsuite_property("model_origin", str(origin))
    record_testsuite_property(
        "model_sha256", hashlib.sha256(origin.read_bytes()).hexdigest()
    )
