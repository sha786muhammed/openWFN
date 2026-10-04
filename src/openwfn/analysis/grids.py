"""Regular molecular grids shared by volumetric analyses."""

from collections.abc import Iterator
from math import isfinite, prod

import numpy as np

from ..constants import BOHR_TO_ANGSTROM
from ..model import Molecule, VolumetricGrid
from .limits import MAX_GRID_POINTS


def molecular_grid_points(
    molecule: Molecule,
    *,
    spacing_bohr: float,
    padding_bohr: float,
) -> tuple[np.ndarray, tuple[float, float, float], tuple[int, int, int]]:
    if not isfinite(spacing_bohr) or spacing_bohr <= 0.0:
        raise ValueError("grid spacing must be positive and finite")
    if not isfinite(padding_bohr) or padding_bohr <= 0.0:
        raise ValueError("grid padding must be positive and finite")
    coordinates = np.asarray([atom.coordinates for atom in molecule.atoms], dtype=float)
    coordinates /= BOHR_TO_ANGSTROM
    lower = np.floor((np.min(coordinates, axis=0) - padding_bohr) / spacing_bohr) * spacing_bohr
    upper = np.ceil((np.max(coordinates, axis=0) + padding_bohr) / spacing_bohr) * spacing_bohr
    extents = np.ceil((upper - lower) / spacing_bohr)
    if not np.all(np.isfinite(extents)):
        raise ValueError("grid dimensions exceed the finite resource limit")
    shape = tuple(int(extent) + 1 for extent in extents)
    count = prod(shape)
    if count > MAX_GRID_POINTS:
        raise ValueError(
            f"Grid requests {count:,} points, exceeding the safety limit of "
            f"{MAX_GRID_POINTS:,}. Increase spacing or reduce padding; "
            "no grid was allocated."
        )
    axes = [
        lower[index]
        + np.arange(shape[index]) * spacing_bohr
        for index in range(3)
    ]
    # Broadcast into the final array: no three full-size mesh temporaries.
    points = np.empty((count, 3), dtype=float)
    ordered = points.reshape((*shape, 3))
    ordered[..., 0] = axes[0][:, None, None]
    ordered[..., 1] = axes[1][None, :, None]
    ordered[..., 2] = axes[2][None, None, :]
    return points, tuple(float(value) for value in lower), tuple(len(axis) for axis in axes)


def iter_point_chunks(points: np.ndarray, chunk_size: int) -> Iterator[np.ndarray]:
    """Yield ordered contiguous point chunks without changing grid layout."""
    if chunk_size <= 0:
        raise ValueError("chunk size must be positive")
    for start in range(0, len(points), chunk_size):
        yield points[start : start + chunk_size]


def scalar_grid(
    molecule: Molecule,
    values: np.ndarray,
    origin_bohr: tuple[float, float, float],
    shape: tuple[int, int, int],
    spacing_bohr: float,
    value_unit: str,
) -> VolumetricGrid:
    step = spacing_bohr * BOHR_TO_ANGSTROM
    return VolumetricGrid(
        origin=tuple(value * BOHR_TO_ANGSTROM for value in origin_bohr),
        axes=((step, 0.0, 0.0), (0.0, step, 0.0), (0.0, 0.0, step)),
        shape=shape,
        values=tuple(float(value) for value in np.asarray(values).ravel()),
        value_unit=value_unit,
    )
