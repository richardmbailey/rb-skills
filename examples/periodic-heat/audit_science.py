"""Independent equation-derived numerical checks; bounds predate implementation read."""

import math
from pathlib import Path

import heat


def test_import_origin():
    assert (
        Path(heat.__file__).resolve() == Path(__file__).with_name("heat.py").resolve()
    )


def test_independent_hand_steps():
    values = (4.0, 0.0, 0.0, 0.0)
    one = heat.simulate(values, diffusivity_m2_s=1, dx_m=1, dt_s=0.25, steps=1)
    two = heat.simulate(values, diffusivity_m2_s=1, dx_m=1, dt_s=0.25, steps=2)
    assert one.temperature_K == (2, 1, 0, 1)
    assert two.temperature_K == (1.5, 1, 0.5, 1)
    assert two.time_s == 0.5


def test_independent_discrete_fourier():
    n, k, r, steps = 32, 2, 0.2, 19
    initial = tuple(280 + 7 * math.cos(2 * math.pi * k * j / n) for j in range(n))
    solution = heat.simulate(initial, diffusivity_m2_s=1, dx_m=1, dt_s=r, steps=steps)
    factor = (1 - 4 * r * math.sin(math.pi * k / n) ** 2) ** steps
    expected = tuple(
        280 + 7 * factor * math.cos(2 * math.pi * k * j / n) for j in range(n)
    )
    assert max(abs(a - b) for a, b in zip(solution.temperature_K, expected)) < 2e-12


def test_independent_continuum_convergence():
    errors = []
    for n in (16, 32, 64):
        initial = tuple(280 + math.cos(2 * math.pi * j / n) for j in range(n))
        solution = heat.simulate(
            initial, diffusivity_m2_s=1, dx_m=1 / n, dt_s=0.25 / n**2, steps=n * n // 16
        )
        assert solution.time_s == 1 / 64
        continuum_amplitude = math.exp(-4 * math.pi**2 / 64)
        error = max(
            abs(value - (280 + continuum_amplitude * math.cos(2 * math.pi * j / n)))
            for j, value in enumerate(solution.temperature_K)
        )
        errors.append(error)
    assert all(3.8 < coarse / fine < 4.2 for coarse, fine in zip(errors, errors[1:]))
    assert errors[-1] < 0.002
