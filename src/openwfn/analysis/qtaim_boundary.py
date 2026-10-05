"""Sparse zero-flux diagnostics for Experimental QTAIM basin analysis."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Callable

import numpy as np

from . import limits
from .qtaim_basins import QTAIMBasinSettings, classify_basin_points

FieldEvaluator = Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]


@dataclass(frozen=True, slots=True)
class ZeroFluxDiagnostics:
    """Bounded sparse diagnostics for basin-boundary zero flux."""

    requested: bool
    status: str
    crossing_sample_count: int
    crossing_points_bohr: np.ndarray
    resolved_sample_count: int
    unresolved_sample_count: int
    median_residual: float | None
    p95_residual: float | None
    max_residual: float | None
    unresolved_plane_fit_count: int
    unresolved_gradient_count: int


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


def _fit_boundary_normal(points_bohr: np.ndarray, *, condition_ratio: float) -> np.ndarray | None:
    """Fit a local plane normal; reject point clouds without 2-D support."""

    points = np.asarray(points_bohr, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 3:
        return None
    if not np.all(np.isfinite(points)):
        return None
    centered = points - np.mean(points, axis=0, keepdims=True)
    try:
        _, singular_values, vh = np.linalg.svd(centered, full_matrices=False)
    except np.linalg.LinAlgError:
        return None
    if len(singular_values) < 2 or singular_values[0] <= 0.0:
        return None
    if singular_values[1] / singular_values[0] < condition_ratio:
        return None
    normal = np.asarray(vh[-1], dtype=float)
    norm = float(np.linalg.norm(normal))
    if not np.isfinite(norm) or norm <= 0.0:
        return None
    return normal / norm


def _boundary_residual(
    evaluator: FieldEvaluator,
    point_bohr: np.ndarray,
    normal: np.ndarray,
    *,
    gradient_floor: float,
) -> float | None:
    rho, gradient = evaluator(np.asarray(point_bohr, dtype=float).reshape(1, 3))
    density = np.asarray(rho, dtype=float)
    grad = np.asarray(gradient, dtype=float)
    if density.shape != (1,) or grad.shape != (1, 3):
        raise ValueError("field evaluator returned unexpected boundary-field shapes")
    vector = grad[0]
    if not np.isfinite(density[0]) or not np.all(np.isfinite(vector)):
        return None
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm <= gradient_floor:
        return None
    return float(abs(np.dot(vector, normal)) / norm)


def _axis_values(lower: float, upper: float, spacing: float) -> np.ndarray:
    span = upper - lower
    count = max(2, int(ceil(span / spacing)) + 1)
    return np.linspace(lower, upper, count, dtype=float)


def _probe_grid(
    bounds: tuple[np.ndarray, np.ndarray],
    settings: QTAIMBasinSettings,
) -> tuple[np.ndarray, tuple[int, int, int]]:
    lower, upper = _validate_bounds(bounds)
    padded_lower = lower - settings.boundary_padding_bohr
    padded_upper = upper + settings.boundary_padding_bohr
    counts = tuple(
        max(
            2,
            int(
                ceil(
                    (float(padded_upper[axis]) - float(padded_lower[axis]))
                    / settings.boundary_spacing_bohr
                )
            )
            + 1,
        )
        for axis in range(3)
    )
    point_count = int(counts[0] * counts[1] * counts[2])
    if point_count > limits.MAX_GRID_POINTS:
        raise ValueError(
            f"boundary probe grid requests {point_count:,} points, exceeding grid safety limit "
            f"{limits.MAX_GRID_POINTS:,}; no boundary grid was allocated."
        )
    axes = tuple(
        _axis_values(
            float(padded_lower[axis]),
            float(padded_upper[axis]),
            settings.boundary_spacing_bohr,
        )
        for axis in range(3)
    )
    mesh = np.meshgrid(*axes, indexing="ij")
    points = np.column_stack([component.reshape(-1) for component in mesh])
    return points, tuple(int(len(axis)) for axis in axes)


def _bisect_crossing(
    evaluator: FieldEvaluator,
    attractors_bohr: np.ndarray,
    left: np.ndarray,
    right: np.ndarray,
    left_basin: int,
    right_basin: int,
    *,
    bounds: tuple[np.ndarray, np.ndarray],
    settings: QTAIMBasinSettings,
) -> np.ndarray:
    a = np.asarray(left, dtype=float).copy()
    b = np.asarray(right, dtype=float).copy()
    basin_a = int(left_basin)
    basin_b = int(right_basin)
    for _ in range(settings.max_boundary_bisections):
        if float(np.linalg.norm(b - a)) <= settings.boundary_bisection_tolerance_bohr:
            break
        midpoint = 0.5 * (a + b)
        classified = classify_basin_points(
            evaluator,
            midpoint.reshape(1, 3),
            attractors_bohr,
            bounds=bounds,
            settings=settings,
            chunk_size=1,
        )
        status = str(classified.status[0])
        basin = int(classified.basin_indices[0])
        if status != "captured" or basin < 0:
            # A separatrix may itself converge to a saddle/gradient floor. That is a
            # useful crossing estimate; unrelated unresolved states remain explicit
            # later through the normal/gradient diagnostic.
            return midpoint
        if basin == basin_a:
            a = midpoint
        elif basin == basin_b:
            b = midpoint
        else:
            return midpoint
    return 0.5 * (a + b)


def _crossing_points(
    evaluator: FieldEvaluator,
    attractors_bohr: np.ndarray,
    grid_points: np.ndarray,
    shape: tuple[int, int, int],
    basin_indices: np.ndarray,
    statuses: np.ndarray,
    *,
    bounds: tuple[np.ndarray, np.ndarray],
    settings: QTAIMBasinSettings,
) -> np.ndarray:
    point_grid = grid_points.reshape(shape + (3,))
    basin_grid = basin_indices.reshape(shape)
    status_grid = statuses.reshape(shape)
    crossings: list[np.ndarray] = []

    for axis in range(3):
        left_slice = [slice(None)] * 3
        right_slice = [slice(None)] * 3
        left_slice[axis] = slice(0, shape[axis] - 1)
        right_slice[axis] = slice(1, shape[axis])
        left_slice_t = tuple(left_slice)
        right_slice_t = tuple(right_slice)

        left_status = status_grid[left_slice_t]
        right_status = status_grid[right_slice_t]
        left_basin = basin_grid[left_slice_t]
        right_basin = basin_grid[right_slice_t]
        mask = (
            (left_status == "captured")
            & (right_status == "captured")
            & (left_basin >= 0)
            & (right_basin >= 0)
            & (left_basin != right_basin)
        )
        for local_index in np.argwhere(mask):
            index_left = local_index.copy()
            index_right = local_index.copy()
            index_right[axis] += 1
            index_left_t = tuple(int(value) for value in index_left)
            index_right_t = tuple(int(value) for value in index_right)
            crossings.append(
                _bisect_crossing(
                    evaluator,
                    attractors_bohr,
                    point_grid[index_left_t],
                    point_grid[index_right_t],
                    int(basin_grid[index_left_t]),
                    int(basin_grid[index_right_t]),
                    bounds=bounds,
                    settings=settings,
                )
            )

    if not crossings:
        return np.empty((0, 3), dtype=float)
    return np.asarray(crossings, dtype=float)


def qtaim_zero_flux_diagnostics(
    evaluator: FieldEvaluator,
    attractors_bohr: np.ndarray,
    *,
    bounds: tuple[np.ndarray, np.ndarray],
    settings: QTAIMBasinSettings | None = None,
) -> ZeroFluxDiagnostics:
    """Sample basin crossings and estimate local zero-flux residuals."""

    settings = settings or QTAIMBasinSettings()
    attractors = np.asarray(attractors_bohr, dtype=float)
    if attractors.ndim != 2 or attractors.shape[1] != 3 or len(attractors) < 1:
        raise ValueError("attractors_bohr must have shape (n_attractors, 3)")
    if not np.all(np.isfinite(attractors)):
        raise ValueError("attractors_bohr must contain only finite coordinates")
    validated_bounds = _validate_bounds(bounds)
    grid_points, shape = _probe_grid(validated_bounds, settings)
    classified = classify_basin_points(
        evaluator,
        grid_points,
        attractors,
        bounds=(
            validated_bounds[0] - settings.boundary_padding_bohr,
            validated_bounds[1] + settings.boundary_padding_bohr,
        ),
        settings=settings,
    )
    crossings = _crossing_points(
        evaluator,
        attractors,
        grid_points,
        shape,
        classified.basin_indices,
        classified.status,
        bounds=(
            validated_bounds[0] - settings.boundary_padding_bohr,
            validated_bounds[1] + settings.boundary_padding_bohr,
        ),
        settings=settings,
    )

    residuals: list[float] = []
    unresolved_plane = 0
    unresolved_gradient = 0
    for point in crossings:
        distances = np.linalg.norm(crossings - point[None, :], axis=1)
        neighbors = crossings[distances <= settings.boundary_local_radius_bohr]
        if len(neighbors) < settings.boundary_min_neighbors:
            unresolved_plane += 1
            continue
        normal = _fit_boundary_normal(
            neighbors,
            condition_ratio=settings.boundary_plane_condition_ratio,
        )
        if normal is None:
            unresolved_plane += 1
            continue
        residual = _boundary_residual(
            evaluator,
            point,
            normal,
            gradient_floor=settings.gradient_floor,
        )
        if residual is None or not np.isfinite(residual):
            unresolved_gradient += 1
            continue
        residuals.append(float(residual))

    resolved_count = len(residuals)
    unresolved_count = len(crossings) - resolved_count
    if residuals:
        values = np.asarray(residuals, dtype=float)
        median = float(np.median(values))
        p95 = float(np.percentile(values, 95))
        maximum = float(np.max(values))
        status = "success" if p95 <= settings.max_zero_flux_p95 else "partial"
    else:
        median = None
        p95 = None
        maximum = None
        status = "partial"

    return ZeroFluxDiagnostics(
        requested=True,
        status=status,
        crossing_sample_count=len(crossings),
        crossing_points_bohr=crossings,
        resolved_sample_count=resolved_count,
        unresolved_sample_count=unresolved_count,
        median_residual=median,
        p95_residual=p95,
        max_residual=maximum,
        unresolved_plane_fit_count=unresolved_plane,
        unresolved_gradient_count=unresolved_gradient,
    )
