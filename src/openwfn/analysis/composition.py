"""Named Mulliken and symmetric Löwdin MO projection conventions."""
import numpy as np


def orbital_weights(coefficients: np.ndarray, overlap: np.ndarray, method: str):
    """Return AO fractions, raw c^TSc norms and overlap diagnostics per MO."""
    if method not in {'lowdin', 'mulliken'}:
        raise ValueError("composition method must be 'lowdin' or 'mulliken'")
    c, s = np.asarray(coefficients, dtype=float), np.asarray(overlap, dtype=float)
    if c.ndim != 2 or s.shape != (c.shape[0], c.shape[0]):
        raise ValueError('coefficient rows and square overlap dimension must agree')
    if not np.all(np.isfinite(c)) or not np.all(np.isfinite(s)):
        raise ValueError('projection inputs must be finite')
    if not np.allclose(s, s.T, atol=1e-10, rtol=1e-10):
        raise ValueError('overlap must be symmetric')
    eigenvalues, eigenvectors = np.linalg.eigh(s)
    minimum, maximum = float(eigenvalues.min()), float(eigenvalues.max())
    if minimum < -1e-10:
        raise ValueError('overlap must be positive semidefinite')
    norms = np.sum(c * (s @ c), axis=0)
    if np.any(norms <= 1e-12) or not np.all(np.isfinite(norms)):
        raise ValueError('MO metric norm must be finite and positive')
    if method == 'mulliken':
        weights = c * (s @ c)
    else:
        square_root = (eigenvectors * np.sqrt(np.clip(eigenvalues, 0., None))) @ eigenvectors.T
        weights = np.square(square_root @ c)
    return weights / norms, norms, {
        'overlap_min_eigenvalue': minimum,
        'overlap_condition_number': maximum/minimum if minimum > 1e-12 else None,
        'overlap_rank_deficient': minimum <= 1e-12,
    }
