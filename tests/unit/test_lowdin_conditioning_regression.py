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


def test_rank_deficient_lowdin_overlap_is_partial_and_diagnostic() -> None:
    molecule = Molecule(
        (Atom(1, (0.0, 0.0, 0.0), nuclear_charge=1.0),),
        0,
        2,
        CalculationMetadata("fixture"),
    )
    # Two identical normalized s shells on the same center make S rank deficient.
    basis = BasisSet(
        (
            BasisShell(0, 0, (1.0,), (1.0,)),
            BasisShell(0, 0, (1.0,), (1.0,)),
        )
    )
    data = CalculationData(
        molecule=molecule,
        basis=basis,
        total_density=DensityMatrix(
            ((0.5, 0.0), (0.0, 0.5)), "total", source="scf"
        ),
    )

    result = population_analysis(data, "lowdin")

    assert result.data["overlap_min_eigenvalue"] <= 1e-10
    assert result.data["overlap_rank_deficient"] is True
    assert result.status == "partial"
    assert result.validation_status == "Experimental"
    assert any("overlap" in warning.lower() for warning in result.warnings)
