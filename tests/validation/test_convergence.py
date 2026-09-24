import math

import pytest

from openwfn.validation.convergence import GridPoint, assess_convergence


def test_convergence_passes_when_final_error_and_successive_change_are_small() -> None:
    points = [
        GridPoint(0.30, 6.0, 41.90, 42.0),
        GridPoint(0.20, 6.0, 41.99, 42.0),
        GridPoint(0.15, 6.0, 42.00, 42.0),
    ]

    result = assess_convergence(
        points,
        maximum_relative_error=0.001,
        maximum_successive_change=0.001,
    )

    assert result.status == "passed"
    assert result.relative_error == 0.0
    assert result.successive_change == pytest.approx(1 / 4200)


def test_convergence_requires_at_least_two_points() -> None:
    with pytest.raises(ValueError, match="at least two"):
        assess_convergence(
            [GridPoint(0.15, 6.0, 42.0, 42.0)],
            maximum_relative_error=0.001,
            maximum_successive_change=0.001,
        )


def test_convergence_fails_when_final_error_exceeds_limit() -> None:
    result = assess_convergence(
        [GridPoint(0.20, 6.0, 41.0, 42.0), GridPoint(0.15, 6.0, 41.5, 42.0)],
        maximum_relative_error=0.001,
        maximum_successive_change=0.1,
    )

    assert result.status == "failed"
    assert "relative error" in result.message


def test_convergence_fails_when_successive_change_exceeds_limit() -> None:
    result = assess_convergence(
        [GridPoint(0.20, 6.0, 41.0, 42.0), GridPoint(0.15, 6.0, 42.0, 42.0)],
        maximum_relative_error=0.001,
        maximum_successive_change=0.001,
    )

    assert result.status == "failed"
    assert "successive change" in result.message


def test_convergence_accepts_non_monotonic_history_when_final_pair_converges() -> None:
    result = assess_convergence(
        [
            GridPoint(0.40, 6.0, 42.4, 42.0),
            GridPoint(0.30, 6.0, 41.7, 42.0),
            GridPoint(0.20, 6.0, 42.01, 42.0),
            GridPoint(0.15, 6.0, 42.00, 42.0),
        ],
        maximum_relative_error=0.001,
        maximum_successive_change=0.001,
    )

    assert result.status == "passed"


@pytest.mark.parametrize(
    "points, message",
    [
        (
            [GridPoint(0.20, 6.0, math.nan, 42.0), GridPoint(0.15, 6.0, 42.0, 42.0)],
            "finite",
        ),
        (
            [GridPoint(0.15, 6.0, 42.0, 42.0), GridPoint(0.15, 6.0, 42.0, 42.0)],
            "unique",
        ),
        (
            [GridPoint(0.20, 5.0, 42.0, 42.0), GridPoint(0.15, 6.0, 42.0, 42.0)],
            "padding",
        ),
        (
            [GridPoint(0.20, 6.0, 42.0, 42.0), GridPoint(0.15, 6.0, 42.0, 41.0)],
            "expected-electron",
        ),
    ],
)
def test_convergence_rejects_invalid_point_sequences(
    points: list[GridPoint], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        assess_convergence(
            points,
            maximum_relative_error=0.001,
            maximum_successive_change=0.001,
        )
