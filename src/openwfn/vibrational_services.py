"""Numerical helpers shared by vibrational spectroscopy analyses and renderers."""

from math import ceil, isfinite, log
from typing import Sequence

import numpy as np

DEFAULT_FWHM_CM1 = 20.0
MAX_SPECTRUM_POINTS = 100_000


def _finite_values(label: str, values: Sequence[float]) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0:
        raise ValueError(f"{label} must be a non-empty one-dimensional sequence")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label} must contain only finite values")
    return array


def broaden_lines(
    frequencies_cm1: Sequence[float],
    strengths: Sequence[float],
    *,
    fwhm_cm1: float = DEFAULT_FWHM_CM1,
    frequency_min_cm1: float | None = None,
    frequency_max_cm1: float | None = None,
    points: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return a peak-height-preserving Gaussian broadening of discrete lines.

    Each source strength is the broadened curve value at its own line center when
    isolated. The Gaussian is defined so the value reaches half height at
    ``frequency +/- FWHM/2``. This is a visualization/post-processing curve; it
    does not replace the original source stick values.
    """

    frequencies = _finite_values("frequencies", frequencies_cm1)
    amplitudes = _finite_values("strengths", strengths)
    if frequencies.shape != amplitudes.shape:
        raise ValueError("frequencies and strengths must contain the same number of values")
    if not isfinite(fwhm_cm1) or fwhm_cm1 <= 0.0:
        raise ValueError("FWHM must be a positive finite value")

    margin = max(100.0, 5.0 * float(fwhm_cm1))
    lower = (
        float(frequency_min_cm1)
        if frequency_min_cm1 is not None
        else max(0.0, float(frequencies.min()) - margin)
    )
    upper = (
        float(frequency_max_cm1)
        if frequency_max_cm1 is not None
        else float(frequencies.max()) + margin
    )
    if not isfinite(lower) or not isfinite(upper) or lower >= upper:
        raise ValueError("frequency range must contain finite min < max values")

    if points is None:
        points = int(ceil(upper - lower)) + 1
    if isinstance(points, bool) or not isinstance(points, int):
        raise ValueError("points must be an integer")
    if points < 2 or points > MAX_SPECTRUM_POINTS:
        raise ValueError(
            f"points must be between 2 and {MAX_SPECTRUM_POINTS} to bound memory use"
        )

    grid = np.linspace(lower, upper, points, dtype=float)
    curve = np.zeros(points, dtype=float)
    coefficient = -4.0 * log(2.0) / (float(fwhm_cm1) ** 2)
    for frequency, amplitude in zip(frequencies, amplitudes, strict=True):
        curve += amplitude * np.exp(coefficient * (grid - frequency) ** 2)
    return grid, curve
