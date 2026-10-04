"""Shared real-space electronic fields built from analytic AO derivatives."""

from dataclasses import dataclass
from typing import Literal

import numpy as np

from ..errors import DataUnavailableError
from ..model import CalculationData, DensityMatrix
from ..results import ResultRecord
from .basis import bounded_ao_chunk_size, evaluate_ao_fields
from .density import density_matrix_for_kind
from .limits import bounded_point_chunk_size

DensityKind = Literal["total", "alpha", "beta", "spin"]
DENSITY_DERIVATIVE_CONVENTION = "analytic_cartesian_ao_product_rule"
KED_CONVENTION = "positive_definite_half_gradient_square"


@dataclass(frozen=True, slots=True)
class DensityFieldBatch:
    """Electron-density values and Cartesian derivatives in atomic units."""

    rho: np.ndarray
    gradient: np.ndarray
    hessian: np.ndarray
    laplacian: np.ndarray


@dataclass(frozen=True, slots=True)
class KineticEnergyDensityBatch:
    """Positive-definite kinetic-energy density in atomic units."""

    tau: np.ndarray
    convention: str = KED_CONVENTION


def _density_fields_for_matrix(
    data: CalculationData,
    density_matrix: DensityMatrix,
    points_bohr: np.ndarray,
) -> DensityFieldBatch:
    if data.basis is None:
        raise DataUnavailableError("Basis set is not available.")

    ao = evaluate_ao_fields(data.basis, data.molecule, points_bohr, derivatives=2)
    matrix = np.asarray(density_matrix.values, dtype=float)
    n_functions = ao.values.shape[1]
    if matrix.shape != (n_functions, n_functions):
        raise ValueError("density matrix size does not match evaluated basis functions")

    values = ao.values
    gradients = ao.gradients
    hessians = ao.hessians

    rho = np.einsum("pi,ij,pj->p", values, matrix, values, optimize=True)
    gradient = np.einsum(
        "pia,ij,pj->pa", gradients, matrix, values, optimize=True
    ) + np.einsum("pi,ij,pja->pa", values, matrix, gradients, optimize=True)
    hessian = (
        np.einsum("piab,ij,pj->pab", hessians, matrix, values, optimize=True)
        + np.einsum("pia,ij,pjb->pab", gradients, matrix, gradients, optimize=True)
        + np.einsum("pib,ij,pja->pab", gradients, matrix, gradients, optimize=True)
        + np.einsum("pi,ij,pjab->pab", values, matrix, hessians, optimize=True)
    )
    laplacian = np.trace(hessian, axis1=1, axis2=2)
    return DensityFieldBatch(
        rho=rho,
        gradient=gradient,
        hessian=hessian,
        laplacian=laplacian,
    )


def _kinetic_energy_density_for_matrix(
    data: CalculationData,
    density_matrix: DensityMatrix,
    points_bohr: np.ndarray,
) -> np.ndarray:
    if data.basis is None:
        raise DataUnavailableError("Basis set is not available.")

    ao = evaluate_ao_fields(data.basis, data.molecule, points_bohr, derivatives=1)
    matrix = np.asarray(density_matrix.values, dtype=float)
    n_functions = ao.values.shape[1]
    if matrix.shape != (n_functions, n_functions):
        raise ValueError("density matrix size does not match evaluated basis functions")
    return 0.5 * np.einsum(
        "pia,ij,pja->p",
        ao.gradients,
        matrix,
        ao.gradients,
        optimize=True,
    )


def _bounded_realspace_chunk_size(
    data: CalculationData,
    point_count: int,
    requested_chunk_size: int | None,
    *,
    requested_components: int,
) -> int:
    if data.basis is None:
        raise DataUnavailableError("Basis set is not available.")
    point_bound = bounded_point_chunk_size(
        point_count=point_count,
        nao=data.basis.n_functions,
        requested_components=requested_components,
        requested_chunk_size=requested_chunk_size,
    )
    # Preserve the stricter contraction-aware estimator used by older AO paths.
    return bounded_ao_chunk_size(data.basis, point_bound)


def _validate_points(points_bohr: np.ndarray) -> np.ndarray:
    points = np.asarray(points_bohr, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points_bohr must have shape (n_points, 3)")
    if not np.all(np.isfinite(points)):
        raise ValueError("points_bohr coordinates must be finite")
    return points


def evaluate_density_fields(
    data: CalculationData,
    points_bohr: np.ndarray,
    *,
    kind: DensityKind = "total",
    chunk_size: int | None = None,
) -> DensityFieldBatch:
    """Evaluate density, gradient, Hessian, and Laplacian at Bohr points.

    The Hessian uses the complete product rule and therefore remains correct
    without assuming an exactly symmetric stored density matrix.
    """

    if data.basis is None:
        raise DataUnavailableError("Basis set is not available.")
    points = _validate_points(points_bohr)
    size = _bounded_realspace_chunk_size(
        data,
        len(points),
        chunk_size,
        requested_components=13,
    )
    density_matrix = density_matrix_for_kind(data, kind)

    if len(points) == 0:
        return DensityFieldBatch(
            rho=np.empty((0,), dtype=float),
            gradient=np.empty((0, 3), dtype=float),
            hessian=np.empty((0, 3, 3), dtype=float),
            laplacian=np.empty((0,), dtype=float),
        )

    batches = [
        _density_fields_for_matrix(data, density_matrix, points[start : start + size])
        for start in range(0, len(points), size)
    ]
    return DensityFieldBatch(
        rho=np.concatenate([batch.rho for batch in batches]),
        gradient=np.concatenate([batch.gradient for batch in batches], axis=0),
        hessian=np.concatenate([batch.hessian for batch in batches], axis=0),
        laplacian=np.concatenate([batch.laplacian for batch in batches]),
    )


def evaluate_kinetic_energy_density(
    data: CalculationData,
    points_bohr: np.ndarray,
    *,
    kind: DensityKind = "total",
    chunk_size: int | None = None,
) -> KineticEnergyDensityBatch:
    """Evaluate the positive-definite half-gradient-square KED at Bohr points."""

    if data.basis is None:
        raise DataUnavailableError("Basis set is not available.")
    points = _validate_points(points_bohr)
    size = _bounded_realspace_chunk_size(
        data,
        len(points),
        chunk_size,
        requested_components=4,
    )
    density_matrix = density_matrix_for_kind(data, kind)

    if len(points) == 0:
        return KineticEnergyDensityBatch(tau=np.empty((0,), dtype=float))

    batches = [
        _kinetic_energy_density_for_matrix(
            data,
            density_matrix,
            points[start : start + size],
        )
        for start in range(0, len(points), size)
    ]
    return KineticEnergyDensityBatch(tau=np.concatenate(batches))


def density_derivatives(
    data: CalculationData,
    *,
    points_bohr: np.ndarray,
    kind: DensityKind = "total",
    chunk_size: int | None = None,
) -> ResultRecord:
    """Return analytic density derivatives at explicitly supplied Bohr points."""

    points = _validate_points(points_bohr)
    fields = evaluate_density_fields(data, points, kind=kind, chunk_size=chunk_size)
    finite_mask = (
        np.isfinite(fields.rho)
        & np.all(np.isfinite(fields.gradient), axis=1)
        & np.all(np.isfinite(fields.hessian), axis=(1, 2))
        & np.isfinite(fields.laplacian)
    )
    return ResultRecord(
        kind="density_derivatives",
        data={
            "points_bohr": points.tolist(),
            "channel": kind,
            "rho": fields.rho.tolist(),
            "gradient": fields.gradient.tolist(),
            "hessian": fields.hessian.tolist(),
            "laplacian": fields.laplacian.tolist(),
            "derivative_convention": DENSITY_DERIVATIVE_CONVENTION,
            "finite_mask": finite_mask.tolist(),
        },
        units={
            "points_bohr": "bohr",
            "rho": "electron/bohr^3",
            "gradient": "electron/bohr^4",
            "hessian": "electron/bohr^5",
            "laplacian": "electron/bohr^5",
        },
        validation_status="Experimental",
    )


def kinetic_energy_density(
    data: CalculationData,
    *,
    points_bohr: np.ndarray,
    kind: DensityKind = "total",
    chunk_size: int | None = None,
) -> ResultRecord:
    """Return positive-definite kinetic-energy density at supplied Bohr points."""

    points = _validate_points(points_bohr)
    result = evaluate_kinetic_energy_density(data, points, kind=kind, chunk_size=chunk_size)
    return ResultRecord(
        kind="kinetic_energy_density",
        data={
            "points_bohr": points.tolist(),
            "channel": kind,
            "tau": result.tau.tolist(),
            "convention": result.convention,
            "finite_mask": np.isfinite(result.tau).tolist(),
        },
        units={
            "points_bohr": "bohr",
            "tau": "hartree/bohr^3",
        },
        validation_status="Experimental",
    )
