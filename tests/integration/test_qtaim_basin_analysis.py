from openwfn.analysis.registry import available_analyses, run_analysis_safe
from openwfn.ingest import load_input


def test_registry_exposes_qtaim_basins_with_existing_capability_requirements() -> None:
    assert "qtaim-basins" in available_analyses()


def test_qtaim_basins_registry_safe_failure_keeps_expected_result_kind() -> None:
    data = load_input("examples/water/water.fchk")
    result = run_analysis_safe(data, "qtaim-basins")

    assert result.kind == "qtaim_basins"
    assert result.analysis_name == "qtaim-basins"
