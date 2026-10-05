"""Bounded QTAIM atomic-basin classification and integration primitives.

Basin identity is determined by density-gradient ascent.  The module keeps
trajectory classification, attractor preparation, population integration, and
boundary diagnostics as separate numerical layers so failures remain explicit.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from math import isfinite

import numpy as np

from ..constants import BOHR_TO_ANGSTROM
from ..errors import DataUnavailableError, ValidationError
from ..model import CalculationData
from ..scientific import effective_nuclear_charge, is_ghost_atom
from . import limits
from .atom_quadrature import AtomQuadratureSettings
from .qtaim import CriticalPoint, QTAIMSettings, SearchDiagnostics, search_critical_points
from .realspace import evaluate_density_fields

FieldEvaluator = Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]

_BOUNDED_ATTRACTOR_WARNING = (
    "QTAIM basin attractor discovery is bounded and not exhaustive; absence of "
    "an undiscovered non-nuclear attractor is not proven."
)
_ALL_ELECTRON_CHARGE_TOLERANCE = 1.0e-10
_ATTRACTOR_PERTURBATION_BOHR = 0.05


@dataclass(frozen=True, slots=True)
class QTAIMBasinSettings:
    """Numerical controls for Experimental QTAIM basin analysis."""

    quadrature: AtomQuadratureSettings = field(
        default_factory=lambda: AtomQuadratureSettings(
            radial_points=48,
            theta_points=12,
            phi_points=24,
            radial_extent_bohr=18.0,
            chunk_size=4096,
        )
    )
    flow_step_bohr: float = 0.05
    attractor_capture_radius_bohr: float = 0.25
    gradient_floor: float = 1.0e-10
    max_flow_steps: int = 2400
    max_backtracks: int = 8
    bounds_padding_bohr: float = 6.0
    attractor_match_tolerance_bohr: float = 0.35
    density_ascent_abs_tolerance: float = 1.0e-14
    density_ascent_rel_tolerance: float = 1.0e-12
    max_unresolved_electrons: float = 1.0e-3
    max_electron_count_residual: float = 1.0e-2
    max_charge_closure_residual: float = 1.0e-2
    boundary_spacing_bohr: float = 0.30
    boundary_padding_bohr: float = 3.0
    boundary_bisection_tolerance_bohr: float = 1.0e-3
    max_boundary_bisections: int = 24
    boundary_local_radius_bohr: float = 0.60
    boundary_min_neighbors: int = 6
    boundary_plane_condition_ratio: float = 1.0e-3
    max_zero_flux_p95: float = 0.15

    def __post_init__(self) -> None:
        if not isinstance(self.quadrature, AtomQuadratureSettings):
            raise ValueError("quadrature must be an AtomQuadratureSettings value")

        positive_float_fields = (
            "flow_step_bohr",
            "attractor_capture_radius_bohr",
            "gradient_floor",
            "bounds_padding_bohr",
            "attractor_match_tolerance_bohr",
            "max_unresolved_electrons",
            "max_electron_count_residual",
            "max_charge_closure_residual",
            "boundary_spacing_bohr",
            "boundary_padding_bohr",
            "boundary_bisection_tolerance_bohr",
            "boundary_local_radius_bohr",
            "boundary_plane_condition_ratio",
            "max_zero_flux_p95",
        )
        for name in positive_float_fields:
            value = getattr(self, name)
            if not isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be positive and finite")

        nonnegative_float_fields = (
            "density_ascent_abs_tolerance",
            "density_ascent_rel_tolerance",
        )
        for name in nonnegative_float_fields:
            value = getattr(self, name)
            if not isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be non-negative and finite")

        positive_integer_fields = (
            "max_flow_steps",
            "max_backtracks",
            "max_boundary_bisections",
            "boundary_min_neighbors",
        )
        for name in positive_integer_fields:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class BasinTrajectoryBatch:
    """Deterministic basin-flow outcomes for one point batch."""

    basin_indices: np.ndarray
    attractor_indices: np.ndarray
    status: np.ndarray
    steps: np.ndarray
    final_points_bohr: np.ndarray
    final_distances_bohr: np.ndarray
    path_lengths_bohr: np.ndarray


@dataclass(frozen=True, slots=True)
class PreparedBasinAttractors:
    """Validated nuclear attractors ordered one-to-one with physical nuclei."""

    physical_nucleus_indices: tuple[int, ...]
    nucleus_positions_bohr: np.ndarray
    nuclear_charges: np.ndarray
    attractor_positions_bohr: np.ndarray
    attractor_to_nucleus_distances_bohr: np.ndarray
    bounds: tuple[np.ndarray, np.ndarray]
    critical_points: tuple[CriticalPoint, ...]
    search_diagnostics: SearchDiagnostics
    search_complete: bool
    warnings: tuple[str, ...]


def _validate_points(
    points_bohr: np.ndarray,
    name: str,
    *,
    allow_empty: bool = True,
) -> np.ndarray:
    points = np.asarray(points_bohr, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"{name} must have shape (n, 3)")
    if not allow_empty and len(points) == 0:
        raise ValueError(f"{name} must contain at least one point")
    if not np.all(np.isfinite(points)):
        raise ValueError(f"{name} must contain only finite coordinates")
    return points


def _validate_bounds(
    bounds: tuple[np.ndarray, np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    lower = np.asarray(bounds[0], dtype=float)
    upper = np.asarray(bounds[1], dtype=float)
    if lower.shape != (3,) or upper.shape != (3,):
        raise ValueError("bounds must contain two Cartesian vectors with shape (3,)")
    if not np.all(np.isfinite(lower)) or not np.all(np.isfinite(upper)):
        raise ValueError("bounds must contain only finite values")
    if np.any(lower >= upper):
        raise ValueError("each lower bound must be smaller than the upper bound")
    return lower, upper


def _evaluate_field(
    evaluator: FieldEvaluator,
    points_bohr: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    rho, gradient = evaluator(points_bohr)
    density = np.asarray(rho, dtype=float)
    density_gradient = np.asarray(gradient, dtype=float)
    if density.shape != (len(points_bohr),):
        raise ValueError("field evaluator density must have shape (n_points,)")
    if density_gradient.shape != (len(points_bohr), 3):
        raise ValueError("field evaluator gradient must have shape (n_points, 3)")
    return density, density_gradient


def _capture_state(
    points_bohr: np.ndarray,
    attractors_bohr: np.ndarray,
    capture_radius_bohr: float,
) -> tuple[np.ndarray, np.ndarray]:
    distances = np.linalg.norm(
        points_bohr[:, None, :] - attractors_bohr[None, :, :],
        axis=2,
    )
    within = distances <= capture_radius_bohr
    counts = np.sum(within, axis=1)
    indices = np.full(len(points_bohr), -1, dtype=np.int64)
    unique = counts == 1
    if np.any(unique):
        indices[unique] = np.argmax(within[unique], axis=1)
    return counts, indices


def _classify_basin_chunk(
    evaluator: FieldEvaluator,
    points_bohr: np.ndarray,
    attractors_bohr: np.ndarray,
    *,
    lower: np.ndarray,
    upper: np.ndarray,
    settings: QTAIMBasinSettings,
) -> BasinTrajectoryBatch:
    point_count = len(points_bohr)
    current = points_bohr.copy()
    basin_indices = np.full(point_count, -1, dtype=np.int64)
    attractor_indices = np.full(point_count, -1, dtype=np.int64)
    status = np.full(point_count, "active", dtype=object)
    steps = np.zeros(point_count, dtype=np.int64)
    path_lengths = np.zeros(point_count, dtype=float)

    outside = np.any((current < lower) | (current > upper), axis=1)
    status[outside] = "out_of_bounds"

    initial_active = status == "active"
    if np.any(initial_active):
        active_ids = np.flatnonzero(initial_active)
        counts, captured = _capture_state(
            current[active_ids],
            attractors_bohr,
            settings.attractor_capture_radius_bohr,
        )
        ambiguous = counts > 1
        unique = counts == 1
        status[active_ids[ambiguous]] = "ambiguous_capture"
        if np.any(unique):
            target_ids = active_ids[unique]
            basin_indices[target_ids] = captured[unique]
            attractor_indices[target_ids] = captured[unique]
            status[target_ids] = "captured"

    for _ in range(settings.max_flow_steps):
        active_ids = np.flatnonzero(status == "active")
        if len(active_ids) == 0:
            break

        rho, gradient = _evaluate_field(evaluator, current[active_ids])
        finite = np.isfinite(rho) & np.all(np.isfinite(gradient), axis=1)
        status[active_ids[~finite]] = "nonfinite_field"
        active_ids = active_ids[finite]
        if len(active_ids) == 0:
            continue
        rho = rho[finite]
        gradient = gradient[finite]

        gradient_norm = np.linalg.norm(gradient, axis=1)
        low_gradient = (~np.isfinite(gradient_norm)) | (
            gradient_norm <= settings.gradient_floor
        )
        status[active_ids[low_gradient]] = "gradient_floor"
        moving_ids = active_ids[~low_gradient]
        if len(moving_ids) == 0:
            continue

        moving_rho = rho[~low_gradient]
        direction = gradient[~low_gradient] / gradient_norm[~low_gradient, None]
        pending = np.ones(len(moving_ids), dtype=bool)
        saw_inside = np.zeros(len(moving_ids), dtype=bool)
        saw_finite = np.zeros(len(moving_ids), dtype=bool)

        for backtrack in range(settings.max_backtracks + 1):
            pending_local = np.flatnonzero(pending)
            if len(pending_local) == 0:
                break

            step_length = settings.flow_step_bohr * (0.5**backtrack)
            candidate_points = (
                current[moving_ids[pending_local]]
                + step_length * direction[pending_local]
            )
            inside = np.all(
                (candidate_points >= lower) & (candidate_points <= upper),
                axis=1,
            )
            saw_inside[pending_local] |= inside
            if not np.any(inside):
                continue

            inside_local = pending_local[inside]
            inside_points = candidate_points[inside]
            candidate_rho, candidate_gradient = _evaluate_field(
                evaluator,
                inside_points,
            )
            finite_candidate = np.isfinite(candidate_rho) & np.all(
                np.isfinite(candidate_gradient), axis=1
            )
            saw_finite[inside_local] |= finite_candidate
            if not np.any(finite_candidate):
                continue

            finite_local = inside_local[finite_candidate]
            finite_points = inside_points[finite_candidate]
            finite_rho = candidate_rho[finite_candidate]
            ascent_slack = settings.density_ascent_abs_tolerance + (
                settings.density_ascent_rel_tolerance
                * np.abs(moving_rho[finite_local])
            )
            accepted = finite_rho >= moving_rho[finite_local] - ascent_slack
            if not np.any(accepted):
                continue

            accepted_local = finite_local[accepted]
            accepted_ids = moving_ids[accepted_local]
            accepted_points = finite_points[accepted]
            current[accepted_ids] = accepted_points
            steps[accepted_ids] += 1
            path_lengths[accepted_ids] += step_length
            pending[accepted_local] = False

            counts, captured = _capture_state(
                accepted_points,
                attractors_bohr,
                settings.attractor_capture_radius_bohr,
            )
            ambiguous = counts > 1
            unique = counts == 1
            status[accepted_ids[ambiguous]] = "ambiguous_capture"
            if np.any(unique):
                target_ids = accepted_ids[unique]
                basin_indices[target_ids] = captured[unique]
                attractor_indices[target_ids] = captured[unique]
                status[target_ids] = "captured"

        unresolved_local = np.flatnonzero(pending)
        if len(unresolved_local) > 0:
            unresolved_ids = moving_ids[unresolved_local]
            no_inside = ~saw_inside[unresolved_local]
            no_finite = saw_inside[unresolved_local] & ~saw_finite[unresolved_local]
            exhausted = ~(no_inside | no_finite)
            status[unresolved_ids[no_inside]] = "out_of_bounds"
            status[unresolved_ids[no_finite]] = "nonfinite_field"
            status[unresolved_ids[exhausted]] = "backtracking_exhausted"

    status[status == "active"] = "step_limit"
    final_distances = np.min(
        np.linalg.norm(
            current[:, None, :] - attractors_bohr[None, :, :],
            axis=2,
        ),
        axis=1,
    )
    return BasinTrajectoryBatch(
        basin_indices=basin_indices,
        attractor_indices=attractor_indices,
        status=status,
        steps=steps,
        final_points_bohr=current,
        final_distances_bohr=final_distances,
        path_lengths_bohr=path_lengths,
    )


def classify_basin_points(
    evaluator: FieldEvaluator,
    points_bohr: np.ndarray,
    attractors_bohr: np.ndarray,
    *,
    bounds: tuple[np.ndarray, np.ndarray],
    settings: QTAIMBasinSettings | None = None,
    chunk_size: int | None = None,
) -> BasinTrajectoryBatch:
    """Assign points to QTAIM attractors by bounded normalized-gradient ascent."""

    settings = settings or QTAIMBasinSettings()
    points = _validate_points(points_bohr, "points_bohr")
    attractors = _validate_points(
        attractors_bohr,
        "attractors_bohr",
        allow_empty=False,
    )
    lower, upper = _validate_bounds(bounds)
    limits.validate_point_analysis_request(len(points))

    if chunk_size is not None and (
        isinstance(chunk_size, bool)
        or not isinstance(chunk_size, int)
        or chunk_size <= 0
    ):
        raise ValueError("chunk_size must be a positive integer")

    if len(points) == 0:
        return BasinTrajectoryBatch(
            basin_indices=np.empty(0, dtype=np.int64),
            attractor_indices=np.empty(0, dtype=np.int64),
            status=np.empty(0, dtype=object),
            steps=np.empty(0, dtype=np.int64),
            final_points_bohr=np.empty((0, 3), dtype=float),
            final_distances_bohr=np.empty(0, dtype=float),
            path_lengths_bohr=np.empty(0, dtype=float),
        )

    effective_chunk_size = (
        len(points) if chunk_size is None else min(chunk_size, len(points))
    )
    batches = [
        _classify_basin_chunk(
            evaluator,
            points[start : start + effective_chunk_size],
            attractors,
            lower=lower,
            upper=upper,
            settings=settings,
        )
        for start in range(0, len(points), effective_chunk_size)
    ]
    return BasinTrajectoryBatch(
        basin_indices=np.concatenate([batch.basin_indices for batch in batches]),
        attractor_indices=np.concatenate(
            [batch.attractor_indices for batch in batches]
        ),
        status=np.concatenate([batch.status for batch in batches]),
        steps=np.concatenate([batch.steps for batch in batches]),
        final_points_bohr=np.concatenate(
            [batch.final_points_bohr for batch in batches], axis=0
        ),
        final_distances_bohr=np.concatenate(
            [batch.final_distances_bohr for batch in batches]
        ),
        path_lengths_bohr=np.concatenate(
            [batch.path_lengths_bohr for batch in batches]
        ),
    )


def evaluate_basin_density_gradient(
    data: CalculationData,
    points_bohr: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate the total density and gradient used by basin flow."""

    fields = evaluate_density_fields(data, np.asarray(points_bohr, dtype=float), kind="total")
    return fields.rho, fields.gradient


def _validate_all_electron_basin_input(data: CalculationData) -> tuple[np.ndarray, np.ndarray]:
    if data.basis is None:
        raise DataUnavailableError("QTAIM basin analysis requires a molecular basis set.")
    if data.total_density is None:
        raise DataUnavailableError("QTAIM basin analysis requires a total density matrix.")
    if data.total_density.kind != "total":
        raise ValidationError("QTAIM basin analysis requires the total molecular density channel.")
    if data.basis.ecp_metadata:
        raise ValidationError(
            "QTAIM basin analysis supports all-electron inputs only; ECP/pseudopotential metadata were found."
        )

    positions: list[tuple[float, float, float]] = []
    charges: list[float] = []
    for atom_index, atom in enumerate(data.molecule.atoms):
        if is_ghost_atom(atom):
            raise ValidationError(
                f"QTAIM basin analysis does not support ghost center at atom index {atom_index}."
            )
        charge = effective_nuclear_charge(atom)
        if abs(charge - float(atom.atomic_number)) > _ALL_ELECTRON_CHARGE_TOLERANCE:
            raise ValidationError(
                "QTAIM basin analysis supports all-electron inputs only; effective nuclear "
                f"charge differs from the atomic number at atom index {atom_index}, indicating ECP/pseudopotential treatment."
            )
        positions.append(tuple(float(value) / BOHR_TO_ANGSTROM for value in atom.coordinates))
        charges.append(charge)
    return np.asarray(positions, dtype=float), np.asarray(charges, dtype=float)


def _basin_bounds(
    atom_positions_bohr: np.ndarray,
    settings: QTAIMBasinSettings,
) -> tuple[np.ndarray, np.ndarray]:
    return (
        np.min(atom_positions_bohr, axis=0) - settings.bounds_padding_bohr,
        np.max(atom_positions_bohr, axis=0) + settings.bounds_padding_bohr,
    )


def _basin_attractor_seeds(atom_positions_bohr: np.ndarray) -> np.ndarray:
    shifts = np.asarray(
        (
            (0.0, 0.0, 0.0),
            (_ATTRACTOR_PERTURBATION_BOHR, 0.0, 0.0),
            (-_ATTRACTOR_PERTURBATION_BOHR, 0.0, 0.0),
            (0.0, _ATTRACTOR_PERTURBATION_BOHR, 0.0),
            (0.0, -_ATTRACTOR_PERTURBATION_BOHR, 0.0),
            (0.0, 0.0, _ATTRACTOR_PERTURBATION_BOHR),
            (0.0, 0.0, -_ATTRACTOR_PERTURBATION_BOHR),
        ),
        dtype=float,
    )
    seeds = (atom_positions_bohr[:, None, :] + shifts[None, :, :]).reshape(-1, 3)
    if len(seeds) > QTAIMSettings().max_seeds:
        raise ValueError(
            f"basin attractor seed count {len(seeds)} exceeds QTAIMSettings.max_seeds={QTAIMSettings().max_seeds}"
        )
    return seeds


def _discover_basin_critical_points(
    data: CalculationData,
    atom_positions_bohr: np.ndarray,
    settings: QTAIMBasinSettings,
) -> tuple[tuple[CriticalPoint, ...], SearchDiagnostics]:
    bounds = _basin_bounds(atom_positions_bohr, settings)
    qtaim_settings = QTAIMSettings(
        bounds_padding_bohr=settings.bounds_padding_bohr,
        max_seeds=QTAIMSettings().max_seeds,
    )

    def evaluator(points: np.ndarray):
        return evaluate_density_fields(data, points, kind="total")

    return search_critical_points(
        evaluator,
        _basin_attractor_seeds(atom_positions_bohr),
        bounds=bounds,
        settings=qtaim_settings,
    )


def _match_nuclear_attractors(
    atom_positions_bohr: np.ndarray,
    critical_points: tuple[CriticalPoint, ...],
    *,
    tolerance_bohr: float,
) -> tuple[np.ndarray, np.ndarray]:
    nuclear = tuple(point for point in critical_points if point.label == "(3,-3)")
    if not nuclear:
        raise ValidationError("QTAIM basin analysis found no nuclear attractors; required attractors are missing.")

    attractor_positions = np.asarray([point.position_bohr for point in nuclear], dtype=float)
    distances = np.linalg.norm(
        atom_positions_bohr[:, None, :] - attractor_positions[None, :, :],
        axis=2,
    )
    within = distances <= tolerance_bohr
    nucleus_counts = np.sum(within, axis=1)
    attractor_counts = np.sum(within, axis=0)

    if np.any(attractor_counts == 0):
        indices = np.flatnonzero(attractor_counts == 0).tolist()
        raise ValidationError(
            "QTAIM basin analysis detected non-nuclear attractor(s) outside the nuclear matching tolerance: "
            f"{indices}. Atomic-only basin populations are not defined for this case."
        )
    if np.any(nucleus_counts == 0):
        indices = np.flatnonzero(nucleus_counts == 0).tolist()
        raise ValidationError(
            f"QTAIM basin analysis has missing attractor/no unique nuclear attractor for nucleus indices {indices}."
        )
    if np.any(nucleus_counts > 1) or np.any(attractor_counts > 1):
        raise ValidationError(
            "QTAIM basin analysis found ambiguous/multiple nucleus-attractor matches within the matching tolerance."
        )

    ordered_indices = np.argmax(within, axis=1)
    ordered = attractor_positions[ordered_indices]
    matched_distances = distances[np.arange(len(atom_positions_bohr)), ordered_indices]
    return ordered, matched_distances


def prepare_qtaim_basin_attractors(
    data: CalculationData,
    *,
    settings: QTAIMBasinSettings | None = None,
) -> PreparedBasinAttractors:
    """Validate all-electron scope and prepare one nuclear attractor per nucleus."""

    controls = settings or QTAIMBasinSettings()
    atom_positions, nuclear_charges = _validate_all_electron_basin_input(data)
    critical_points, diagnostics = _discover_basin_critical_points(
        data,
        atom_positions,
        controls,
    )
    attractors, distances = _match_nuclear_attractors(
        atom_positions,
        critical_points,
        tolerance_bohr=controls.attractor_match_tolerance_bohr,
    )
    return PreparedBasinAttractors(
        physical_nucleus_indices=tuple(range(len(atom_positions))),
        nucleus_positions_bohr=atom_positions,
        nuclear_charges=nuclear_charges,
        attractor_positions_bohr=attractors,
        attractor_to_nucleus_distances_bohr=distances,
        bounds=_basin_bounds(atom_positions, controls),
        critical_points=critical_points,
        search_diagnostics=diagnostics,
        search_complete=False,
        warnings=(_BOUNDED_ATTRACTOR_WARNING,),
    )
