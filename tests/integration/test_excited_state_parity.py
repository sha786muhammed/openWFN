from pathlib import Path

import openwfn
from openwfn.analysis.registry import run_analysis

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/gaussian/excited/tddft_states.log"


def _assert_scientific_parity(left, right) -> None:
    assert left.analysis_name == right.analysis_name
    assert left.analysis_version == right.analysis_version
    assert left.kind == right.kind
    assert left.data == right.data
    assert left.units == right.units
    assert left.validation_status == right.validation_status
    assert left.status == right.status
    assert left.warnings == right.warnings
    assert left.provenance == right.provenance


def test_python_high_level_api_matches_registry_for_excited_states() -> None:
    calculation = openwfn.load(FIXTURE)
    assert calculation.data.calculation is not None

    for name, parameters in (
        ("excited-states", {}),
        ("excited-state", {"state": 1}),
        ("transition-dipoles", {}),
        ("uvvis-spectrum", {"fwhm_ev": 0.15, "points": 301}),
    ):
        high_level = calculation.analyze(name, **parameters)
        registry = run_analysis(calculation.data, name, **parameters)
        _assert_scientific_parity(high_level, registry)
