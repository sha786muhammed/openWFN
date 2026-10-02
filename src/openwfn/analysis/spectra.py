"""Bounded, normalized Gaussian broadening in a linear energy variable."""
from math import isfinite

import numpy as np

MAX_SPECTRUM_POINTS = 100_000
MAX_SPECTRUM_VALUES = 2_000_000


def gaussian_spectrum(lines: np.ndarray, x: np.ndarray, sigma: float,
                      weights: np.ndarray | None = None) -> np.ndarray:
    """Sum unit-area Gaussian lines, optionally with one row of weights per series."""
    energies, axis = np.asarray(lines, dtype=float), np.asarray(x, dtype=float)
    if not isfinite(sigma) or sigma <= 0:
        raise ValueError('Gaussian sigma must be positive and finite')
    if energies.ndim != 1 or not len(energies) or axis.ndim != 1 or len(axis) < 2:
        raise ValueError('line/energy arrays must be nonempty one-dimensional arrays')
    if len(axis) > MAX_SPECTRUM_POINTS:
        raise ValueError('energy grid exceeds 100000-point safety limit')
    if not np.all(np.isfinite(energies)) or not np.all(np.isfinite(axis)) or np.any(np.diff(axis) <= 0):
        raise ValueError('spectrum arrays must be finite and grid strictly increasing')
    w = np.ones((1, len(energies))) if weights is None else np.asarray(weights, dtype=float)
    if w.ndim != 2 or w.shape[1] != len(energies) or not np.all(np.isfinite(w)):
        raise ValueError('projection weights must have one finite column per line')
    if w.shape[0] * len(axis) > MAX_SPECTRUM_VALUES:
        raise ValueError('projected spectrum exceeds the two-million-value safety limit')
    result = np.zeros((w.shape[0], len(axis)))
    chunk = max(1, 1_000_000 // len(axis))
    for start in range(0, len(energies), chunk):
        stop = min(start+chunk, len(energies))
        with np.errstate(over='ignore', under='ignore'):
            z = (axis[:, None]-energies[None, start:stop])/sigma
            kernel = np.exp(-.5*z*z)/(sigma*np.sqrt(2*np.pi))
        result += w[:, start:stop] @ kernel.T
    return result[0] if weights is None else result


def trapezoid_area(values: np.ndarray, x: np.ndarray) -> float:
    return float(np.sum((values[1:]+values[:-1])*.5*np.diff(x)))
