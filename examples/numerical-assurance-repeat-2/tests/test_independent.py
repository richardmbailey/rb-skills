"""Independent acceptance design, frozen before candidate access or execution."""

import csv
import importlib.util
import itertools
import math
import subprocess
import sys
from pathlib import Path

import pytest

MODEL_PATH = Path(__file__).resolve().parents[1] / "model.py"


@pytest.fixture(scope="module")
def model():
    spec = importlib.util.spec_from_file_location("independent_model", MODEL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_exact_simultaneous_transfer_and_short_final_step(model):
    # Transfers: 2 kg, 1 kg, then 0.25 kg with h=0.25.
    samples = model.simulate(4, 3, 1, 1.25, 0.5)
    assert [(s.time_days, s.a_kg, s.b_kg) for s in samples] == [
        (0, 4, 3),
        (0.5, 2, 5),
        (1, 1, 6),
        (1.25, 0.75, 6.25),
    ]
    assert all(s.total_tonnes == 0.007 for s in samples)
    with pytest.raises((AttributeError, TypeError)):
        samples[0].a_kg = 9


@pytest.mark.parametrize(
    "a,b,k,t,h",
    [
        (0, 0, 0, 0, 1),
        (0, 7, 0.5, 3, 0.5),
        (7, 5, 0, 3.25, 0.5),
        (7, 5, 1, 0, 0.5),
        (7, 5, 2, 1.25, 0.5),
        (1e-10, 3e-10, 0.3, 7.1, 0.25),
        (1e10, 3e10, 0.3, 7.1, 0.25),
        (1000, 0, 0.2, 10, 0.1),
    ],
)
def test_bounded_trajectory_invariants(model, a, b, k, t, h):
    samples = model.simulate(a, b, k, t, h)
    assert isinstance(samples, list)
    assert samples[0].time_days == 0
    assert samples[-1].time_days == t
    assert len(samples) == math.ceil(t / h) + 1
    allowance = 1e-12 * max(1, a + b)
    for s in samples:
        assert math.isfinite(s.a_kg) and math.isfinite(s.b_kg)
        assert s.a_kg >= 0 and s.b_kg >= 0
        assert abs(s.a_kg + s.b_kg - a - b) <= allowance
        assert s.total_tonnes == (s.a_kg + s.b_kg) / 1000
        if k == 0:
            assert (s.a_kg, s.b_kg) == (a, b)
    for previous, current in itertools.pairwise(samples):
        assert previous.time_days < current.time_days <= t
        assert current.a_kg <= previous.a_kg
        assert current.b_kg >= previous.b_kg
    if k * h == 1 and t >= h:
        assert samples[1].a_kg == 0
        assert samples[1].b_kg == a + b


def test_continuous_reference_and_first_order_convergence(model):
    exact = 1000 * math.exp(-2)
    errors = []
    for h in (0.2, 0.1, 0.05):
        final = model.simulate(1000, 0, 0.2, 10, h)[-1]
        error = exact - final.a_kg
        assert error > 0
        assert abs(final.b_kg - (1000 - exact)) == pytest.approx(error, abs=1e-9)
        errors.append(error)
    assert errors[1] <= 3
    for coarse, fine in itertools.pairwise(errors):
        assert 1.9 <= coarse / fine <= 2.1


@pytest.mark.parametrize("index", range(5))
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_rejects_every_nonfinite_input(model, index, bad):
    arguments = [4, 3, 0.5, 1, 0.5]
    arguments[index] = bad
    with pytest.raises(ValueError):
        model.simulate(*arguments)


@pytest.mark.parametrize(
    "arguments",
    [
        (-1, 0, 0, 0, 1),
        (1, -1, 0, 0, 1),
        (1, 0, -1, 0, 1),
        (1, 0, 0, -1, 1),
        (1, 0, 0, 1, 0),
        (1, 0, 0, 1, -1),
        (1, 0, 2.01, 1, 0.5),
        (1e308, 1e308, 0, 0, 1),
        (1, 0, 0, 100000.25, 1),
        (1, 0, 0, 1e308, 1e-308),
    ],
)
def test_rejects_invalid_domains_and_resource_excess(model, arguments):
    with pytest.raises(ValueError):
        model.simulate(*arguments)


def test_exact_step_cap_is_supported(model):
    samples = model.simulate(1, 2, 0, 100000, 1)
    assert len(samples) == 100001
    assert samples[-1].time_days == 100000
    assert (samples[-1].a_kg, samples[-1].b_kg) == (1, 2)


def run_cli(output, *args):
    return subprocess.run(
        [sys.executable, str(MODEL_PATH), "--output", str(output), *args],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def read_rows(output):
    with output.open(newline="") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == ["time_days", "a_kg", "b_kg", "total_tonnes"]
        return [{key: float(value) for key, value in row.items()} for row in reader]


def test_actual_cli_custom_exact_case(tmp_path):
    output = tmp_path / "custom.csv"
    result = run_cli(
        output,
        "--a0",
        "4",
        "--b0",
        "3",
        "--rate",
        "1",
        "--duration",
        "1.25",
        "--dt",
        "0.5",
    )
    assert result.returncode == 0, result.stderr
    rows = read_rows(output)
    assert rows == [
        dict(zip(["time_days", "a_kg", "b_kg", "total_tonnes"], values))
        for values in [
            (0, 4, 3, 0.007),
            (0.5, 2, 5, 0.007),
            (1, 1, 6, 0.007),
            (1.25, 0.75, 6.25, 0.007),
        ]
    ]


def test_actual_cli_defaults_against_discrete_closed_form(tmp_path):
    output = tmp_path / "defaults.csv"
    result = run_cli(output)
    assert result.returncode == 0, result.stderr
    rows = read_rows(output)
    assert len(rows) == 101
    for index, row in enumerate(rows):
        a = 1000 * (0.98**index)
        assert row["time_days"] == pytest.approx(index / 10, abs=1e-12)
        assert row["a_kg"] == pytest.approx(a, abs=1e-9)
        assert row["b_kg"] == pytest.approx(1000 - a, abs=1e-9)
        assert row["total_tonnes"] == pytest.approx(1, abs=1e-12)


@pytest.mark.parametrize(
    "args",
    [
        ("--a0", "-1"),
        ("--b0", "nan"),
        ("--rate", "20"),
        ("--duration", "-1"),
        ("--dt", "0"),
        ("--duration", "10001"),
    ],
)
def test_actual_cli_invalid_does_not_create_output(tmp_path, args):
    output = tmp_path / "invalid.csv"
    result = run_cli(output, *args)
    assert result.returncode != 0
    assert not output.exists()


def test_actual_cli_output_io_failure(tmp_path):
    result = run_cli(tmp_path)
    assert result.returncode != 0


# Post-inspection regression: not part of the independent frozen design.
def test_no_duplicate_endpoint_when_float_grid_rounds_to_duration(model):
    samples = model.simulate(4, 3, 1, 1, 1 / 3)
    assert all(
        left.time_days < right.time_days for left, right in itertools.pairwise(samples)
    )
    assert samples[-1].time_days == 1
