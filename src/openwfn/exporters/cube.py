"""Gaussian cube export for molecular scalar fields."""

from pathlib import Path

from ..constants import BOHR_TO_ANGSTROM
from ..model import Molecule, VolumetricGrid


def write_cube(
    grid: VolumetricGrid,
    molecule: Molecule,
    path: Path,
    overwrite: bool = False,
) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output exists: {path}. Pass overwrite=True to replace it.")
    path.write_text(format_cube(grid, molecule), encoding="utf-8")


def format_cube(grid: VolumetricGrid, molecule: Molecule) -> str:
    """Serialize a scalar field as Gaussian cube text."""

    origin_bohr = tuple(value / BOHR_TO_ANGSTROM for value in grid.origin)
    lines = ["openWFN scalar field", f"units: {grid.value_unit}"]
    lines.append(
        f"{len(molecule.atoms):5d} {origin_bohr[0]:13.6f} {origin_bohr[1]:13.6f} {origin_bohr[2]:13.6f}"
    )
    for count, axis in zip(grid.shape, grid.axes):
        axis_bohr = tuple(value / BOHR_TO_ANGSTROM for value in axis)
        lines.append(
            f"{count:5d} {axis_bohr[0]:13.6f} {axis_bohr[1]:13.6f} {axis_bohr[2]:13.6f}"
        )
    for atom in molecule.atoms:
        x, y, z = (value / BOHR_TO_ANGSTROM for value in atom.coordinates)
        lines.append(f"{atom.atomic_number:5d} {float(atom.atomic_number):13.6f} {x:13.6f} {y:13.6f} {z:13.6f}")
    for start in range(0, len(grid.values), 6):
        lines.append(" ".join(f"{value:13.5E}" for value in grid.values[start : start + 6]))
    return "\n".join(lines) + "\n"
