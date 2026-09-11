"""Electrostatic-potential primitives in atomic units."""

import numpy as np

from ..constants import BOHR_TO_ANGSTROM
from ..model import Molecule, VolumetricGrid


def point_charge_esp(
    centers_bohr: np.ndarray,
    charges: np.ndarray,
    points_bohr: np.ndarray,
    *,
    singularity_value: float = float("nan"),
    singularity_tolerance: float = 1e-12,
) -> np.ndarray:
    """Evaluate ``sum(q_A / |r-R_A|)`` in atomic units.

    Points at a charge center are assigned ``singularity_value`` instead of
    producing an infinity that could silently contaminate a volumetric grid.
    """

    centers = np.asarray(centers_bohr, dtype=float)
    charge_values = np.asarray(charges, dtype=float)
    points = np.asarray(points_bohr, dtype=float)
    if centers.ndim != 2 or centers.shape[1] != 3:
        raise ValueError("centers_bohr must have shape (n_centers, 3)")
    if charge_values.ndim != 1 or len(charge_values) != len(centers):
        raise ValueError("charges must contain one charge per center")
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points_bohr must have shape (n_points, 3)")
    if singularity_tolerance < 0.0:
        raise ValueError("singularity_tolerance must be non-negative")

    distances = np.linalg.norm(points[:, None, :] - centers[None, :, :], axis=2)
    singular = np.any(distances <= singularity_tolerance, axis=1)
    safe_distances = np.where(distances <= singularity_tolerance, 1.0, distances)
    values = np.sum(charge_values[None, :] / safe_distances, axis=1)
    values[singular] = singularity_value
    return values


def nuclear_esp(
    molecule: Molecule,
    points_bohr: np.ndarray,
    *,
    singularity_value: float = float("nan"),
    singularity_tolerance: float = 1e-12,
) -> np.ndarray:
    """Evaluate the nuclear contribution to the molecular ESP in Hartree/e."""

    centers = np.asarray([atom.coordinates for atom in molecule.atoms], dtype=float)
    centers /= BOHR_TO_ANGSTROM
    charges = np.asarray([atom.atomic_number for atom in molecule.atoms], dtype=float)
    return point_charge_esp(
        centers,
        charges,
        points_bohr,
        singularity_value=singularity_value,
        singularity_tolerance=singularity_tolerance,
    )


def _grid_centers_and_charges(grid: VolumetricGrid) -> tuple[np.ndarray, np.ndarray]:
    axes_bohr = np.asarray(grid.axes, dtype=float) / BOHR_TO_ANGSTROM
    origin_bohr = np.asarray(grid.origin, dtype=float) / BOHR_TO_ANGSTROM
    indices = np.indices(grid.shape).reshape(3, -1).T
    centers = origin_bohr + indices @ axes_bohr
    voxel_volume = abs(float(np.linalg.det(axes_bohr)))
    electron_charges = -np.asarray(grid.values, dtype=float) * voxel_volume
    return centers, electron_charges


def electronic_esp_from_grid(
    electron_density: VolumetricGrid,
    points_bohr: np.ndarray,
    *,
    singularity_value: float = float("nan"),
    singularity_tolerance: float = 1e-12,
    chunk_size: int = 256,
) -> np.ndarray:
    """Approximate electronic ESP by Coulomb summation over density voxels.

    This quadrature is intentionally exposed as an Experimental method: its
    accuracy depends on the density-grid extent and spacing.
    """

    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    points = np.asarray(points_bohr, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points_bohr must have shape (n_points, 3)")
    centers, charges = _grid_centers_and_charges(electron_density)
    values = np.empty(len(points), dtype=float)
    for start in range(0, len(points), chunk_size):
        stop = min(start + chunk_size, len(points))
        values[start:stop] = point_charge_esp(
            centers,
            charges,
            points[start:stop],
            singularity_value=singularity_value,
            singularity_tolerance=singularity_tolerance,
        )
    return values


def total_esp_from_grid(
    molecule: Molecule,
    electron_density: VolumetricGrid,
    points_bohr: np.ndarray,
    *,
    singularity_value: float = float("nan"),
    singularity_tolerance: float = 1e-12,
) -> np.ndarray:
    """Combine nuclear ESP with Experimental density-grid electronic ESP."""

    nuclear = nuclear_esp(
        molecule,
        points_bohr,
        singularity_value=singularity_value,
        singularity_tolerance=singularity_tolerance,
    )
    electronic = electronic_esp_from_grid(
        electron_density,
        points_bohr,
        singularity_value=singularity_value,
        singularity_tolerance=singularity_tolerance,
    )
    return nuclear + electronic
