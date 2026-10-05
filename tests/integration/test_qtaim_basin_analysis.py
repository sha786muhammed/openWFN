from openwfn.analysis.registry import available_analyses, run_analysis_safe
from openwfn.model import Atom, CalculationData, CalculationMetadata, Molecule


def test_registry_exposes_qtaim_basins_with_existing_capability_requirements() -> None:
    assert "qtaim-basins" in available_analyses()


def test_qtaim_basins_registry_safe_failure_keeps_expected_result_kind() -> None:
    data = CalculationData(
        molecule=Molecule(
            (Atom(1, (0.0, 0.0, 0.0)),),
            0,
            1,
            CalculationMetadata("fixture"),
        )
    )
    result = run_analysis_safe(data, "qtaim-basins")

    assert result.kind == "qtaim_basins"
    assert result.analysis_name == "qtaim-basins"
