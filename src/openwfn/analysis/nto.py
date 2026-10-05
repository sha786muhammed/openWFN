"""Natural-transition-orbital numerical kernels and registered analysis helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..errors import DataUnavailableError
from ..excited_states import AmplitudeBlock, ExcitedState
from .limits import MAX_NTO_MATRIX_ELEMENTS


@dataclass(frozen=True, slots=True)
class NTOSVDResult:
    """Internal real-valued SVD representation of one transition matrix."""

    hole_vectors: np.ndarray
    electron_vectors: np.ndarray
    singular_values: np.ndarray
    pair_strengths: np.ndarray
    weights: np.ndarray
    cumulative_weights: np.ndarray
    transition_norm: float


def _paired_deterministic_phase(hole_vectors: np.ndarray, vt: np.ndarray) -> None:
    """Fix each SVD pair phase using the first largest-magnitude hole component."""

    for pair in range(hole_vectors.shape[1]):
        column = hole_vectors[:, pair]
        largest = float(np.max(np.abs(column)))
        pivot = int(np.flatnonzero(np.abs(column) == largest)[0])
        if column[pivot] < 0.0:
            hole_vectors[:, pair] *= -1.0
            vt[pair, :] *= -1.0


def compute_nto_svd(matrix: np.ndarray) -> NTOSVDResult:
    """Return a bounded deterministic real SVD for an NTO transition matrix.

    The input convention/orientation is deliberately outside this pure numerical
    kernel. ``transition_norm`` is the squared Frobenius norm, equal to the sum
    of all pair strengths and used as the weight-normalization denominator.
    """

    array = np.asarray(matrix, dtype=float)
    if array.ndim != 2:
        raise ValueError("NTO transition matrix must be two-dimensional")
    if array.shape[0] == 0 or array.shape[1] == 0:
        raise ValueError("NTO transition matrix must be non-empty")
    if array.size > MAX_NTO_MATRIX_ELEMENTS:
        raise ValueError(
            f"NTO transition matrix requests {array.size:,} elements, exceeding the "
            f"safety ceiling of {MAX_NTO_MATRIX_ELEMENTS:,}; SVD was not started."
        )
    if not np.all(np.isfinite(array)):
        raise ValueError("NTO transition matrix must contain only finite values")

    norm_squared = float(np.sum(np.square(array)))
    if not np.isfinite(norm_squared) or norm_squared <= 0.0:
        raise ValueError("NTO transition matrix is zero-norm and is non-informative")

    hole_vectors, singular_values, vt = np.linalg.svd(array, full_matrices=False)
    _paired_deterministic_phase(hole_vectors, vt)
    pair_strengths = np.square(singular_values)
    transition_norm = float(np.sum(pair_strengths))
    if not np.isfinite(transition_norm) or transition_norm <= 0.0:
        raise ValueError("NTO transition matrix is zero-norm and is non-informative")
    weights = pair_strengths / transition_norm
    cumulative_weights = np.cumsum(weights)
    cumulative_weights[-1] = 1.0

    return NTOSVDResult(
        hole_vectors=hole_vectors,
        electron_vectors=vt.T,
        singular_values=singular_values,
        pair_strengths=pair_strengths,
        weights=weights,
        cumulative_weights=cumulative_weights,
        transition_norm=transition_norm,
    )


def transition_matrix_from_block(block: AmplitudeBlock) -> np.ndarray:
    """Materialize one complete occupied-by-virtual block after ``nto_ready`` gating."""

    if not block.nto_ready:
        raise DataUnavailableError(
            "Amplitude block is not a complete explicitly oriented NTO transition matrix."
        )
    rows, columns = block.dimensions
    if rows * columns > MAX_NTO_MATRIX_ELEMENTS:
        raise ValueError(
            f"NTO transition matrix requests {rows * columns:,} elements, exceeding the "
            f"safety ceiling of {MAX_NTO_MATRIX_ELEMENTS:,}; matrix was not materialized."
        )
    if not block.indices:
        return np.asarray(block.values, dtype=float).reshape(rows, columns)

    matrix = np.empty((rows, columns), dtype=float)
    for index_tuple, value in zip(block.indices, block.values, strict=True):
        row, column = index_tuple
        matrix[row, column] = value
    return matrix


def select_nto_amplitude_block(
    state: ExcitedState,
    *,
    spin: str | None = None,
) -> AmplitudeBlock:
    """Select one eligible source block without guessing across spin channels."""

    eligible = tuple(block for block in state.amplitudes if block.nto_ready)
    if spin is not None:
        requested = spin.strip().casefold()
        if not requested:
            raise ValueError("spin selector must not be blank")
        eligible = tuple(
            block
            for block in eligible
            if block.spin_block is not None and block.spin_block.casefold() == requested
        )
        if not eligible:
            raise DataUnavailableError(
                f"No complete NTO transition matrix is available for spin block '{spin}'."
            )
    if not eligible:
        raise DataUnavailableError(
            "Excited state does not contain a complete explicitly supported transition matrix."
        )
    if len(eligible) != 1:
        raise DataUnavailableError(
            "NTO transition matrix selection is ambiguous across multiple eligible blocks; "
            "provide an explicit spin selector."
        )
    return eligible[0]


__all__ = [
    "MAX_NTO_MATRIX_ELEMENTS",
    "NTOSVDResult",
    "compute_nto_svd",
    "select_nto_amplitude_block",
    "transition_matrix_from_block",
]
