from dataclasses import replace
from pathlib import Path

import pytest

from openwfn.errors import ParseError
from openwfn.exporters.structures import write_structure
from openwfn.model import Bond
from openwfn.parsers.registry import load


def test_xyz_round_trip_preserves_elements_and_coordinates(tmp_path: Path) -> None:
    source = tmp_path / "water.xyz"
    source.write_text(
        "3\nwater\nO 0.0 0.0 0.1\nH 0.0 0.8 -0.4\nH 0.0 -0.8 -0.4\n",
        encoding="utf-8",
    )
    data = load(source)
    output = tmp_path / "roundtrip.xyz"

    write_structure(data.molecule, output, format="xyz")
    restored = load(output)

    assert tuple(atom.atomic_number for atom in restored.molecule.atoms) == (8, 1, 1)
    assert tuple(atom.coordinates for atom in restored.molecule.atoms) == (
        (0.0, 0.0, 0.1),
        (0.0, 0.8, -0.4),
        (0.0, -0.8, -0.4),
    )


def test_registry_reports_unsupported_format(tmp_path: Path) -> None:
    source = tmp_path / "water.unknown"
    source.write_text("data", encoding="utf-8")

    with pytest.raises(ParseError, match="Unsupported input format '.unknown'"):
        load(source)


def test_registry_detects_xyz_content_when_suffix_is_unknown(tmp_path: Path) -> None:
    source = tmp_path / "water.dat"
    source.write_text("1\nwater\nO 0 0 0\n", encoding="utf-8")

    data = load(source)

    assert len(data.molecule.atoms) == 1
    assert data.molecule.atoms[0].atomic_number == 8


def test_structure_writer_protects_existing_output(tmp_path: Path) -> None:
    source = tmp_path / "water.xyz"
    source.write_text("1\nwater\nO 0 0 0\n", encoding="utf-8")
    data = load(source)

    with pytest.raises(FileExistsError, match="overwrite"):
        write_structure(data.molecule, source, format="xyz")


@pytest.mark.parametrize("format", ["pdb", "mol", "sdf"])
def test_bonded_structure_round_trip_preserves_atoms_coordinates_and_bonds(
    tmp_path: Path, format: str
) -> None:
    source = tmp_path / "water.xyz"
    source.write_text(
        "3\nwater\nO 0.0 0.0 0.1\nH 0.0 0.8 -0.4\nH 0.0 -0.8 -0.4\n",
        encoding="utf-8",
    )
    data = load(source)
    molecule = replace(data.molecule, bonds=(Bond(0, 1), Bond(0, 2)))
    output = tmp_path / f"water.{format}"

    write_structure(molecule, output, format=format)
    restored = load(output).molecule

    assert tuple(atom.atomic_number for atom in restored.atoms) == (8, 1, 1)
    assert restored.atoms[0].coordinates == pytest.approx((0.0, 0.0, 0.1), abs=1e-4)
    assert restored.bonds == (Bond(0, 1), Bond(0, 2))
