import numpy as np

from openwfn.analysis.population import mulliken_population
from openwfn.model import (
    Atom,
    BasisSet,
    BasisShell,
    CalculationData,
    CalculationMetadata,
    DensityMatrix,
    Molecule,
)
from openwfn.services import population_analysis


def test_mulliken_uses_effective_nuclear_charge_for_ecp_center() -> None:
    molecule = Molecule(
        (Atom(14, (0.0, 0.0, 0.0), nuclear_charge=4.0),),
        0,
        1,
        CalculationMetadata("fixture"),
    )
    density = DensityMatrix(((4.0,),), "total")

    result = mulliken_population(molecule, density, np.eye(1), (0,))

    assert result.electron_populations == (4.0,)
    assert result.atomic_charges == (0.0,)
    assert result.total_charge == 0.0
    assert result.conservation_error == 0.0


def test_mulliken_assigns_zero_nuclear_charge_to_ghost_center() -> None:
    molecule = Molecule(
        (Atom(8, (0.0, 0.0, 0.0), nuclear_charge=0.0),),
        0,
        1,
        CalculationMetadata("fixture"),
    )
    density = DensityMatrix(((0.0,),), "total")

    result = mulliken_population(molecule, density, np.eye(1), (0,))

    assert result.atomic_charges == (0.0,)
    assert result.total_charge == 0.0


def test_population_conservation_failure_is_partial_and_warned() -> None:
    molecule = Molecule(
        (Atom(1, (0.0, 0.0, 0.0), nuclear_charge=1.0),),
        0,
        2,
        CalculationMetadata("fixture"),
    )
    data = CalculationData(
        molecule=molecule,
        basis=BasisSet((BasisShell(0, 0, (1.0,), (1.0,)),)),
        total_density=DensityMatrix(((0.5,),), "total", source="scf"),
    )

    result = population_analysis(data, "mulliken")

    assert result.data["conservation_error"] > 1e-6
    assert result.status == "partial"
    assert result.validation_status == "Experimental"
    assert any("conservation" in warning.lower() for warning in result.warnings)


def test_post_hf_population_identifies_scf_density_source() -> None:
    molecule = Molecule(
        (Atom(1, (0.0, 0.0, 0.0), nuclear_charge=1.0),),
        0,
        2,
        CalculationMetadata("Gaussian", method="MP2"),
    )
    data = CalculationData(
        molecule=molecule,
        basis=BasisSet((BasisShell(0, 0, (1.0,), (1.0,)),)),
        total_density=DensityMatrix(((1.0,),), "total", source="scf"),
    )

    result = population_analysis(data, "mulliken")

    assert result.data["density_source"] == "scf"
    assert any("SCF density" in warning for warning in result.warnings)
