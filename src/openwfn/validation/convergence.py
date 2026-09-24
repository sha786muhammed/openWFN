"""Grid-refinement checks for numerical density integration."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class GridPoint:
    spacing: float
    padding: float
    electron_count: float
    expected_electrons: float


@dataclass(frozen=True, slots=True)
class ConvergenceResult:
    status: Literal["passed", "failed"]
    relative_error: float
    successive_change: float
    message: str


def assess_convergence(
    points: Sequence[GridPoint],
    *,
    maximum_relative_error: float,
    maximum_successive_change: float,
) -> ConvergenceResult:
    """Assess the finest result and the change from the next-finest grid."""

    if len(points) < 2:
        raise ValueError("grid convergence requires at least two points")
    thresholds = (maximum_relative_error, maximum_successive_change)
    if any(not math.isfinite(value) or value < 0.0 for value in thresholds):
        raise ValueError("convergence thresholds must be finite and non-negative")
    for point in points:
        values = (
            point.spacing,
            point.padding,
            point.electron_count,
            point.expected_electrons,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("grid convergence values must be finite")
        if point.spacing <= 0.0 or point.padding <= 0.0:
            raise ValueError("grid spacing and padding must be positive")
        if point.expected_electrons <= 0.0:
            raise ValueError("expected-electron count must be positive")

    if len({point.spacing for point in points}) != len(points):
        raise ValueError("grid spacings must be unique")
    if len({point.padding for point in points}) != 1:
        raise ValueError("all grid points must use identical padding")
    expected = points[0].expected_electrons
    if any(
        not math.isclose(point.expected_electrons, expected, rel_tol=0.0, abs_tol=1e-12)
        for point in points[1:]
    ):
        raise ValueError("expected-electron count must be consistent")

    ordered = sorted(points, key=lambda point: point.spacing, reverse=True)
    previous, final = ordered[-2:]
    relative_error = abs(final.electron_count - expected) / expected
    successive_change = abs(final.electron_count - previous.electron_count) / expected
    failures: list[str] = []
    if relative_error > maximum_relative_error:
        failures.append("final relative error exceeds the configured limit")
    if successive_change > maximum_successive_change:
        failures.append("final successive change exceeds the configured limit")
    if failures:
        return ConvergenceResult("failed", relative_error, successive_change, "; ".join(failures))
    return ConvergenceResult(
        "passed",
        relative_error,
        successive_change,
        "final error and successive change satisfy the configured limits",
    )
