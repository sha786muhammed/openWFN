"""Electron and spin-density evaluation and integration."""

from dataclasses import dataclass
from typing import Literal

import numpy as np

from ..constants import BOHR_TO_ANGSTROM
from ..errors import DataUnavailableError
from ..model import BasisSet, CalculationData, DensityMatrix, Molecule, VolumetricGrid
from .basis import evaluate_ao

DENSITY_RELATIVE_TOLERANCE = 5e-3
DENSITY_ZERO_ABSOLUTE_TOLERANCE = 5e-3
DENSITY_ZERO_TARGET_EPSILON = 1e-12


@dataclass(frozen=True, slots=True)
class IntegrationResult:
    electron_count: float
    expected_electrons: float
    absolute_error: float
    relative_error: float | None
    error_metric: Literal["absolute", "relative"]
    passed: bool


def density_matrix_for_kind(
    data: CalculationData,
    kind: Literal["total", "alpha", "beta", "spin"],
) -> DensityMatrix:
    """Return a requested density channel, deriving alpha/beta when necessary."""

    if kind not in {"total", "alpha", "beta", "spin"}:
        raise ValueError("density kind must be 'total', 'alpha', 'beta', or 'spin'")

    if kind == "total":
        if data.total_density is None:
            raise DataUnavailableError("Total density matrix is not available.")
        return data.total_density
    if kind == "spin":
        if data.spin_density is None:
            raise DataUnavailableError("Spin density matrix is not available.")
        return data.spin_density
    if data.total_density is None:
        raise DataUnavailableError("Total density matrix is required for spin-channel density.")
    if data.spin_density is None:
        raise DataUnavailableError("Spin density matrix is required for alpha/beta density.")
    total = np.asarray(data.total_density.values, dtype=float)
    spin = np.asarray(data.spin_density.values, dtype=float)
    if total.shape != spin.shape:
        raise ValueError("total and spin density matrices must have the same shape")
    values = 0.5 * (total + spin if kind == "alpha" else total - spin)
    source = (
        data.total_density.source
        if data.total_density.source == data.spin_density.source
        else "derived"
    )
    return DensityMatrix(
        tuple(tuple(float(value) for value in row) for row in values),
        kind,
        source=source,
    )


def evaluate_density(
    molecule: Molecule,
    basis: BasisSet,
    density_matrix: DensityMatrix,
    points_bohr: np.ndarray,
) -> np.ndarray:
    ao_values = evaluate_ao(basis, molecule, points_bohr)
    matrix = np.asarray(density_matrix.values, dtype=float)
    if matrix.shape != (ao_values.shape[1], ao_values.shape[1]):
        raise ValueError("density matrix size does not match evaluated basis functions")
    return np.einsum("pi,ij,pj->p", ao_values, matrix, ao_values, optimize=True)


def integrate_density(grid: VolumetricGrid, expected_electrons: float) -> IntegrationResult:
    """Integrate a density grid and evaluate conservation against its expected integral.

    Near-zero targets, which are valid for closed-shell spin densities, are
    validated with an absolute error. Nonzero targets use relative error.
    """

    axes_bohr = np.asarray(grid.axes, dtype=float) / BOHR_TO_ANGSTROM
    voxel_volume = abs(float(np.linalg.det(axes_bohr)))
    electron_count = float(np.sum(grid.values) * voxel_volume)
    absolute_error = abs(electron_count - expected_electrons)
    if abs(expected_electrons) <= DENSITY_ZERO_TARGET_EPSILON:
        return IntegrationResult(
            electron_count=electron_count,
            expected_electrons=expected_electrons,
            absolute_error=absolute_error,
            relative_error=None,
            error_metric="absolute",
            passed=absolute_error <= DENSITY_ZERO_ABSOLUTE_TOLERANCE,
        )
    relative_error = absolute_error / abs(expected_electrons)
    return IntegrationResult(
        electron_count=electron_count,
        expected_electrons=expected_electrons,
        absolute_error=absolute_error,
        relative_error=relative_error,
        error_metric="relative",
        passed=relative_error < DENSITY_RELATIVE_TOLERANCE,
    )
