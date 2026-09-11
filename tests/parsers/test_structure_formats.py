from dataclasses import replace
from hashlib import sha256
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


def test_registry_dispatches_gaussian_cube_and_output_files(tmp_path: Path) -> None:
    cube = tmp_path / "density.cube"
    cube.write_text(
        "density\nfixture\n0 0 0 0\n1 1 0 0\n1 0 1 0\n1 0 0 1\n0.5\n",
        encoding="utf-8",
    )
    output = tmp_path / "job.log"
    output.write_text(
        "# RHF/3-21G\nSCF Done: E(RHF) = -7.5\nNormal termination of Gaussian\n",
        encoding="utf-8",
    )

    assert load(cube).shape == (1, 1, 1)
    assert load(output).energy_hartree == pytest.approx(-7.5)


def test_registry_converts_binary_checkpoint_before_parsing(monkeypatch, tmp_path: Path) -> None:
    checkpoint = tmp_path / "water.chk"
    checkpoint.write_bytes(b"binary")
    formatted = tmp_path / "water.fchk"
    formatted.write_text(
        "Water\nFOpt RHF STO-3G\nNumber of atoms I 1\nCharge I 0\n"
        "Multiplicity I 1\nAtomic numbers I N= 1\n8\n"
        "Current cartesian coordinates R N= 3\n0 0 0\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "openwfn.parsers.registry.resolve_checkpoint", lambda _path: formatted
    )

    assert load(checkpoint).molecule.atoms[0].atomic_number == 8


def test_registry_detects_xyz_content_when_suffix_is_unknown(tmp_path: Path) -> None:
    source = tmp_path / "water.dat"
    source.write_text("1\nwater\nO 0 0 0\n", encoding="utf-8")

    data = load(source)

    assert len(data.molecule.atoms) == 1
    assert data.molecule.atoms[0].atomic_number == 8


def test_sdf_provenance_hash_identifies_original_file_bytes(tmp_path: Path) -> None:
    source = tmp_path / "water.sdf"
    source.write_text(
        "water\nopenWFN\n\n  1  0  0  0  0  0            999 V2000\n"
        "    0.0000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n"
        "M  END\n$$$$\n",
        encoding="utf-8",
    )

    data = load(source)

    assert data.molecule.provenance is not None
    assert data.molecule.provenance.sha256 == sha256(source.read_bytes()).hexdigest()


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
