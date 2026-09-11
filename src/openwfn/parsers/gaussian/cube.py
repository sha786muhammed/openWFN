"""Gaussian cube volumetric-grid parser."""

from math import prod
from pathlib import Path

from ...constants import BOHR_TO_ANGSTROM
from ...errors import ParseError
from ...model import VolumetricGrid


def _numbers(line: str, count: int, context: str) -> list[float]:
    fields = line.split()
    if len(fields) < count:
        raise ParseError(f"Malformed cube {context}: expected at least {count} fields.")
    try:
        return [float(field.replace("D", "E").replace("d", "e")) for field in fields[:count]]
    except ValueError as exc:
        raise ParseError(f"Malformed numeric value in cube {context}.") from exc


def parse_cube(path: Path) -> VolumetricGrid:
    """Parse a Gaussian cube file into a regular typed grid."""

    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 6:
        raise ParseError("Malformed cube file: the six-line header is incomplete.")

    origin_record = _numbers(lines[2], 4, "origin record")
    signed_atom_count = int(origin_record[0])
    atom_count = abs(signed_atom_count)
    shape: list[int] = []
    raw_axes: list[tuple[float, float, float]] = []
    signed_axis_counts: list[int] = []
    for offset in range(3):
        axis_record = _numbers(lines[3 + offset], 4, "axis record")
        signed_axis_count = int(axis_record[0])
        axis_count = abs(signed_axis_count)
        if axis_count < 1:
            raise ParseError("Malformed cube axis record: grid dimensions must be positive.")
        shape.append(axis_count)
        signed_axis_counts.append(signed_axis_count)
        raw_axes.append(tuple(axis_record[1:4]))  # type: ignore[arg-type]

    if all(count > 0 for count in signed_axis_counts):
        coordinate_factor = BOHR_TO_ANGSTROM
    elif all(count < 0 for count in signed_axis_counts):
        coordinate_factor = 1.0
    else:
        raise ParseError("Malformed cube axis records: coordinate-unit signs are inconsistent.")
    origin = tuple(value * coordinate_factor for value in origin_record[1:4])
    axes = [tuple(value * coordinate_factor for value in axis) for axis in raw_axes]

    data_start = 6 + atom_count
    if len(lines) < data_start:
        raise ParseError("Malformed cube file: atom records are truncated.")
    if signed_atom_count < 0:
        if len(lines) <= data_start:
            raise ParseError("Malformed orbital cube: orbital identifier record is missing.")
        orbital_header = lines[data_start].split()
        if not orbital_header:
            raise ParseError("Malformed orbital cube: orbital identifier record is empty.")
        try:
            orbital_count = int(orbital_header[0])
        except ValueError as exc:
            raise ParseError("Malformed orbital cube identifier count.") from exc
        if len(orbital_header[1:]) != orbital_count:
            raise ParseError("Malformed orbital cube: orbital identifier count does not match.")
        data_start += 1

    tokens = " ".join(lines[data_start:]).split()
    try:
        values = tuple(float(token.replace("D", "E").replace("d", "e")) for token in tokens)
    except ValueError as exc:
        raise ParseError("Malformed numeric voxel value in cube file.") from exc
    expected = prod(shape)
    if len(values) != expected:
        raise ParseError(
            f"Malformed cube grid: expected {expected} voxel values but found {len(values)}."
        )

    return VolumetricGrid(
        origin=origin,  # type: ignore[arg-type]
        axes=tuple(axes),  # type: ignore[arg-type]
        shape=tuple(shape),  # type: ignore[arg-type]
        values=values,
        value_unit="atomic_unit",
    )
