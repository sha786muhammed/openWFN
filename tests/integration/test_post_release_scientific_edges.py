from pathlib import Path

import numpy as np
import pytest

import openwfn
from openwfn.analysis.density import density_matrix_for_kind
from openwfn.model import Atom, CalculationData, CalculationMetadata, MolecularOrbitals, Molecule
from openwfn.services import density_cube_export, orbital_frontier

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / "examples" / "water" / "water.fchk"


@pytest.mark.parametrize("method", ["UMP2-FC", "UMP3-FC", "UCISD-FC"])
def test_real_style_post_hf_method_names_warn_when_scf_density_is_used(
    tmp_path: Path, method: str
) -> None:
    source = WATER.read_text(encoding="utf-8")
    lines = source.splitlines()
    lines[1] = f"FOpt      {method:<60}3-21G"
    fixture = tmp_path / f"water-{method}.fchk"
    fixture.write_text("\n".join(lines) + "\n", encoding="utf-8")

    calculation = openwfn.load(fixture)
    result = calculation.population("mulliken")

    assert calculation.molecule.metadata.method == method
    assert result.data["density_source"] == "scf"
    warning = " ".join(result.warnings).lower()
    assert "scf density" in warning
    assert "post-scf" in warning


def test_restricted_closed_shell_derives_alpha_beta_and_zero_spin_density() -> None:
    calculation = openwfn.load(WATER).data
    assert calculation.total_density is not None
    assert calculation.spin_density is None

    total = np.asarray(calculation.total_density.values)
    alpha = density_matrix_for_kind(calculation, "alpha")
    beta = density_matrix_for_kind(calculation, "beta")
    spin = density_matrix_for_kind(calculation, "spin")

    assert alpha.source == "scf"
    assert beta.source == "scf"
    assert spin.source == "scf"
    np.testing.assert_allclose(alpha.values, 0.5 * total, atol=1e-14)
    np.testing.assert_allclose(beta.values, 0.5 * total, atol=1e-14)
    np.testing.assert_allclose(spin.values, np.zeros_like(total), atol=1e-14)


def test_restricted_closed_shell_zero_spin_integrates_and_exports_cube(tmp_path: Path) -> None:
    calculation = openwfn.load(WATER)

    result = calculation.density("spin", spacing_bohr=0.25, padding_bohr=5.0)
    cube_path = tmp_path / "spin.cube"
    cube = density_cube_export(
        calculation.data,
        "spin",
        0.25,
        5.0,
        cube_path,
        False,
    )

    assert result.status == "success"
    assert result.data["expected_electrons"] == pytest.approx(0.0)
    assert result.data["electron_count"] == pytest.approx(0.0, abs=1e-10)
    assert result.data["error_metric"] == "absolute"
    assert cube.status == "success"
    assert cube_path.is_file()
    assert cube_path.stat().st_size > 0


def _one_electron_uhf() -> CalculationData:
    molecule = Molecule(
        atoms=(Atom(1, (0.0, 0.0, 0.0), nuclear_charge=1.0),),
        charge=0,
        multiplicity=2,
        metadata=CalculationMetadata(source_program="Gaussian", method="UHF", basis="STO-3G"),
    )
    alpha = MolecularOrbitals(
        energies=(-0.46658185,),
        coefficients=((1.0,),),
        occupations=(1.0,),
        spin="alpha",
        occupation_source="electron-count filling",
    )
    beta = MolecularOrbitals(
        energies=(0.308024094,),
        coefficients=((1.0,),),
        occupations=(0.0,),
        spin="beta",
        occupation_source="electron-count filling",
    )
    return CalculationData(
        molecule=molecule,
        alpha_orbitals=alpha,
        beta_orbitals=beta,
        records={
            "Number of electrons": 1,
            "Number of alpha electrons": 1,
            "Number of beta electrons": 0,
        },
    )


def test_one_electron_frontier_preserves_available_alpha_homo_without_lumo() -> None:
    result = orbital_frontier(_one_electron_uhf(), "alpha")

    assert result.status == "partial"
    assert result.data["homo_number"] == 1
    assert result.data["homo_hartree"] == pytest.approx(-0.46658185)
    assert result.data["lumo_number"] is None
    assert result.data["lumo_hartree"] is None
    assert result.data["gap_hartree"] is None
    assert any("lumo" in warning.lower() for warning in result.warnings)


def test_empty_beta_channel_reports_lumo_without_inventing_homo() -> None:
    result = orbital_frontier(_one_electron_uhf(), "beta")

    assert result.status == "partial"
    assert result.data["homo_number"] is None
    assert result.data["homo_hartree"] is None
    assert result.data["lumo_number"] == 1
    assert result.data["lumo_hartree"] == pytest.approx(0.308024094)
    assert result.data["gap_hartree"] is None
    assert any("homo" in warning.lower() for warning in result.warnings)


def test_one_electron_all_spin_frontier_keeps_overall_homo() -> None:
    result = orbital_frontier(_one_electron_uhf(), "all")

    assert result.status == "partial"
    assert result.data["alpha"]["homo_number"] == 1
    assert result.data["alpha"]["lumo_number"] is None
    assert result.data["beta"]["homo_number"] is None
    assert result.data["beta"]["lumo_number"] == 1
    assert result.data["overall_homo_number"] == 1
    assert result.data["overall_homo_hartree"] == pytest.approx(-0.46658185)
    assert result.data["overall_homo_spin"] == "alpha"
