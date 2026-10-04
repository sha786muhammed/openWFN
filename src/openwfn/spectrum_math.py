"""Shared, unit-agnostic numerical helpers for broadened line spectra."""

from math import ceil, isfinite, log
from typing import Sequence

import numpy as np

MAX_SPECTRUM_POINTS = 100_000


def _finite_1d(label: str, values: Sequence[float]) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0:
        raise ValueError(f"{label} must be a non-empty one-dimensional sequence")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label} must contain only finite values")
    return array


def gaussian_broaden(
    positions: Sequence[float],
    strengths: Sequence[float],
    *,
    fwhm: float,
    lower: float | None = None,
    upper: float | None = None,
    points: int | None = None,
    margin: float,
    lower_floor: float | None = None,
    default_step: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return a peak-height-preserving Gaussian broadening of discrete lines.

    The Gaussian is defined so an isolated source line reaches half of its
    source-reported height at ``position +/- FWHM/2``. Units are supplied by
    callers; all position/range/FWHM values must use the same unit.
    """

    x = _finite_1d("positions", positions)
    amplitudes = _finite_1d("strengths", strengths)
    if x.shape != amplitudes.shape:
        raise ValueError("positions and strengths must contain the same number of values")
    if not isfinite(fwhm) or fwhm <= 0.0:
        raise ValueError("FWHM must be a positive finite value")
    if not isfinite(margin) or margin < 0.0:
        raise ValueError("spectrum margin must be a non-negative finite value")
    if not isfinite(default_step) or default_step <= 0.0:
        raise ValueError("default spectrum step must be a positive finite value")

    actual_lower = float(lower) if lower is not None else float(x.min()) - float(margin)
    actual_upper = float(upper) if upper is not None else float(x.max()) + float(margin)
    if lower_floor is not None:
        if not isfinite(lower_floor):
            raise ValueError("lower floor must be finite")
        actual_lower = max(float(lower_floor), actual_lower)
    if not isfinite(actual_lower) or not isfinite(actual_upper) or actual_lower >= actual_upper:
        raise ValueError("spectrum range must contain finite min < max values")

    if points is None:
        points = int(ceil((actual_upper - actual_lower) / default_step)) + 1
    if isinstance(points, bool) or not isinstance(points, int):
        raise ValueError("points must be an integer")
    if points < 2 or points > MAX_SPECTRUM_POINTS:
        raise ValueError(
            f"points must be between 2 and {MAX_SPECTRUM_POINTS} to bound memory use"
        )

    grid = np.linspace(actual_lower, actual_upper, points, dtype=float)
    curve = np.zeros(points, dtype=float)
    coefficient = -4.0 * log(2.0) / (float(fwhm) ** 2)
    for position, amplitude in zip(x, amplitudes, strict=True):
        curve += amplitude * np.exp(coefficient * (grid - position) ** 2)
    return grid, curve
