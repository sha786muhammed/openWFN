"""Numerical helpers shared by vibrational spectroscopy analyses and renderers."""

from typing import Sequence

import numpy as np

from .spectrum_math import gaussian_broaden

DEFAULT_FWHM_CM1 = 20.0


def broaden_lines(
    frequencies_cm1: Sequence[float],
    strengths: Sequence[float],
    *,
    fwhm_cm1: float = DEFAULT_FWHM_CM1,
    frequency_min_cm1: float | None = None,
    frequency_max_cm1: float | None = None,
    points: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return the established peak-height-preserving vibrational Gaussian curve."""

    margin = max(100.0, 5.0 * float(fwhm_cm1))
    return gaussian_broaden(
        frequencies_cm1,
        strengths,
        fwhm=fwhm_cm1,
        lower=frequency_min_cm1,
        upper=frequency_max_cm1,
        points=points,
        margin=margin,
        lower_floor=0.0,
        default_step=1.0,
    )
