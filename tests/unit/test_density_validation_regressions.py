from pathlib import Path

from openwfn.analysis.density import integrate_density
from openwfn.constants import BOHR_TO_ANGSTROM
from openwfn.model import (
    Atom,
    BasisSet,
    BasisShell,
    CalculationData,
    CalculationMetadata,
    DensityMatrix,
    Molecule,
    VolumetricGrid,
)
from openwfn.services import density_cube_export, density_integration


def _one_s_basis() -> BasisSet:
    return BasisSet((BasisShell(0, 0, (1.0,), (1.0,)),))


def test_zero_target_density_uses_absolute_error_and_can_pass() -> None:
    step = BOHR_TO_ANGSTROM
    grid = VolumetricGrid(
        origin=(0.0, 0.0, 0.0),
        axes=((step, 0.0, 0.0), (0.0, step, 0.0), (0.0, 0.0, step)),
        shape=(1, 1, 1),
        values=(0.0,),
        value_unit="electron/bohr^3",
    )

    result = integrate_density(grid, expected_electrons=0.0)

    assert result.electron_count == 0.0
    assert result.absolute_error == 0.0
    assert result.relative_error is None
    assert result.error_metric == "absolute"
    assert result.passed is True


def test_spin_density_with_zero_expected_integral_is_valid() -> None:
    molecule = Molecule(
        (Atom(2, (0.0, 0.0, 0.0), nuclear_charge=2.0),),
        0,
        1,
        CalculationMetadata("fixture"),
    )
    data = CalculationData(
        molecule=molecule,
        basis=_one_s_basis(),
        total_density=DensityMatrix(((2.0,),), "total", source="scf"),
        spin_density=DensityMatrix(((0.0,),), "spin", source="scf"),
        records={
            "Number of electrons": 2,
            "Number of alpha electrons": 1,
            "Number of beta electrons": 1,
        },
    )

    result = density_integration(data, "spin", spacing_bohr=1.0, padding_bohr=2.0)

    assert result.data["expected_electrons"] == 0.0
    assert result.data["error_metric"] == "absolute"
    assert result.status == "success"


def test_density_uses_fchk_total_electron_count_for_ecp_system() -> None:
    molecule = Molecule(
        (Atom(14, (0.0, 0.0, 0.0), nuclear_charge=4.0),),
        0,
        1,
        CalculationMetadata("fixture"),
    )
    data = CalculationData(
        molecule=molecule,
        basis=_one_s_basis(),
        total_density=DensityMatrix(((4.0,),), "total", source="scf"),
        records={"Number of electrons": 4},
    )

    result = density_integration(data, "total", spacing_bohr=0.6, padding_bohr=4.0)

    assert result.data["expected_electrons"] == 4.0
    assert result.data["expectation_source"] == "Number of electrons"


def test_coarse_cube_is_written_but_not_claimed_validated(tmp_path: Path) -> None:
    molecule = Molecule(
        (Atom(1, (0.0, 0.0, 0.0), nuclear_charge=1.0),),
        0,
        2,
        CalculationMetadata("fixture"),
    )
    data = CalculationData(
        molecule=molecule,
        basis=_one_s_basis(),
        total_density=DensityMatrix(((1.0,),), "total", source="scf"),
        records={"Number of electrons": 1},
    )
    output = tmp_path / "coarse.cube"

    result = density_cube_export(
        data,
        "total",
        spacing_bohr=3.0,
        padding_bohr=1.0,
        output_path=output,
        overwrite=False,
    )

    assert output.exists()
    assert result.status == "partial"
    assert result.validation_status == "Experimental"
    assert result.data["expected_electrons"] == 1.0
    assert result.data["absolute_error"] > 0.005
    assert any("conservation" in warning.lower() for warning in result.warnings)


def test_post_hf_density_result_names_scf_source_and_warns() -> None:
    molecule = Molecule(
        (Atom(1, (0.0, 0.0, 0.0), nuclear_charge=1.0),),
        0,
        2,
        CalculationMetadata("Gaussian", method="MP2"),
    )
    data = CalculationData(
        molecule=molecule,
        basis=_one_s_basis(),
        total_density=DensityMatrix(((1.0,),), "total", source="scf"),
        records={"Number of electrons": 1},
    )

    result = density_integration(data, "total", spacing_bohr=0.6, padding_bohr=4.0)

    assert result.data["density_source"] == "scf"
    assert any("SCF density" in warning for warning in result.warnings)
