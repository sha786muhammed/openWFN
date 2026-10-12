"""Gaussian cube export for molecular scalar fields."""

import os
from collections.abc import Iterable
from math import isfinite, prod
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np

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
    _write_lines(path, _cube_lines(grid, molecule, comment), overwrite)


def _write_lines(path: Path, lines: Iterable[str], overwrite: bool) -> None:
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output exists: {path}. Pass overwrite=True to replace it.")
    temporary = None
    try:
        with NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                dir=path.parent, prefix='.openwfn-', delete=False) as stream:
            temporary = Path(stream.name)
            for line in lines:
                stream.write(line+'\n')
        if overwrite:
            os.replace(temporary, path)
        else:
            # Linking is atomic and refuses a target created during serialization.
            os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_cube_chunks(
    molecule: Molecule, path: Path, *, origin_bohr: tuple[float, float, float],
    shape: tuple[int, int, int], spacing_bohr: float, value_unit: str,
    chunks: Iterable[np.ndarray], overwrite: bool = False, comment: str | None = None,
    squared: bool = False,
) -> float:
    """Publish blocks and return their compensated sum (or squared-value sum)."""
    axes = ((spacing_bohr, 0., 0.), (0., spacing_bohr, 0.), (0., 0., spacing_bohr))
    total = correction = 0.

    def lines():
        nonlocal total, correction
        yield from _cube_header(origin_bohr, axes, shape, value_unit, molecule, comment)
        row = []
        count = 0
        for chunk in chunks:
            values = np.asarray(chunk)
            if values.ndim != 1 or not np.all(np.isfinite(values)):
                raise ValueError("Cube blocks must contain finite scalar values")
            partial = float(np.sum(np.square(values) if squared else values, dtype=np.float64))
            if not isfinite(partial):
                raise ValueError("Cube integral contains nonfinite values")
            combined = total + partial
            correction += ((total - combined) + partial if abs(total) >= abs(partial)
                           else (partial - combined) + total)
            total = combined
            count += len(values)
            if count > prod(shape):
                raise ValueError("Cube stream exceeds the declared grid size")
            for value in values:
                row.append(f"{value:13.5E}")
                if len(row) == 6:
                    yield " ".join(row)
                    row = []
        if count != prod(shape):
            raise ValueError("Cube stream does not match the declared grid size")
        if not isfinite(total + correction):
            raise ValueError("Cube integral contains nonfinite values")
        if row:
            yield " ".join(row)

    _write_lines(path, lines(), overwrite)
    return total + correction


def format_cube(grid: VolumetricGrid, molecule: Molecule, *, comment: str | None = None) -> str:
    """Serialize for callers that need embedded text; file exports stream."""
    return "\n".join(_cube_lines(grid, molecule, comment)) + "\n"


def _cube_lines(grid: VolumetricGrid, molecule: Molecule, comment: str | None = None):
    origin_bohr = tuple(value / BOHR_TO_ANGSTROM for value in grid.origin)
    axes_bohr = tuple(tuple(value / BOHR_TO_ANGSTROM for value in axis) for axis in grid.axes)
    yield from _cube_header(origin_bohr, axes_bohr, grid.shape, grid.value_unit, molecule, comment)
    for start in range(0, len(grid.values), 6):
        yield " ".join(f"{value:13.5E}" for value in grid.values[start : start + 6])


def _cube_header(origin_bohr, axes_bohr, shape, value_unit, molecule, comment):
    yield "openWFN scalar field"
    yield comment if comment is not None else f"units: {value_unit}"
    yield (
        f"{len(molecule.atoms):5d} {origin_bohr[0]:13.6f} {origin_bohr[1]:13.6f} {origin_bohr[2]:13.6f}"
    )
    for count, axis_bohr in zip(shape, axes_bohr):
        yield (
            f"{count:5d} {axis_bohr[0]:13.6f} {axis_bohr[1]:13.6f} {axis_bohr[2]:13.6f}"
        )
    for atom in molecule.atoms:
        x, y, z = (value / BOHR_TO_ANGSTROM for value in atom.coordinates)
        nuclear_charge = effective_nuclear_charge(atom)
        yield (
            f"{atom.atomic_number:5d} {nuclear_charge:13.6f} {x:13.6f} {y:13.6f} {z:13.6f}"
        )
