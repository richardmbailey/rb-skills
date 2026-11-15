"""Requirements-first oracles designed without reading candidate implementation."""

import math

import pytest

from model import simulate


def test_exact_transfer_and_short_final_step() -> None:
    samples = simulate(16.0, 3.0, 0.5, 1.25, 0.5)
    assert [(s.time_days, s.a_kg, s.b_kg) for s in samples] == [
        (0.0, 16.0, 3.0),
        (0.5, 12.0, 7.0),
        (1.0, 9.0, 10.0),
        (1.25, 7.875, 11.125),
    ]
    assert samples[-1].total_tonnes == 19.0 / 1000.0


def test_endpoint_against_continuous_solution_and_derived_bound() -> None:
    final = simulate(1000.0, 0.0, 0.2, 10.0, 0.1)[-1]
    exact_a = 1000.0 * math.exp(-2.0)
    bound = exact_a * 100 * 0.02**2 / (2 * (1 - 0.02))
    assert bound < 2.77
    assert final.time_days == 10.0
    assert -1e-9 <= exact_a - final.a_kg <= bound + 1e-9
    assert abs(final.b_kg - (1000.0 - exact_a)) <= bound + 1e-9


def test_first_order_convergence_in_declared_regime() -> None:
    exact_a = 1000.0 * math.exp(-2.0)
    errors = [
        abs(simulate(1000.0, 0.0, 0.2, 10.0, dt)[-1].a_kg - exact_a)
        for dt in (0.2, 0.1, 0.05)
    ]
    assert all(error > 0 for error in errors)
    assert all(
        1.9 <= coarse / fine <= 2.1
        for coarse, fine in zip(errors, errors[1:], strict=False)
    )


@pytest.mark.parametrize(
    ("a0", "b0", "rate", "duration", "dt"),
    [
        (32.0, 7.0, 0.5, 3.125, 0.25),
        (0.0, 8.0, 1.0, 2.0, 0.5),
        (13.0, 2.0, 0.0, 1.125, 0.5),
        (1e-8, 2e-8, 0.25, 4.0, 0.5),
    ],
)
def test_trajectory_physical_invariants(
    a0: float, b0: float, rate: float, duration: float, dt: float
) -> None:
    samples = simulate(a0, b0, rate, duration, dt)
    allowance = 1e-12 * max(1.0, a0 + b0)
    assert samples[0].time_days == 0.0
    assert samples[-1].time_days == duration
    for sample in samples:
        assert sample.a_kg >= 0.0
        assert sample.b_kg >= 0.0
        assert abs(sample.a_kg + sample.b_kg - a0 - b0) <= allowance
    for before, after in zip(samples, samples[1:], strict=False):
        assert before.time_days < after.time_days
        assert after.a_kg <= before.a_kg
        assert after.b_kg >= before.b_kg
    if rate == 0 or a0 == 0:
        assert all(sample.a_kg == a0 and sample.b_kg == b0 for sample in samples)


def test_positivity_boundary_empties_donor_once() -> None:
    samples = simulate(8.0, 3.0, 2.0, 1.25, 0.5)
    assert [(s.time_days, s.a_kg, s.b_kg) for s in samples] == [
        (0.0, 8.0, 3.0),
        (0.5, 0.0, 11.0),
        (1.0, 0.0, 11.0),
        (1.25, 0.0, 11.0),
    ]


def test_zero_duration_is_initial_state_only() -> None:
    samples = simulate(8.0, 3.0, 0.5, 0.0, 0.5)
    assert [(s.time_days, s.a_kg, s.b_kg) for s in samples] == [(0.0, 8.0, 3.0)]


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("index", range(5))
def test_nonfinite_inputs_rejected(index: int, value: float) -> None:
    args = [8.0, 3.0, 0.5, 1.0, 0.5]
    args[index] = value
    with pytest.raises(ValueError):
        simulate(*args)


@pytest.mark.parametrize(
    "args",
    [
        (-1.0, 0.0, 0.5, 1.0, 0.5),
        (1.0, -1.0, 0.5, 1.0, 0.5),
        (1.0, 0.0, -0.5, 1.0, 0.5),
        (1.0, 0.0, 0.5, -1.0, 0.5),
        (1.0, 0.0, 0.5, 1.0, 0.0),
        (1.0, 0.0, 0.5, 1.0, -0.5),
        (1.0, 0.0, 2.0, 1.0, math.nextafter(0.5, math.inf)),
        (1e308, 1e308, 0.0, 0.0, 1.0),
        (1.0, 0.0, 0.0, 100001.0, 1.0),
        (1.0, 0.0, 0.0, 1e308, 1e-308),
    ],
)
def test_invalid_boundary_inputs_rejected(args: tuple[float, ...]) -> None:
    with pytest.raises(ValueError):
        simulate(*args)


# The following regressions were added after implementation inspection.
def test_rounding_near_stability_boundary_preserves_nonnegative_donor() -> None:
    samples = simulate(1.0, 0.0, math.nextafter(10.0, 0.0), 0.5, 0.1)
    assert all(sample.a_kg >= 0.0 for sample in samples)
    assert all(sample.b_kg >= 0.0 for sample in samples)


def test_underflowed_step_quotient_still_includes_positive_final_time() -> None:
    samples = simulate(1.0, 0.0, 0.0, 1e-308, 1e308)
    assert [sample.time_days for sample in samples] == [0.0, 1e-308]
    assert all(sample.a_kg == 1.0 and sample.b_kg == 0.0 for sample in samples)
