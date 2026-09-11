from pathlib import Path

import numpy as np
import pytest

from openwfn.errors import ParseError
from openwfn.exporters.cube import write_cube
from openwfn.model import Atom, CalculationMetadata, Molecule, VolumetricGrid
from openwfn.parsers.gaussian.cube import parse_cube


def _cube(values: str, atom_count: int = 1, orbital_line: str = "") -> str:
    return (
        "density\n"
        "generated fixture\n"
        f"{atom_count} 0.0 0.0 0.0\n"
        "2 0.5 0.0 0.0\n"
        "2 0.0 0.5 0.0\n"
        "2 0.0 0.0 0.5\n"
        "8 0.0 0.0 0.0 0.0\n"
        f"{orbital_line}"
        f"{values}\n"
    )


def test_cube_parser_validates_shape_and_converts_axes(tmp_path: Path) -> None:
    source = tmp_path / "density.cube"
    source.write_text(_cube("0 1 2 3 4 5 6 7"), encoding="utf-8")

    grid = parse_cube(source)

    assert grid.shape == (2, 2, 2)
    assert grid.axes[0][0] == pytest.approx(0.2645886054515)
    assert grid.values == tuple(float(value) for value in range(8))


def test_cube_parser_reads_negative_atom_orbital_header(tmp_path: Path) -> None:
    source = tmp_path / "orbital.cube"
    source.write_text(_cube("0 1 2 3 4 5 6 7", atom_count=-1, orbital_line="1 5\n"), encoding="utf-8")

    grid = parse_cube(source)

    assert grid.shape == (2, 2, 2)


def test_cube_parser_rejects_wrong_voxel_count(tmp_path: Path) -> None:
    source = tmp_path / "broken.cube"
    source.write_text(_cube("0 1"), encoding="utf-8")

    with pytest.raises(ParseError, match="expected 8 voxel values but found 2"):
        parse_cube(source)


def test_cube_round_trip_preserves_grid_geometry_and_values(tmp_path: Path) -> None:
    molecule = Molecule(
        (Atom(1, (0.0, 0.0, 0.0)),), 0, 2, CalculationMetadata("fixture")
    )
    grid = VolumetricGrid(
        origin=(-0.5, -0.5, -0.5),
        axes=((0.5, 0.0, 0.0), (0.0, 0.5, 0.0), (0.0, 0.0, 0.5)),
        shape=(2, 2, 2),
        values=tuple(value / 10.0 for value in range(8)),
        value_unit="orbital_amplitude",
    )
    output = tmp_path / "orbital.cube"

    write_cube(grid, molecule, output)
    restored = parse_cube(output)

    assert restored.origin == pytest.approx(grid.origin)
    assert np.asarray(restored.axes) == pytest.approx(np.asarray(grid.axes))
    assert restored.values == pytest.approx(grid.values)
