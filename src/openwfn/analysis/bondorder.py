"""Mayer AO bond orders including the unrestricted spin-density term."""
import numpy as np


def mayer_matrix(total: np.ndarray, spin: np.ndarray, overlap: np.ndarray,
                 ao_atoms: tuple[int, ...], atom_count: int) -> np.ndarray:
    p, q, s = (np.asarray(value, dtype=float) for value in (total, spin, overlap))
    size = len(ao_atoms)
    if size == 0 or any(value.shape != (size, size) for value in (p, q, s)):
        raise ValueError('density/overlap must match the nonempty AO mapping')
    if any(not np.all(np.isfinite(value)) for value in (p, q, s)):
        raise ValueError('density/overlap must be finite')
    if any(not np.allclose(value, value.T, atol=1e-10, rtol=1e-10) for value in (p, q, s)):
        raise ValueError('density/overlap must be symmetric')
    if any(index < 0 or index >= atom_count for index in ao_atoms):
        raise ValueError('AO atom mapping contains invalid centers')
    ps, qs = p @ s, q @ s
    products = ps * ps.T + qs * qs.T
    matrix = np.zeros((atom_count, atom_count))
    mapping = np.asarray(ao_atoms)
    for atom in range(atom_count):
        row = products[mapping == atom].sum(axis=0)
        matrix[atom] = np.bincount(mapping, weights=row, minlength=atom_count)
    np.fill_diagonal(matrix, 0.)
    return matrix
