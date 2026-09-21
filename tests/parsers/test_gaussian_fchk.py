from pathlib import Path

import pytest

from openwfn.errors import ParseError
from openwfn.parsers.gaussian.fchk import FCHKDocument, parse_fchk


def test_document_reads_scalar_numeric_and_character_records() -> None:
    document = FCHKDocument.from_lines(
        [
            "Charge I 0\n",
            "SCF Energy R -7.558595974892307D+01\n",
            "Labels C N= 2\n",
            "first       second      \n",
        ]
    )

    assert document.scalar("Charge") == 0
    assert document.scalar("SCF Energy") == pytest.approx(-75.58595974892307)
    assert document.array("Labels") == ("first", "second")


def test_document_preserves_blank_fixed_width_character_values() -> None:
    document = FCHKDocument.from_lines(
        ["Atom Types C N= 3\n", "                                    \n"]
    )

    assert document.array("Atom Types") == ("", "", "")


def test_document_reads_compact_blank_character_array_line() -> None:
    document = FCHKDocument.from_lines(["Atom Types C N= 3\n", "\n"])

    assert document.array("Atom Types") == ("", "", "")


def test_document_rejects_truncated_array_with_record_and_line() -> None:
    with pytest.raises(ParseError, match=r"Atomic numbers.*line 1.*expected 3.*found 2"):
        FCHKDocument.from_lines(["Atomic numbers I N= 3\n", "8 1\n"])


def test_document_rejects_invalid_numeric_token() -> None:
    with pytest.raises(ParseError, match=r"Atomic numbers.*not-an-integer"):
        FCHKDocument.from_lines(["Atomic numbers I N= 2\n", "8 not-an-integer\n"])


def test_document_reads_adjacent_signed_real_values_from_fixed_width_writer() -> None:
    document = FCHKDocument.from_lines(
        [
            "Current cartesian coordinates R N= 2\n",
            " 1.13086932e+00-3.46281773e-118\n",
        ]
    )

    assert document.array("Current cartesian coordinates") == pytest.approx(
        (1.13086932, -3.46281773e-118)
    )


def test_parse_fchk_returns_typed_molecule_with_provenance(tmp_path: Path) -> None:
    source = tmp_path / "water.fchk"
    source.write_text(
        "Water\n"
        "FOpt RHF 3-21G\n"
        "Number of atoms I 3\n"
        "Charge I 0\n"
        "Multiplicity I 1\n"
        "Atomic numbers I N= 3\n"
        "8 1 1\n"
        "Current cartesian coordinates R N= 9\n"
        "0.0 0.0 0.0 0.0 1.0 0.0 0.0 -1.0 0.0\n",
        encoding="utf-8",
    )

    data = parse_fchk(source)

    assert tuple(atom.atomic_number for atom in data.molecule.atoms) == (8, 1, 1)
    assert data.molecule.atoms[1].coordinates[1] == pytest.approx(0.529177210903)
    assert data.molecule.provenance is not None
    assert data.molecule.provenance.source_path == str(source)
    assert len(data.molecule.provenance.sha256) == 64
    assert data.molecule.provenance.source_format == "fchk"
    assert data.molecule.provenance.parser_version == "1"
    assert data.molecule.boundary_conditions.kind == "isolated"


def test_parse_fchk_derives_atom_count_when_redundant_scalar_is_absent(
    tmp_path: Path,
) -> None:
    source = tmp_path / "minimal.fchk"
    source.write_text(
        "Minimal\n"
        "SP RHF STO-3G\n"
        "Charge I 0\n"
        "Multiplicity I 1\n"
        "Atomic numbers I N= 2\n"
        "1 1\n"
        "Current cartesian coordinates R N= 6\n"
        "0.0 0.0 0.0 1.4 0.0 0.0\n",
        encoding="utf-8",
    )

    data = parse_fchk(source)

    assert tuple(atom.atomic_number for atom in data.molecule.atoms) == (1, 1)


def test_parse_fchk_does_not_parse_header_text_as_a_record(tmp_path: Path) -> None:
    source = tmp_path / "qchem.fchk"
    source.write_text(
        "Jobname.Temp\n"
        "SP        R                             STO-3G\n"
        "Number of atoms I 1\n"
        "Charge I 0\n"
        "Multiplicity I 1\n"
        "Atomic numbers I N= 1\n"
        "1\n"
        "Current cartesian coordinates R N= 3\n"
        "0.0 0.0 0.0\n",
        encoding="utf-8",
    )

    data = parse_fchk(source)

    assert data.molecule.atoms[0].atomic_number == 1


def test_parse_fchk_rejects_atom_coordinate_count_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "broken.fchk"
    source.write_text(
        "Broken\n"
        "FOpt RHF STO-3G\n"
        "Number of atoms I 2\n"
        "Charge I 0\n"
        "Multiplicity I 1\n"
        "Atomic numbers I N= 1\n"
        "8\n"
        "Current cartesian coordinates R N= 3\n"
        "0.0 0.0 0.0\n",
        encoding="utf-8",
    )

    with pytest.raises(ParseError, match="Number of atoms"):
        parse_fchk(source)


def test_parse_fchk_builds_ordered_basis_set_from_real_fixture() -> None:
    source = Path(__file__).resolve().parents[2] / "examples" / "water" / "water.fchk"

    data = parse_fchk(source)

    assert data.basis is not None
    assert len(data.basis.shells) == 7
    assert data.basis.n_functions == 13
    assert data.alpha_orbitals is not None
    assert len(data.alpha_orbitals.energies) == 13
    assert len(data.alpha_orbitals.coefficients) == 13
    assert len(data.alpha_orbitals.coefficients[0]) == 13
    assert data.alpha_orbitals.occupations[:6] == (2.0, 2.0, 2.0, 2.0, 2.0, 0.0)
    assert data.total_density is not None
    assert len(data.total_density.values) == 13
    assert data.total_density.values[0][1] == data.total_density.values[1][0]


def test_parse_fchk_accepts_windows_crlf_line_endings(tmp_path: Path) -> None:
    fixture = Path(__file__).resolve().parents[2] / "examples" / "water" / "water.fchk"
    source = tmp_path / "water-crlf.fchk"
    source.write_bytes(fixture.read_bytes().replace(b"\n", b"\r\n"))

    data = parse_fchk(source)

    assert tuple(atom.atomic_number for atom in data.molecule.atoms) == (8, 1, 1)
    assert data.alpha_orbitals is not None
