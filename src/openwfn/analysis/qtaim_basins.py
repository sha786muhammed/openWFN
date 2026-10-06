"""Bounded QTAIM atomic-basin classification and integration primitives.

Basin identity is determined by density-gradient ascent. The module keeps
trajectory classification, attractor preparation, population integration, and
boundary diagnostics as separate numerical layers so failures remain explicit.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from math import isfinite

import numpy as np

from ..constants import BOHR_TO_ANGSTROM, Z_TO_SYMBOL
from ..errors import DataUnavailableError, ValidationError
from ..model import CalculationData
from ..results import ResultRecord
from ..scientific import effective_nuclear_charge, expected_electron_count, is_ghost_atom
from . import limits
from .atom_quadrature import AtomQuadratureSettings, iter_atom_centered_chunks
from .density import evaluate_density
from .qtaim import CriticalPoint, QTAIMSettings, SearchDiagnostics, search_critical_points
from .realspace import evaluate_density_fields, evaluate_density_gradient

FieldEvaluator = Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]

_BOUNDED_ATTRACTOR_WARNING = (
    "QTAIM basin attractor discovery is bounded and not exhaustive; absence of "
    "an undiscovered non-nuclear attractor is not proven."
)
_ALL_ELECTRON_CHARGE_TOLERANCE = 1.0e-10
_ATTRACTOR_PERTURBATION_BOHR = 0.05
_POPULATION_ACCOUNTING_TOLERANCE = 1.0e-8
_NEGATIVE_DENSITY_TOLERANCE = 1.0e-10


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
        for name in ("density_ascent_abs_tolerance", "density_ascent_rel_tolerance"):
            value = getattr(self, name)
            if not isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be non-negative and finite")
        for name in (
            "max_flow_steps",
            "max_backtracks",
            "max_boundary_bisections",
            "boundary_min_neighbors",
        ):
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


@dataclass(frozen=True, slots=True)
class QTAIMBasinPopulationResult:
    """Typed numerical basin integration result before presentation."""

    populations: np.ndarray
    charges: np.ndarray
    integrated_electrons: float
    expected_electrons: float
    electron_count_residual: float
    resolved_population_sum: float
    unresolved_electrons: float
    population_partition_residual: float
    expected_molecular_charge: float
    integrated_atomic_charge: float
    charge_closure_residual: float
    unresolved_quadrature_weight: float
    resolved_point_count: int
    unresolved_point_count: int
    trajectory_termination_counts: dict[str, int]
    passed: bool
    warnings: tuple[str, ...]


def _validate_points(points_bohr: np.ndarray, name: str, *, allow_empty: bool = True) -> np.ndarray:
    points = np.asarray(points_bohr, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"{name} must have shape (n, 3)")
    if not allow_empty and len(points) == 0:
        raise ValueError(f"{name} must contain at least one point")
    if not np.all(np.isfinite(points)):
        raise ValueError(f"{name} must contain only finite coordinates")
    return points


def _validate_bounds(bounds: tuple[np.ndarray, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    lower = np.asarray(bounds[0], dtype=float)
    upper = np.asarray(bounds[1], dtype=float)
    if lower.shape != (3,) or upper.shape != (3,):
        raise ValueError("bounds must contain two Cartesian vectors with shape (3,)")
    if not np.all(np.isfinite(lower)) or not np.all(np.isfinite(upper)):
        raise ValueError("bounds must contain only finite values")
    if np.any(lower >= upper):
        raise ValueError("each lower bound must be smaller than the upper bound")
    return lower, upper


def _evaluate_field(evaluator: FieldEvaluator, points_bohr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
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
    distances = np.linalg.norm(points_bohr[:, None, :] - attractors_bohr[None, :, :], axis=2)
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
            current[active_ids], attractors_bohr, settings.attractor_capture_radius_bohr
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
        low_gradient = (~np.isfinite(gradient_norm)) | (gradient_norm <= settings.gradient_floor)
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
            candidate_points = current[moving_ids[pending_local]] + step_length * direction[pending_local]
            inside = np.all((candidate_points >= lower) & (candidate_points <= upper), axis=1)
            saw_inside[pending_local] |= inside
            if not np.any(inside):
                continue
            inside_local = pending_local[inside]
            inside_points = candidate_points[inside]
            candidate_rho, candidate_gradient = _evaluate_field(evaluator, inside_points)
            finite_candidate = np.isfinite(candidate_rho) & np.all(np.isfinite(candidate_gradient), axis=1)
            saw_finite[inside_local] |= finite_candidate
            if not np.any(finite_candidate):
                continue
            finite_local = inside_local[finite_candidate]
            finite_points = inside_points[finite_candidate]
            finite_rho = candidate_rho[finite_candidate]
            ascent_slack = settings.density_ascent_abs_tolerance + (
                settings.density_ascent_rel_tolerance * np.abs(moving_rho[finite_local])
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
                accepted_points, attractors_bohr, settings.attractor_capture_radius_bohr
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
        np.linalg.norm(current[:, None, :] - attractors_bohr[None, :, :], axis=2), axis=1
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
    attractors = _validate_points(attractors_bohr, "attractors_bohr", allow_empty=False)
    lower, upper = _validate_bounds(bounds)
    limits.validate_point_analysis_request(len(points))
    if chunk_size is not None and (
        isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size <= 0
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
    effective_chunk_size = len(points) if chunk_size is None else min(chunk_size, len(points))
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
        attractor_indices=np.concatenate([batch.attractor_indices for batch in batches]),
        status=np.concatenate([batch.status for batch in batches]),
        steps=np.concatenate([batch.steps for batch in batches]),
        final_points_bohr=np.concatenate([batch.final_points_bohr for batch in batches], axis=0),
        final_distances_bohr=np.concatenate([batch.final_distances_bohr for batch in batches]),
        path_lengths_bohr=np.concatenate([batch.path_lengths_bohr for batch in batches]),
    )


def evaluate_basin_density_gradient(
    data: CalculationData, points_bohr: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate total density and gradient used by basin flow."""

    return evaluate_density_gradient(data, np.asarray(points_bohr, dtype=float), kind="total")


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
    atom_positions_bohr: np.ndarray, settings: QTAIMBasinSettings
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
    maximum = QTAIMSettings().max_seeds
    if len(seeds) > maximum:
        raise ValueError(f"basin attractor seed count {len(seeds)} exceeds QTAIMSettings.max_seeds={maximum}")
    return seeds


def _discover_basin_critical_points(
    data: CalculationData,
    atom_positions_bohr: np.ndarray,
    settings: QTAIMBasinSettings,
) -> tuple[tuple[CriticalPoint, ...], SearchDiagnostics]:
    bounds = _basin_bounds(atom_positions_bohr, settings)
    qtaim_settings = QTAIMSettings(bounds_padding_bohr=settings.bounds_padding_bohr)

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
        atom_positions_bohr[:, None, :] - attractor_positions[None, :, :], axis=2
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
    critical_points, diagnostics = _discover_basin_critical_points(data, atom_positions, controls)
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


def _is_post_hf_method(method: str | None) -> bool:
    if not method:
        return False
    normalized = method.upper().replace("-", "").replace("_", "").replace(" ", "")
    candidates = [normalized]
    for prefix in ("RO", "R", "U"):
        if normalized.startswith(prefix):
            candidates.append(normalized[len(prefix) :])
    return any(candidate.startswith(("MP2", "MP3", "MP4", "CC", "CI", "QCI")) for candidate in candidates)


def _density_source_warnings(data: CalculationData) -> tuple[str, ...]:
    assert data.total_density is not None
    if data.total_density.source == "scf" and _is_post_hf_method(data.molecule.metadata.method):
        method = data.molecule.metadata.method or "post-HF"
        return (
            f"{method} calculation is using the SCF density because no supported post-SCF density was selected.",
        )
    return ()


def _validate_quadrature_request(data: CalculationData, settings: AtomQuadratureSettings) -> None:
    point_count = (
        len(data.molecule.atoms)
        * settings.radial_points
        * settings.theta_points
        * settings.phi_points
    )
    if point_count > limits.MAX_ATOM_QUADRATURE_POINTS:
        raise ValueError(
            f"quadrature point count {point_count} exceeds safety limit {limits.MAX_ATOM_QUADRATURE_POINTS}"
        )


def _integrate_qtaim_basin_populations(
    data: CalculationData,
    prepared: PreparedBasinAttractors,
    settings: QTAIMBasinSettings,
) -> QTAIMBasinPopulationResult:
    assert data.basis is not None
    assert data.total_density is not None
    _validate_quadrature_request(data, settings.quadrature)
    expectation = expected_electron_count(data, "total")
    populations = np.zeros(len(prepared.physical_nucleus_indices), dtype=float)
    integrated_electrons = 0.0
    unresolved_electrons = 0.0
    unresolved_weight = 0.0
    resolved_points = 0
    unresolved_points = 0
    terminations: Counter[str] = Counter()

    def flow_evaluator(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return evaluate_basin_density_gradient(data, points)

    for chunk in iter_atom_centered_chunks(data.molecule, settings.quadrature):
        rho = np.asarray(
            evaluate_density(
                data.molecule,
                data.basis,
                data.total_density,
                chunk.points_bohr,
            ),
            dtype=float,
        )
        if rho.shape != (len(chunk.points_bohr),) or not np.all(np.isfinite(rho)):
            raise ValidationError("QTAIM basin density evaluation produced non-finite or invalid values.")
        minimum = float(np.min(rho)) if len(rho) else 0.0
        if minimum < -_NEGATIVE_DENSITY_TOLERANCE:
            raise ValidationError(
                "QTAIM basin density evaluation produced materially negative density "
                f"({minimum:.6g} electron/bohr^3)."
            )
        rho = np.maximum(rho, 0.0)
        weighted = rho * np.asarray(chunk.integration_weights, dtype=float)
        integrated_electrons += float(np.sum(weighted))
        flow = classify_basin_points(
            flow_evaluator,
            chunk.points_bohr,
            prepared.attractor_positions_bohr,
            bounds=prepared.bounds,
            settings=settings,
            chunk_size=settings.quadrature.chunk_size,
        )
        if len(flow.basin_indices) != len(rho):
            raise ValidationError("QTAIM basin classifier returned a mismatched point count.")
        terminations.update(str(item) for item in flow.status.tolist())
        resolved = (flow.basin_indices >= 0) & (flow.status == "captured")
        for basin_index in range(len(populations)):
            mask = resolved & (flow.basin_indices == basin_index)
            populations[basin_index] += float(np.sum(weighted[mask]))
        unresolved = ~resolved
        resolved_points += int(np.count_nonzero(resolved))
        unresolved_points += int(np.count_nonzero(unresolved))
        unresolved_electrons += float(np.sum(weighted[unresolved]))
        unresolved_weight += float(np.sum(np.asarray(chunk.integration_weights)[unresolved]))

    population_sum = float(np.sum(populations))
    electron_residual = abs(integrated_electrons - float(expectation.value))
    partition_residual = abs(population_sum + unresolved_electrons - integrated_electrons)
    charges = prepared.nuclear_charges - populations
    integrated_charge = float(np.sum(charges))
    expected_charge = float(data.molecule.charge)
    charge_residual = abs(integrated_charge - expected_charge)
    passed = (
        unresolved_electrons <= settings.max_unresolved_electrons
        and electron_residual <= settings.max_electron_count_residual
        and partition_residual <= _POPULATION_ACCOUNTING_TOLERANCE
        and charge_residual <= settings.max_charge_closure_residual
    )
    warnings = [*expectation.warnings, *prepared.warnings, *_density_source_warnings(data)]
    if unresolved_electrons > settings.max_unresolved_electrons:
        warnings.append("Unresolved QTAIM trajectories contain electron density above the configured tolerance; populations were not renormalized.")
    if electron_residual > settings.max_electron_count_residual:
        warnings.append("Integrated molecular electron count failed the QTAIM basin electron-closure tolerance.")
    if partition_residual > _POPULATION_ACCOUNTING_TOLERANCE:
        warnings.append("Resolved plus unresolved QTAIM population accounting failed numerical closure.")
    if charge_residual > settings.max_charge_closure_residual:
        warnings.append("QTAIM atomic charges failed molecular charge closure; charges were not renormalized.")
    return QTAIMBasinPopulationResult(
        populations=populations,
        charges=charges,
        integrated_electrons=integrated_electrons,
        expected_electrons=float(expectation.value),
        electron_count_residual=electron_residual,
        resolved_population_sum=population_sum,
        unresolved_electrons=unresolved_electrons,
        population_partition_residual=partition_residual,
        expected_molecular_charge=expected_charge,
        integrated_atomic_charge=integrated_charge,
        charge_closure_residual=charge_residual,
        unresolved_quadrature_weight=unresolved_weight,
        resolved_point_count=resolved_points,
        unresolved_point_count=unresolved_points,
        trajectory_termination_counts=dict(sorted(terminations.items())),
        passed=passed,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def qtaim_basins(
    data: CalculationData,
    *,
    settings: QTAIMBasinSettings | None = None,
    include_boundary_diagnostics: bool = False,
) -> ResultRecord:
    """Integrate Experimental QTAIM atomic populations over gradient-flow basins."""

    controls = settings or QTAIMBasinSettings()
    prepared = prepare_qtaim_basin_attractors(data, settings=controls)
    integrated = _integrate_qtaim_basin_populations(data, prepared, controls)
    if include_boundary_diagnostics:
        from .qtaim_boundary import qtaim_zero_flux_diagnostics

        boundary_result = qtaim_zero_flux_diagnostics(
            lambda points: evaluate_basin_density_gradient(data, points),
            prepared.attractor_positions_bohr,
            bounds=prepared.bounds,
            settings=controls,
        )
        boundary: dict[str, object] = {
            "requested": boundary_result.requested,
            "status": boundary_result.status,
            "crossing_sample_count": boundary_result.crossing_sample_count,
            "resolved_sample_count": boundary_result.resolved_sample_count,
            "unresolved_sample_count": boundary_result.unresolved_sample_count,
            "median_residual": boundary_result.median_residual,
            "p95_residual": boundary_result.p95_residual,
            "max_residual": boundary_result.max_residual,
            "unresolved_plane_fit_count": boundary_result.unresolved_plane_fit_count,
            "unresolved_gradient_count": boundary_result.unresolved_gradient_count,
        }
        passed = integrated.passed and boundary_result.status == "success"
        if boundary_result.status == "success":
            warnings = integrated.warnings
        else:
            warnings = (
                *integrated.warnings,
                "Requested zero-flux boundary diagnostics did not meet the configured quality gate.",
            )
    else:
        boundary = {"status": "not_requested"}
        passed = integrated.passed
        warnings = integrated.warnings

    atoms: list[dict[str, object]] = []
    for basin_index, atom_index in enumerate(prepared.physical_nucleus_indices):
        atom = data.molecule.atoms[atom_index]
        atoms.append(
            {
                "atom_index": atom_index,
                "element": Z_TO_SYMBOL.get(atom.atomic_number, f"Z{atom.atomic_number}"),
                "nuclear_charge": float(prepared.nuclear_charges[basin_index]),
                "attractor_position_bohr": [float(value) for value in prepared.attractor_positions_bohr[basin_index]],
                "attractor_to_nucleus_distance_bohr": float(prepared.attractor_to_nucleus_distances_bohr[basin_index]),
                "electron_population": float(integrated.populations[basin_index]),
                "net_charge": float(integrated.charges[basin_index]),
            }
        )

    assert data.total_density is not None
    return ResultRecord(
        kind="qtaim_basins",
        data={
            "atoms": atoms,
            "diagnostics": {
                "expected_electrons": integrated.expected_electrons,
                "integrated_electrons": integrated.integrated_electrons,
                "electron_count_residual": integrated.electron_count_residual,
                "resolved_population_sum": integrated.resolved_population_sum,
                "unresolved_electrons": integrated.unresolved_electrons,
                "population_partition_residual": integrated.population_partition_residual,
                "expected_molecular_charge": integrated.expected_molecular_charge,
                "integrated_atomic_charge": integrated.integrated_atomic_charge,
                "charge_closure_residual": integrated.charge_closure_residual,
                "unresolved_quadrature_weight": integrated.unresolved_quadrature_weight,
                "resolved_point_count": integrated.resolved_point_count,
                "unresolved_point_count": integrated.unresolved_point_count,
                "trajectory_termination_counts": integrated.trajectory_termination_counts,
                "attractor_search_complete": prepared.search_complete,
                "attractor_search": asdict(prepared.search_diagnostics),
            },
            "boundary_diagnostics": boundary,
            "density_source": data.total_density.source,
            "formulas": {
                "population": "N_A = integral_{Omega_A} rho(r) dr",
                "charge": "q_A = Z_A - N_A",
                "basin_definition": "normalized density-gradient ascent to a unique attractor",
            },
            "settings": asdict(controls),
            "conventions": {
                "coordinates": "Cartesian bohr",
                "atom_indices": "zero-based",
                "basin_membership": "density-gradient flow; quadrature owner does not define basin",
                "isolated_molecule_basin_volume": "not reported",
            },
        },
        units={
            "electron_population": "electron",
            "net_charge": "elementary charge",
            "integrated_electrons": "electron",
            "expected_electrons": "electron",
            "electron_count_residual": "electron",
            "unresolved_electrons": "electron",
            "charge_closure_residual": "electron",
            "attractor_position_bohr": "bohr",
            "attractor_to_nucleus_distance_bohr": "bohr",
        },
        validation_status="Experimental",
        status="success" if passed else "partial",
        warnings=tuple(dict.fromkeys(warnings)),
    )
