"""Gaussian cube export for molecular scalar fields."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from ..constants import BOHR_TO_ANGSTROM
from ..model import Molecule, VolumetricGrid
from ..scientific import effective_nuclear_charge


def write_cube(
    grid: VolumetricGrid,
    molecule: Molecule,
    path: Path,
    overwrite: bool = False,
    *,
    comment: str | None = None,
) -> None:
    """Stream to a sibling temporary file and publish only a complete cube."""
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output exists: {path}. Pass overwrite=True to replace it.")
    temporary = None
    try:
        with NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                dir=path.parent, prefix='.openwfn-', delete=False) as stream:
            temporary = Path(stream.name)
            for line in _cube_lines(grid, molecule, comment):
                stream.write(line+'\n')
        if overwrite:
            os.replace(temporary, path)
        else:
            # Linking is atomic and refuses a target created during serialization.
            os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def format_cube(grid: VolumetricGrid, molecule: Molecule) -> str:
    """Serialize for callers that need embedded text; file exports stream."""
    return "\n".join(_cube_lines(grid, molecule)) + "\n"


def _cube_lines(grid: VolumetricGrid, molecule: Molecule, comment: str | None = None):
    origin_bohr = tuple(value / BOHR_TO_ANGSTROM for value in grid.origin)
    yield "openWFN scalar field"
    yield comment if comment is not None else f"units: {grid.value_unit}"
    yield (
        f"{len(molecule.atoms):5d} {origin_bohr[0]:13.6f} {origin_bohr[1]:13.6f} {origin_bohr[2]:13.6f}"
    )
    for count, axis in zip(grid.shape, grid.axes):
        axis_bohr = tuple(value / BOHR_TO_ANGSTROM for value in axis)
        yield (
            f"{count:5d} {axis_bohr[0]:13.6f} {axis_bohr[1]:13.6f} {axis_bohr[2]:13.6f}"
        )
    for atom in molecule.atoms:
        x, y, z = (value / BOHR_TO_ANGSTROM for value in atom.coordinates)
        nuclear_charge = effective_nuclear_charge(atom)
        yield (
            f"{atom.atomic_number:5d} {nuclear_charge:13.6f} {x:13.6f} {y:13.6f} {z:13.6f}"
        )
    for start in range(0, len(grid.values), 6):
        yield " ".join(f"{value:13.5E}" for value in grid.values[start : start + 6])
