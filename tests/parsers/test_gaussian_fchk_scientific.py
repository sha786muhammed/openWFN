from pathlib import Path

from openwfn.parsers.gaussian.fchk import parse_fchk

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "scientific"


def test_parse_fchk_preserves_ecp_nuclear_charge() -> None:
    data = parse_fchk(FIXTURES / "ecp_minimal.fchk")

    assert data.molecule.atoms[0].atomic_number == 14
    assert data.molecule.atoms[0].nuclear_charge == 4.0


def test_parse_fchk_preserves_zero_charge_for_ghost_center() -> None:
    data = parse_fchk(FIXTURES / "ghost_minimal.fchk")

    assert data.molecule.atoms[1].atomic_number == 8
    assert data.molecule.atoms[1].nuclear_charge == 0.0


def test_parse_fchk_tags_scf_density_source() -> None:
    data = parse_fchk(FIXTURES / "post_hf_scf_density.fchk")

    assert data.total_density is not None
    assert data.total_density.source == "scf"
    assert data.spin_density is not None
    assert data.spin_density.source == "scf"


def test_parse_fchk_warns_when_nuclear_charges_are_missing(tmp_path: Path) -> None:
    source = tmp_path / "missing-nuclear-charges.fchk"
    source.write_text(
        "Minimal\n"
        "SP RHF STO-3G\n"
        "Number of atoms I 1\n"
        "Charge I 0\n"
        "Multiplicity I 2\n"
        "Number of electrons I 1\n"
        "Number of alpha electrons I 1\n"
        "Number of beta electrons I 0\n"
        "Atomic numbers I N= 1\n"
        "1\n"
        "Current cartesian coordinates R N= 3\n"
        "0.0 0.0 0.0\n",
        encoding="utf-8",
    )

    data = parse_fchk(source)

    assert data.molecule.atoms[0].nuclear_charge is None
    assert data.molecule.provenance is not None
    assert any("Nuclear charges" in warning for warning in data.molecule.provenance.warnings)
