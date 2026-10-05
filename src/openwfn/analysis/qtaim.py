"""Conservative QTAIM critical-point search and bond-path diagnostics.

The implementation deliberately treats critical-point discovery as bounded and
non-exhaustive.  It reuses the analytic density-gradient/Hessian engine and
reports numerical diagnostics instead of inferring completeness from a finite
seed search.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from math import isfinite
from typing import Callable

import numpy as np

from ..constants import BOHR_TO_ANGSTROM
from ..model import CalculationData
from ..results import ResultRecord
from .realspace import DensityFieldBatch, evaluate_density_fields

FieldEvaluator = Callable[[np.ndarray], DensityFieldBatch]
QTAIMLabel = str | None

_BOUNDED_SEARCH_WARNING = (
    "QTAIM critical-point search is bounded and not exhaustive; the reported "
    "topology may be incomplete."
)
_LABELS = ("(3,-3)", "(3,-1)", "(3,+1)", "(3,+3)")


@dataclass(frozen=True, slots=True)
class QTAIMSettings:
    """Numerical and resource limits for bounded QTAIM topology analysis."""

    gradient_tolerance: float = 1.0e-7
    curvature_tolerance: float = 1.0e-8
    trust_radius_bohr: float = 0.35
    max_iterations: int = 64
    max_backtracks: int = 8
    bounds_padding_bohr: float = 4.0
    merge_tolerance_bohr: float = 1.0e-3
    max_seeds: int = 2048
    max_pair_seeds: int = 1024
    path_step_bohr: float = 0.05
    path_initial_displacement_bohr: float = 0.02
    path_capture_radius_bohr: float = 0.35
    path_gradient_floor: float = 1.0e-10
    max_path_steps: int = 4000
    max_stored_path_points: int = 512

    def __post_init__(self) -> None:
        for name in (
            "gradient_tolerance",
            "curvature_tolerance",
            "trust_radius_bohr",
            "bounds_padding_bohr",
            "merge_tolerance_bohr",
            "path_step_bohr",
            "path_initial_displacement_bohr",
            "path_capture_radius_bohr",
            "path_gradient_floor",
        ):
            value = getattr(self, name)
            if not isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be positive and finite")
        for name in (
            "max_iterations",
            "max_backtracks",
            "max_seeds",
            "max_pair_seeds",
            "max_path_steps",
            "max_stored_path_points",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class QTAIMClassification:
    """Rank/signature classification of a symmetric density Hessian."""

    eigenvalues: tuple[float, float, float]
    rank: int
    signature: int | None
    label: QTAIMLabel


@dataclass(frozen=True, slots=True)
class CriticalPoint:
    """One converged stationary point of the electron density."""

    position_bohr: tuple[float, float, float]
    rho: float
    gradient_norm: float
    laplacian: float
    hessian_eigenvalues: tuple[float, float, float]
    rank: int
    signature: int | None
    label: QTAIMLabel
    iterations: int
    nearest_atom_index: int | None = None
    nearest_atom_distance_bohr: float | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "position_bohr": list(self.position_bohr),
            "rho": self.rho,
            "gradient_norm": self.gradient_norm,
            "laplacian": self.laplacian,
            "hessian_eigenvalues": list(self.hessian_eigenvalues),
            "rank": self.rank,
            "signature": self.signature,
            "label": self.label,
            "iterations": self.iterations,
            "nearest_atom_index": self.nearest_atom_index,
            "nearest_atom_distance_bohr": self.nearest_atom_distance_bohr,
        }


@dataclass(frozen=True, slots=True)
class SearchDiagnostics:
    """Finite accounting for the bounded critical-point seed search."""

    seed_count: int
    converged_seed_count: int
    failed_seed_count: int
    merged_critical_point_count: int


@dataclass(frozen=True, slots=True)
class BondPath:
    """Bounded pair of density-gradient ascent branches from one BCP."""

    points_bohr: tuple[tuple[float, float, float], ...]
    endpoint_atom_indices: tuple[int | None, int | None]
    termination_reasons: tuple[str, str]
    resolved: bool
    unresolved_reason: str | None
    length_bohr: float

    def as_dict(self) -> dict[str, object]:
        return {
            "points_bohr": [list(point) for point in self.points_bohr],
            "endpoint_atom_indices": list(self.endpoint_atom_indices),
            "termination_reasons": list(self.termination_reasons),
            "resolved": self.resolved,
            "unresolved_reason": self.unresolved_reason,
            "length_bohr": self.length_bohr,
        }


@dataclass(frozen=True, slots=True)
class QTAIMTopology:
    """Critical points plus explicit bounded-search diagnostics."""

    critical_points: tuple[CriticalPoint, ...]
    diagnostics: SearchDiagnostics
    counts: dict[str, int]
    topology_relation_value: int
    topology_relation_satisfied: bool
    search_complete: bool
    warnings: tuple[str, ...]
    bounds: tuple[np.ndarray, np.ndarray]


def classify_qtaim_hessian(
    hessian: np.ndarray,
    *,
    curvature_tolerance: float,
) -> QTAIMClassification:
    """Classify a finite 3x3 density Hessian by QTAIM rank/signature."""

    matrix = np.asarray(hessian, dtype=float)
    if matrix.shape != (3, 3):
        raise ValueError("hessian must have shape (3, 3)")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("hessian must contain only finite values")
    if not isfinite(curvature_tolerance) or curvature_tolerance <= 0.0:
        raise ValueError("curvature_tolerance must be positive and finite")

    symmetric = 0.5 * (matrix + matrix.T)
    eigenvalues_array = np.linalg.eigvalsh(symmetric)
    eigenvalues = tuple(float(value) for value in eigenvalues_array)
    rank = int(np.count_nonzero(np.abs(eigenvalues_array) > curvature_tolerance))
    if rank != 3:
        return QTAIMClassification(eigenvalues, rank, None, None)

    signature = int(np.sum(np.where(eigenvalues_array > 0.0, 1, -1)))
    label = {
        -3: "(3,-3)",
        -1: "(3,-1)",
        1: "(3,+1)",
        3: "(3,+3)",
    }.get(signature)
    return QTAIMClassification(eigenvalues, rank, signature, label)


def topology_relation(counts: dict[str, int]) -> int:
    """Return N_NCP - N_BCP + N_RCP - N_CCP for a finite molecule."""

    return (
        int(counts.get("(3,-3)", 0))
        - int(counts.get("(3,-1)", 0))
        + int(counts.get("(3,+1)", 0))
        - int(counts.get("(3,+3)", 0))
    )


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


def _validate_seeds(seeds_bohr: np.ndarray, settings: QTAIMSettings) -> np.ndarray:
    seeds = np.asarray(seeds_bohr, dtype=float)
    if seeds.ndim != 2 or seeds.shape[1] != 3:
        raise ValueError("seeds_bohr must have shape (n_seeds, 3)")
    if not np.all(np.isfinite(seeds)):
        raise ValueError("seeds_bohr coordinates must be finite")
    if len(seeds) > settings.max_seeds:
        raise ValueError(
            f"seed count {len(seeds)} exceeds QTAIMSettings.max_seeds={settings.max_seeds}"
        )
    return seeds


def _inside_bounds(point: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> bool:
    return bool(np.all(point >= lower) and np.all(point <= upper))


def _single_field(evaluator: FieldEvaluator, point: np.ndarray) -> tuple[float, np.ndarray, np.ndarray, float] | None:
    batch = evaluator(np.asarray(point, dtype=float).reshape(1, 3))
    if (
        batch.rho.shape != (1,)
        or batch.gradient.shape != (1, 3)
        or batch.hessian.shape != (1, 3, 3)
        or batch.laplacian.shape != (1,)
    ):
        raise ValueError("field evaluator returned unexpected density-field shapes")
    rho = float(batch.rho[0])
    gradient = np.asarray(batch.gradient[0], dtype=float)
    hessian = np.asarray(batch.hessian[0], dtype=float)
    laplacian = float(batch.laplacian[0])
    if not (
        isfinite(rho)
        and np.all(np.isfinite(gradient))
        and np.all(np.isfinite(hessian))
        and isfinite(laplacian)
    ):
        return None
    return rho, gradient, hessian, laplacian


def _newton_step(hessian: np.ndarray, gradient: np.ndarray, settings: QTAIMSettings) -> np.ndarray | None:
    symmetric = 0.5 * (hessian + hessian.T)
    try:
        eigenvalues = np.linalg.eigvalsh(symmetric)
    except np.linalg.LinAlgError:
        return None
    largest = float(np.max(np.abs(eigenvalues)))
    if not isfinite(largest) or largest == 0.0:
        return None
    smallest = float(np.min(np.abs(eigenvalues)))
    try:
        if smallest > settings.curvature_tolerance:
            step = np.linalg.solve(symmetric, -gradient)
        else:
            rcond = min(0.5, settings.curvature_tolerance / largest)
            step = np.linalg.pinv(symmetric, rcond=rcond) @ (-gradient)
    except np.linalg.LinAlgError:
        return None
    if not np.all(np.isfinite(step)):
        return None
    norm = float(np.linalg.norm(step))
    if norm == 0.0:
        return None
    if norm > settings.trust_radius_bohr:
        step = step * (settings.trust_radius_bohr / norm)
    return step


def _critical_point_from_field(
    point: np.ndarray,
    field: tuple[float, np.ndarray, np.ndarray, float],
    *,
    iterations: int,
    settings: QTAIMSettings,
) -> CriticalPoint:
    rho, gradient, hessian, laplacian = field
    classification = classify_qtaim_hessian(
        hessian,
        curvature_tolerance=settings.curvature_tolerance,
    )
    return CriticalPoint(
        position_bohr=tuple(float(value) for value in point),
        rho=rho,
        gradient_norm=float(np.linalg.norm(gradient)),
        laplacian=laplacian,
        hessian_eigenvalues=classification.eigenvalues,
        rank=classification.rank,
        signature=classification.signature,
        label=classification.label,
        iterations=iterations,
    )


def _solve_critical_point(
    evaluator: FieldEvaluator,
    seed_bohr: np.ndarray,
    *,
    bounds: tuple[np.ndarray, np.ndarray],
    settings: QTAIMSettings,
) -> CriticalPoint | None:
    lower, upper = bounds
    point = np.asarray(seed_bohr, dtype=float).copy()
    if not _inside_bounds(point, lower, upper):
        return None

    for iteration in range(settings.max_iterations):
        field = _single_field(evaluator, point)
        if field is None:
            return None
        _, gradient, hessian, _ = field
        residual = float(np.linalg.norm(gradient))
        if residual <= settings.gradient_tolerance:
            return _critical_point_from_field(
                point,
                field,
                iterations=iteration,
                settings=settings,
            )

        step = _newton_step(hessian, gradient, settings)
        if step is None:
            return None

        accepted = False
        for backtrack in range(settings.max_backtracks):
            scale = 0.5**backtrack
            candidate = point + scale * step
            if not _inside_bounds(candidate, lower, upper):
                continue
            candidate_field = _single_field(evaluator, candidate)
            if candidate_field is None:
                continue
            candidate_residual = float(np.linalg.norm(candidate_field[1]))
            if candidate_residual < residual:
                point = candidate
                accepted = True
                break
        if not accepted:
            return None

    field = _single_field(evaluator, point)
    if field is None or float(np.linalg.norm(field[1])) > settings.gradient_tolerance:
        return None
    return _critical_point_from_field(
        point,
        field,
        iterations=settings.max_iterations,
        settings=settings,
    )


def _compatible_for_merge(left: CriticalPoint, right: CriticalPoint) -> bool:
    return left.label == right.label and left.rank == right.rank


def _merge_critical_points(
    points: list[CriticalPoint], settings: QTAIMSettings
) -> tuple[CriticalPoint, ...]:
    merged: list[CriticalPoint] = []
    for point in points:
        position = np.asarray(point.position_bohr, dtype=float)
        match_index = None
        for index, existing in enumerate(merged):
            if not _compatible_for_merge(point, existing):
                continue
            distance = float(
                np.linalg.norm(position - np.asarray(existing.position_bohr, dtype=float))
            )
            if distance <= settings.merge_tolerance_bohr:
                match_index = index
                break
        if match_index is None:
            merged.append(point)
        elif point.gradient_norm < merged[match_index].gradient_norm:
            merged[match_index] = point
    return tuple(merged)


def search_critical_points(
    evaluator: FieldEvaluator,
    seeds_bohr: np.ndarray,
    *,
    bounds: tuple[np.ndarray, np.ndarray],
    settings: QTAIMSettings | None = None,
) -> tuple[tuple[CriticalPoint, ...], SearchDiagnostics]:
    """Run deterministic bounded stationary-point searches from explicit seeds."""

    settings = settings or QTAIMSettings()
    seeds = _validate_seeds(seeds_bohr, settings)
    validated_bounds = _validate_bounds(bounds)

    converged: list[CriticalPoint] = []
    for seed in seeds:
        point = _solve_critical_point(
            evaluator,
            seed,
            bounds=validated_bounds,
            settings=settings,
        )
        if point is not None:
            converged.append(point)

    merged = _merge_critical_points(converged, settings)
    diagnostics = SearchDiagnostics(
        seed_count=len(seeds),
        converged_seed_count=len(converged),
        failed_seed_count=len(seeds) - len(converged),
        merged_critical_point_count=len(merged),
    )
    return merged, diagnostics


def _atom_positions_bohr(data: CalculationData) -> np.ndarray:
    return np.asarray(
        [atom.coordinates for atom in data.molecule.atoms],
        dtype=float,
    ) / BOHR_TO_ANGSTROM


def _molecular_bounds(
    atom_positions_bohr: np.ndarray, settings: QTAIMSettings
) -> tuple[np.ndarray, np.ndarray]:
    lower = np.min(atom_positions_bohr, axis=0) - settings.bounds_padding_bohr
    upper = np.max(atom_positions_bohr, axis=0) + settings.bounds_padding_bohr
    return lower, upper


def _molecular_seeds(data: CalculationData, settings: QTAIMSettings) -> np.ndarray:
    atom_positions = _atom_positions_bohr(data)
    if len(atom_positions) > settings.max_seeds:
        raise ValueError(
            f"atom count {len(atom_positions)} exceeds QTAIMSettings.max_seeds="
            f"{settings.max_seeds}"
        )

    seeds: list[np.ndarray] = [position.copy() for position in atom_positions]
    pair_count = 0
    for left in range(len(atom_positions)):
        for right in range(left + 1, len(atom_positions)):
            if pair_count >= settings.max_pair_seeds or len(seeds) >= settings.max_seeds:
                break
            seeds.append(0.5 * (atom_positions[left] + atom_positions[right]))
            pair_count += 1
        if pair_count >= settings.max_pair_seeds or len(seeds) >= settings.max_seeds:
            break

    if len(seeds) < settings.max_seeds:
        seeds.append(np.mean(atom_positions, axis=0))
    return np.asarray(seeds, dtype=float)


def _attach_nearest_atoms(
    points: tuple[CriticalPoint, ...], atom_positions_bohr: np.ndarray
) -> tuple[CriticalPoint, ...]:
    attached: list[CriticalPoint] = []
    for point in points:
        distances = np.linalg.norm(
            atom_positions_bohr - np.asarray(point.position_bohr, dtype=float)[None, :],
            axis=1,
        )
        nearest_index = int(np.argmin(distances))
        attached.append(
            replace(
                point,
                nearest_atom_index=nearest_index,
                nearest_atom_distance_bohr=float(distances[nearest_index]),
            )
        )
    return tuple(attached)


def _count_critical_points(points: tuple[CriticalPoint, ...]) -> dict[str, int]:
    counts = {label: 0 for label in _LABELS}
    counts["unclassified"] = 0
    for point in points:
        if point.label in counts:
            counts[point.label] += 1  # type: ignore[index]
        else:
            counts["unclassified"] += 1
    return counts


def find_qtaim_critical_points(
    data: CalculationData,
    *,
    seeds_bohr: np.ndarray | None = None,
    settings: QTAIMSettings | None = None,
) -> QTAIMTopology:
    """Find a bounded, explicitly non-exhaustive set of QTAIM critical points."""

    settings = settings or QTAIMSettings()
    atom_positions = _atom_positions_bohr(data)
    bounds = _molecular_bounds(atom_positions, settings)
    seeds = (
        _molecular_seeds(data, settings)
        if seeds_bohr is None
        else _validate_seeds(seeds_bohr, settings)
    )

    def evaluator(points: np.ndarray) -> DensityFieldBatch:
        return evaluate_density_fields(data, points, kind="total")

    points, diagnostics = search_critical_points(
        evaluator,
        seeds,
        bounds=bounds,
        settings=settings,
    )
    points = _attach_nearest_atoms(points, atom_positions)
    counts = _count_critical_points(points)
    relation = topology_relation(counts)
    warnings = [_BOUNDED_SEARCH_WARNING]
    if relation != 1:
        warnings.append(
            "The finite-molecule QTAIM topology relation is not satisfied; "
            "the bounded critical-point set is incomplete or numerically unresolved."
        )
    return QTAIMTopology(
        critical_points=points,
        diagnostics=diagnostics,
        counts=counts,
        topology_relation_value=relation,
        topology_relation_satisfied=relation == 1,
        search_complete=False,
        warnings=tuple(warnings),
        bounds=bounds,
    )


def _nearest_captured_atom(
    point: np.ndarray,
    atom_positions_bohr: np.ndarray,
    capture_radius_bohr: float,
) -> int | None:
    distances = np.linalg.norm(atom_positions_bohr - point[None, :], axis=1)
    nearest = int(np.argmin(distances))
    if float(distances[nearest]) <= capture_radius_bohr:
        return nearest
    return None


def _trace_gradient_branch(
    evaluator: FieldEvaluator,
    start: np.ndarray,
    *,
    atom_positions_bohr: np.ndarray,
    bounds: tuple[np.ndarray, np.ndarray],
    settings: QTAIMSettings,
) -> tuple[list[np.ndarray], int | None, str]:
    lower, upper = bounds
    point = np.asarray(start, dtype=float).copy()
    points = [point.copy()]
    for _ in range(settings.max_path_steps):
        captured = _nearest_captured_atom(
            point,
            atom_positions_bohr,
            settings.path_capture_radius_bohr,
        )
        if captured is not None:
            return points, captured, "captured_atom"
        if not _inside_bounds(point, lower, upper):
            return points, None, "left_bounds"
        field = _single_field(evaluator, point)
        if field is None:
            return points, None, "nonfinite_field"
        gradient = field[1]
        norm = float(np.linalg.norm(gradient))
        if norm <= settings.path_gradient_floor:
            return points, None, "gradient_too_small"
        point = point + settings.path_step_bohr * (gradient / norm)
        if not np.all(np.isfinite(point)):
            return points, None, "nonfinite_step"
        points.append(point.copy())
    return points, None, "step_limit"


def _polyline_length(points: list[np.ndarray]) -> float:
    if len(points) < 2:
        return 0.0
    array = np.asarray(points, dtype=float)
    return float(np.sum(np.linalg.norm(np.diff(array, axis=0), axis=1)))


def _downsample_path(
    points: list[np.ndarray], max_points: int
) -> tuple[tuple[float, float, float], ...]:
    if len(points) > max_points:
        indices = np.linspace(0, len(points) - 1, max_points, dtype=int)
        points = [points[index] for index in np.unique(indices)]
    return tuple(tuple(float(value) for value in point) for point in points)


def trace_bond_path_for_field(
    evaluator: FieldEvaluator,
    *,
    bcp_position_bohr: np.ndarray,
    atom_positions_bohr: np.ndarray,
    bounds: tuple[np.ndarray, np.ndarray],
    settings: QTAIMSettings | None = None,
) -> BondPath:
    """Trace two bounded density-gradient ascent branches from a BCP position."""

    settings = settings or QTAIMSettings()
    bcp = np.asarray(bcp_position_bohr, dtype=float)
    atoms = np.asarray(atom_positions_bohr, dtype=float)
    lower, upper = _validate_bounds(bounds)
    if bcp.shape != (3,) or not np.all(np.isfinite(bcp)):
        raise ValueError("bcp_position_bohr must be a finite Cartesian vector")
    if atoms.ndim != 2 or atoms.shape[1] != 3 or len(atoms) == 0:
        raise ValueError("atom_positions_bohr must have shape (n_atoms, 3)")
    if not np.all(np.isfinite(atoms)):
        raise ValueError("atom_positions_bohr coordinates must be finite")

    field = _single_field(evaluator, bcp)
    if field is None:
        raise ValueError("BCP field is nonfinite")
    hessian = 0.5 * (field[2] + field[2].T)
    classification = classify_qtaim_hessian(
        hessian,
        curvature_tolerance=settings.curvature_tolerance,
    )
    if classification.label != "(3,-1)":
        raise ValueError("bond-path tracing requires a nondegenerate (3,-1) BCP")

    eigenvalues, eigenvectors = np.linalg.eigh(hessian)
    direction = eigenvectors[:, int(np.argmax(eigenvalues))]
    direction = direction / np.linalg.norm(direction)

    minus_start = bcp - settings.path_initial_displacement_bohr * direction
    plus_start = bcp + settings.path_initial_displacement_bohr * direction
    minus_points, minus_atom, minus_reason = _trace_gradient_branch(
        evaluator,
        minus_start,
        atom_positions_bohr=atoms,
        bounds=(lower, upper),
        settings=settings,
    )
    plus_points, plus_atom, plus_reason = _trace_gradient_branch(
        evaluator,
        plus_start,
        atom_positions_bohr=atoms,
        bounds=(lower, upper),
        settings=settings,
    )

    full_path = [*reversed(minus_points), bcp.copy(), *plus_points]
    length = _polyline_length(full_path)
    captured_both = minus_reason == "captured_atom" and plus_reason == "captured_atom"
    resolved = captured_both and minus_atom is not None and plus_atom is not None and minus_atom != plus_atom
    unresolved_reason = None
    if not resolved:
        if captured_both and minus_atom == plus_atom:
            unresolved_reason = "same_atom_endpoint"
        else:
            unresolved_reason = f"branch_termination:{minus_reason},{plus_reason}"

    return BondPath(
        points_bohr=_downsample_path(full_path, settings.max_stored_path_points),
        endpoint_atom_indices=(minus_atom, plus_atom),
        termination_reasons=(minus_reason, plus_reason),
        resolved=resolved,
        unresolved_reason=unresolved_reason,
        length_bohr=length,
    )


def trace_bond_path(
    data: CalculationData,
    bcp: CriticalPoint,
    *,
    settings: QTAIMSettings | None = None,
) -> BondPath:
    """Trace a bounded molecular bond path for one converged BCP."""

    settings = settings or QTAIMSettings()
    atoms = _atom_positions_bohr(data)
    bounds = _molecular_bounds(atoms, settings)

    def evaluator(points: np.ndarray) -> DensityFieldBatch:
        return evaluate_density_fields(data, points, kind="total")

    return trace_bond_path_for_field(
        evaluator,
        bcp_position_bohr=np.asarray(bcp.position_bohr, dtype=float),
        atom_positions_bohr=atoms,
        bounds=bounds,
        settings=settings,
    )


def qtaim(
    data: CalculationData,
    *,
    seeds_bohr: np.ndarray | None = None,
    settings: QTAIMSettings | None = None,
    include_bond_paths: bool = True,
) -> ResultRecord:
    """Return bounded QTAIM topology diagnostics for the total electron density."""

    settings = settings or QTAIMSettings()
    topology = find_qtaim_critical_points(
        data,
        seeds_bohr=seeds_bohr,
        settings=settings,
    )
    bond_paths: list[BondPath] = []
    if include_bond_paths:
        for point in topology.critical_points:
            if point.label == "(3,-1)":
                bond_paths.append(trace_bond_path(data, point, settings=settings))

    warnings = list(topology.warnings)
    unresolved_count = sum(not path.resolved for path in bond_paths)
    if unresolved_count:
        warnings.append(
            f"{unresolved_count} QTAIM bond path(s) did not resolve to two distinct atoms."
        )

    return ResultRecord(
        kind="qtaim_topology",
        data={
            "settings": asdict(settings),
            "critical_points": [point.as_dict() for point in topology.critical_points],
            "counts": dict(topology.counts),
            "seed_count": topology.diagnostics.seed_count,
            "converged_seed_count": topology.diagnostics.converged_seed_count,
            "failed_seed_count": topology.diagnostics.failed_seed_count,
            "topology_relation": topology.topology_relation_value,
            "topology_relation_satisfied": topology.topology_relation_satisfied,
            "search_complete": topology.search_complete,
            "bond_paths": [path.as_dict() for path in bond_paths],
        },
        units={
            "position_bohr": "bohr",
            "rho": "electron/bohr^3",
            "gradient_norm": "electron/bohr^4",
            "laplacian": "electron/bohr^5",
            "hessian_eigenvalues": "electron/bohr^5",
            "bond_path_points_bohr": "bohr",
            "bond_path_length_bohr": "bohr",
        },
        validation_status="Experimental",
        status="partial",
        warnings=tuple(warnings),
    )
