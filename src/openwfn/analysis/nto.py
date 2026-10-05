"""Natural-transition-orbital numerical kernels and registered analysis helpers."""

from __future__ import annotations

from dataclasses import dataclass
from math import isqrt

import numpy as np

from ..errors import DataUnavailableError
from ..excited_states import (
    AmplitudeBlock,
    ExcitedState,
    ExcitedStateCollection,
    ExcitedStateJob,
    get_excited_state_collection,
)
from ..model import CalculationData, MolecularOrbitals
from ..results import ResultRecord
from .basis import overlap_matrix
from .limits import MAX_NTO_MATRIX_ELEMENTS
from .orbitals import OCCUPATION_THRESHOLD

MAX_NTO_RETURNED_PAIRS = isqrt(MAX_NTO_MATRIX_ELEMENTS)


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


@dataclass(frozen=True, slots=True)
class NTOMappedResult:
    """One NTO decomposition rotated into the source AO coefficient basis."""

    svd: NTOSVDResult
    hole_coefficients: np.ndarray
    electron_coefficients: np.ndarray
    hole_norms: np.ndarray
    electron_norms: np.ndarray
    hole_norm_residuals: np.ndarray
    electron_norm_residuals: np.ndarray
    occupied_mo_indices: tuple[int, ...]
    virtual_mo_indices: tuple[int, ...]
    spin_block: str


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


def _source_orbitals_for_block(
    data: CalculationData,
    block: AmplitudeBlock,
) -> tuple[MolecularOrbitals, str]:
    """Resolve the source orbital channel without guessing open-shell spin."""

    requested = block.spin_block.casefold() if block.spin_block is not None else None
    if requested == "alpha":
        if data.alpha_orbitals is None:
            raise DataUnavailableError("Alpha orbitals are unavailable for NTO mapping.")
        return data.alpha_orbitals, "alpha"
    if requested == "beta":
        if data.beta_orbitals is None:
            raise DataUnavailableError("Beta orbitals are unavailable for NTO mapping.")
        return data.beta_orbitals, "beta"
    if requested not in {None, "restricted"}:
        raise DataUnavailableError(
            f"NTO spin block '{block.spin_block}' cannot be mapped to source orbitals."
        )

    orbitals = data.alpha_orbitals
    if orbitals is None:
        raise DataUnavailableError("Molecular orbitals are unavailable for NTO mapping.")
    if orbitals.spin != "restricted":
        raise DataUnavailableError(
            "Unrestricted NTO mapping requires an explicit alpha or beta spin block."
        )
    return orbitals, "restricted"


def _orbital_domains(orbitals: MolecularOrbitals) -> tuple[tuple[int, ...], tuple[int, ...]]:
    occupied = tuple(
        index
        for index, occupation in enumerate(orbitals.occupations)
        if occupation > OCCUPATION_THRESHOLD
    )
    virtual = tuple(
        index
        for index, occupation in enumerate(orbitals.occupations)
        if occupation <= OCCUPATION_THRESHOLD
    )
    if not occupied or not virtual:
        raise DataUnavailableError(
            "NTO mapping requires both occupied and virtual source orbitals."
        )
    return occupied, virtual


def _metric_norms(coefficients: np.ndarray, overlap: np.ndarray) -> np.ndarray:
    norms = np.einsum("ai,ab,bi->i", coefficients, overlap, coefficients, optimize=True)
    if not np.all(np.isfinite(norms)):
        raise ValueError("NTO AO overlap norms must be finite")
    return norms


def map_nto_to_ao(data: CalculationData, block: AmplitudeBlock) -> NTOMappedResult:
    """Rotate one complete occupied-by-virtual transition matrix into AO coefficients.

    Source MO coefficients are used exactly as stored. AO-overlap norms and their
    residuals from unity are reported diagnostically; coefficients are never
    silently renormalized.
    """

    if data.basis is None:
        raise DataUnavailableError("A molecular basis is required for NTO AO mapping.")

    orbitals, spin_block = _source_orbitals_for_block(data, block)
    occupied, virtual = _orbital_domains(orbitals)
    expected_dimensions = (len(occupied), len(virtual))
    if block.dimensions != expected_dimensions:
        raise DataUnavailableError(
            "NTO transition matrix dimensions do not match the source occupied and virtual "
            f"orbital sets: got {block.dimensions}, expected {expected_dimensions}."
        )

    matrix = transition_matrix_from_block(block)
    svd = compute_nto_svd(matrix)
    source_coefficients = np.asarray(orbitals.coefficients, dtype=float)
    if source_coefficients.ndim != 2:
        raise ValueError("Source MO coefficient matrix must be two-dimensional")
    if source_coefficients.shape[1] != len(orbitals.energies):
        raise ValueError("Source MO coefficient columns must match the orbital count")
    if source_coefficients.shape[0] != data.basis.n_functions:
        raise DataUnavailableError(
            "Source MO coefficient rows do not match the available AO basis functions."
        )
    if not np.all(np.isfinite(source_coefficients)):
        raise ValueError("Source MO coefficients must be finite for NTO mapping")

    hole_coefficients = source_coefficients[:, occupied] @ svd.hole_vectors
    electron_coefficients = source_coefficients[:, virtual] @ svd.electron_vectors
    overlap = overlap_matrix(data.basis, data.molecule)
    hole_norms = _metric_norms(hole_coefficients, overlap)
    electron_norms = _metric_norms(electron_coefficients, overlap)

    return NTOMappedResult(
        svd=svd,
        hole_coefficients=hole_coefficients,
        electron_coefficients=electron_coefficients,
        hole_norms=hole_norms,
        electron_norms=electron_norms,
        hole_norm_residuals=np.abs(hole_norms - 1.0),
        electron_norm_residuals=np.abs(electron_norms - 1.0),
        occupied_mo_indices=tuple(index + 1 for index in occupied),
        virtual_mo_indices=tuple(index + 1 for index in virtual),
        spin_block=spin_block,
    )


def _one_based_index(label: str, value: int, size: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= size:
        raise ValueError(
            f"{label} must be a valid one-based index between 1 and {size}; got {value!r}."
        )
    return value - 1


def _select_job(
    collection: ExcitedStateCollection,
    job: int | None,
) -> ExcitedStateJob:
    if job is None:
        if len(collection.jobs) != 1:
            raise ValueError(
                "job must be supplied as a one-based index when multiple excited-state jobs exist."
            )
        return collection.jobs[0]
    return collection.jobs[_one_based_index("job", job, len(collection.jobs))]


def _validate_analysis_parameters(max_pairs: int, min_weight: float) -> float:
    if (
        isinstance(max_pairs, bool)
        or not isinstance(max_pairs, int)
        or not 1 <= max_pairs <= MAX_NTO_RETURNED_PAIRS
    ):
        raise ValueError(
            f"max_pairs must be an integer from 1 to {MAX_NTO_RETURNED_PAIRS}."
        )
    if isinstance(min_weight, bool):
        raise ValueError("min_weight must be a finite number from 0 to 1.")
    try:
        normalized_weight = float(min_weight)
    except (TypeError, ValueError) as exc:
        raise ValueError("min_weight must be a finite number from 0 to 1.") from exc
    if not np.isfinite(normalized_weight) or not 0.0 <= normalized_weight <= 1.0:
        raise ValueError("min_weight must be a finite number from 0 to 1.")
    return normalized_weight


def nto(
    data: CalculationData,
    *,
    state: int,
    job: int | None = None,
    spin: str | None = None,
    max_pairs: int = 20,
    min_weight: float = 0.0,
) -> ResultRecord:
    """Return conservative NTO pairs for one explicitly selected excited state."""

    normalized_weight = _validate_analysis_parameters(max_pairs, min_weight)
    collection = get_excited_state_collection(data)
    selected_job = _select_job(collection, job)
    state_offset = _one_based_index("state", state, len(selected_job.states))
    selected_state = selected_job.states[state_offset]
    block = select_nto_amplitude_block(selected_state, spin=spin)
    mapped = map_nto_to_ao(data, block)

    kept_by_weight = [
        pair
        for pair, weight in enumerate(mapped.svd.weights)
        if float(weight) >= normalized_weight
    ]
    returned_pairs = kept_by_weight[:max_pairs]
    omitted_by_weight = len(mapped.svd.weights) - len(kept_by_weight)
    omitted_by_limit = len(kept_by_weight) - len(returned_pairs)

    pairs = [
        {
            "pair": pair + 1,
            "singular_value": float(mapped.svd.singular_values[pair]),
            "pair_strength": float(mapped.svd.pair_strengths[pair]),
            "weight": float(mapped.svd.weights[pair]),
            "cumulative_weight": float(mapped.svd.cumulative_weights[pair]),
            "hole_norm": float(mapped.hole_norms[pair]),
            "electron_norm": float(mapped.electron_norms[pair]),
            "hole_norm_residual": float(mapped.hole_norm_residuals[pair]),
            "electron_norm_residual": float(mapped.electron_norm_residuals[pair]),
        }
        for pair in returned_pairs
    ]

    omitted = omitted_by_weight + omitted_by_limit
    warnings = (
        (
            f"{omitted} NTO pair(s) omitted by the requested min_weight/max_pairs filters."
        ),
    ) if omitted else ()
    return ResultRecord(
        kind="natural_transition_orbitals",
        data={
            "job": selected_job.index,
            "state": selected_state.index,
            "source_state": selected_state.source_state,
            "source_program": selected_job.source_program,
            "method_family": selected_job.method_family,
            "method_detail": selected_job.method_detail,
            "reference_state": selected_job.reference_state,
            "spin_block": mapped.spin_block,
            "amplitude_convention": block.convention,
            "matrix_dimensions": list(block.dimensions),
            "transition_norm": mapped.svd.transition_norm,
            "occupied_mo_indices": list(mapped.occupied_mo_indices),
            "virtual_mo_indices": list(mapped.virtual_mo_indices),
            "pair_count_total": len(mapped.svd.weights),
            "pair_count_returned": len(pairs),
            "max_pairs": max_pairs,
            "min_weight": normalized_weight,
            "omitted_by_weight": omitted_by_weight,
            "omitted_by_limit": omitted_by_limit,
            "omitted_pair_count": omitted,
            "phase_convention": "paired_sign_first_largest_hole_component_positive",
            "coefficient_mapping": "source_mo_occupied_virtual_to_ao",
            "weight_normalization": "squared_singular_value_over_transition_frobenius_norm_squared",
            "pairs": pairs,
        },
        units={
            "transition_norm": "dimensionless",
            "singular_value": "dimensionless",
            "pair_strength": "dimensionless",
            "weight": "dimensionless",
            "cumulative_weight": "dimensionless",
            "ao_overlap_norm": "dimensionless",
        },
        validation_status="Experimental",
        warnings=warnings,
    )


__all__ = [
    "MAX_NTO_MATRIX_ELEMENTS",
    "MAX_NTO_RETURNED_PAIRS",
    "NTOMappedResult",
    "NTOSVDResult",
    "compute_nto_svd",
    "map_nto_to_ao",
    "nto",
    "select_nto_amplitude_block",
    "transition_matrix_from_block",
]
