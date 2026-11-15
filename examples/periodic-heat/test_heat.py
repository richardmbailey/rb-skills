"""Deterministic verification; references are derived in TEST_DESIGN.md."""

import csv
import math
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import heat

HERE = Path(__file__).resolve().parent


def solve(values, **kwargs):
    parameters = dict(diffusivity_m2_s=0.25, dx_m=1.0, dt_s=1.0, steps=1)
    parameters.update(kwargs)
    return heat.simulate(values, **parameters)


def test_import_origin():
    origin = Path(heat.__file__).resolve()
    print(f"ACTUAL_IMPORT_ORIGIN={origin}")
    assert origin == HERE / "heat.py"


def test_hand_worked_periodic_simultaneous_step():
    assert solve([400, 300, 300, 300]).temperature_K == (350, 325, 300, 325)
    assert solve([4, 0, 0], steps=2).temperature_K == (1.5, 1.25, 1.25)


def test_result_copy_frozen_and_time():
    values = [400, 300, 300]
    result = solve(values, dt_s=0.5, steps=3)
    assert values == [400, 300, 300]
    values[0] = 0
    assert isinstance(result.temperature_K, tuple)
    assert len(result.temperature_K) == 3
    assert result.time_s == 1.5
    assert result.dx_m == 1
    with pytest.raises(FrozenInstanceError):
        result.time_s = 0


@pytest.mark.parametrize("steps", [0, 1, 10000])
def test_zero_diffusion(steps):
    initial = [0.1, 1e6, 17.125]
    assert solve(initial, diffusivity_m2_s=0, steps=steps).temperature_K == tuple(
        initial
    )


def test_zero_steps():
    assert solve([1, 2, 3], steps=0).temperature_K == (1, 2, 3)
    assert solve([1, 2, 3], steps=0).time_s == 0


@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), -float("inf"), True, "1", None]
)
@pytest.mark.parametrize("field", ["diffusivity_m2_s", "dx_m", "dt_s"])
def test_invalid_scalar(field, value):
    with pytest.raises(ValueError):
        solve([1, 2, 3], **{field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("diffusivity_m2_s", -1),
        ("diffusivity_m2_s", 1000001),
        ("dx_m", 0),
        ("dx_m", math.nextafter(1e-6, 0)),
        ("dx_m", 1000001),
        ("dt_s", 0),
        ("dt_s", math.nextafter(1e-6, 0)),
        ("dt_s", 1000001),
        ("steps", -1),
        ("steps", 10001),
        ("steps", True),
        ("steps", 1.0),
        ("steps", float("nan")),
        ("steps", "1"),
    ],
)
def test_invalid_parameter_range(field, value):
    with pytest.raises(ValueError):
        solve([1, 2, 3], **{field: value})


@pytest.mark.parametrize(
    "values",
    [
        [],
        [1, 2],
        [1] * 257,
        [-1, 1, 2],
        [1000001, 1, 2],
        [True, 1, 2],
        ["1", 1, 2],
        [None, 1, 2],
        [float("nan"), 1, 2],
        [float("inf"), 1, 2],
        [-float("inf"), 1, 2],
    ],
)
def test_invalid_initial(values):
    with pytest.raises(ValueError):
        solve(values)


@pytest.mark.parametrize(
    "dx,dt,d", [(1e-6, 1e-6, 0), (1e6, 1e6, 0.5e6), (1e6, 1e-6, 1e6)]
)
def test_inclusive_domain_endpoints(dx, dt, d):
    result = solve([0, 1e6] * 128, dx_m=dx, dt_s=dt, diffusivity_m2_s=d)
    assert len(result.temperature_K) == 256
    assert all(0 <= v <= 1e6 for v in result.temperature_K)


@pytest.mark.parametrize("r", [math.nextafter(0.5, 0), 0.5])
def test_stability_accepted(r):
    assert solve([0, 100, 0, 100], diffusivity_m2_s=r).temperature_K == pytest.approx(
        [200 * r, 100 - 200 * r, 200 * r, 100 - 200 * r], rel=0, abs=1e-13
    )


@pytest.mark.parametrize("steps", [0, 1])
def test_stability_rejected(steps):
    with pytest.raises(ValueError):
        solve([1, 2, 3], diffusivity_m2_s=math.nextafter(0.5, math.inf), steps=steps)


@pytest.mark.parametrize("r", [0.01, 0.25, 0.5])
def test_conservation_bounds_and_constants(r):
    initial = [0, 1e6, 37, 999999, 0.001, 713]
    final = solve(initial, diffusivity_m2_s=r, steps=10000).temperature_K
    assert math.fsum(final) / len(final) == pytest.approx(
        math.fsum(initial) / len(initial), rel=0, abs=2e-5
    )
    assert min(final) >= min(initial) - 2e-5
    assert max(final) <= max(initial) + 2e-5
    assert (
        solve([273.15] * 7, diffusivity_m2_s=r, steps=100).temperature_K
        == (273.15,) * 7
    )


def test_shift_symmetry():
    values = [0.1, 1000, 37, 999999, 1]
    final = solve(values, steps=19).temperature_K
    shifted = solve(values[2:] + values[:2], steps=19).temperature_K
    assert shifted == final[2:] + final[:2]


@pytest.mark.parametrize("mode", [1, 7, 16])
@pytest.mark.parametrize("r", [0.2, 0.5])
@pytest.mark.parametrize("steps", [1, 37])
def test_discrete_fourier(mode, r, steps):
    n = 32
    initial = [300 + 10 * math.cos(2 * math.pi * mode * i / n) for i in range(n)]
    amplitude = 10 * (1 - 4 * r * math.sin(math.pi * mode / n) ** 2) ** steps
    expected = [
        300 + amplitude * math.cos(2 * math.pi * mode * i / n) for i in range(n)
    ]
    assert solve(
        initial, diffusivity_m2_s=r, steps=steps
    ).temperature_K == pytest.approx(expected, rel=0, abs=1e-10)


def test_continuum_convergence():
    errors = []
    for n in (16, 32, 64):
        dx = 1 / n
        initial = [300 + 10 * math.cos(2 * math.pi * i / n) for i in range(n)]
        final = solve(
            initial, diffusivity_m2_s=1, dx_m=dx, dt_s=0.25 * dx**2, steps=n * n // 16
        )
        expected = 300 + 10 * math.exp(-4 * math.pi**2 / 64)
        error = abs(final.temperature_K[0] - expected)
        assert final.time_s == 1 / 64
        assert 4 / n**2 < error < 7 / n**2
        errors.append(error)
    assert all(3.8 < a / b < 4.2 for a, b in zip(errors, errors[1:]))


def read_csv(path):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == ["x_m", "time_s", "temperature_K"]
        return [tuple(float(row[key]) for key in reader.fieldnames) for row in reader]


def test_csv_roundtrip(tmp_path):
    result = solve([301.1, 277.5, 399.125, 0], dx_m=0.3, dt_s=0.1, steps=7)
    path = tmp_path / "field.csv"
    heat.write_csv(result, path)
    assert read_csv(path) == [
        (i * result.dx_m, result.time_s, value)
        for i, value in enumerate(result.temperature_K)
    ]


def test_csv_failure(tmp_path):
    with pytest.raises(OSError):
        heat.write_csv(solve([1, 2, 3]), tmp_path / "absent" / "field.csv")


def test_cli_roundtrip_and_failure(tmp_path):
    output = tmp_path / "demo.csv"
    command = [sys.executable, str(HERE / "heat.py"), "--output", str(output)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert read_csv(output) == [(0, 1, 350), (1, 1, 325), (2, 1, 300), (3, 1, 325)]
    command[-1] = str(tmp_path / "absent" / "demo.csv")
    failed = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert failed.returncode != 0
    assert not Path(command[-1]).exists()


def test_unrepresentable_real_rejected():
    with pytest.raises(ValueError):
        solve([1, 2, 3], diffusivity_m2_s=10**400)
    with pytest.raises(ValueError):
        solve([10**400, 1, 2])
