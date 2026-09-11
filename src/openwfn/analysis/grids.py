"""Regular molecular grids shared by volumetric analyses."""

import numpy as np

from ..constants import BOHR_TO_ANGSTROM
from ..model import Molecule, VolumetricGrid


def molecular_grid_points(
    molecule: Molecule,
    *,
    spacing_bohr: float,
    padding_bohr: float,
) -> tuple[np.ndarray, tuple[float, float, float], tuple[int, int, int]]:
    if spacing_bohr <= 0.0:
        raise ValueError("grid spacing must be positive")
    if padding_bohr <= 0.0:
        raise ValueError("grid padding must be positive")
    coordinates = np.asarray([atom.coordinates for atom in molecule.atoms], dtype=float)
    coordinates /= BOHR_TO_ANGSTROM
    lower = np.floor((np.min(coordinates, axis=0) - padding_bohr) / spacing_bohr) * spacing_bohr
    upper = np.ceil((np.max(coordinates, axis=0) + padding_bohr) / spacing_bohr) * spacing_bohr
    axes = [
        lower[index]
        + np.arange(int(np.ceil((upper[index] - lower[index]) / spacing_bohr)) + 1) * spacing_bohr
        for index in range(3)
    ]
    mesh = np.meshgrid(*axes, indexing="ij")
    points = np.column_stack(tuple(component.ravel() for component in mesh))
    return points, tuple(float(value) for value in lower), tuple(len(axis) for axis in axes)


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
