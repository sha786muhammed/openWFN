from pathlib import Path

import openwfn
from openwfn.analysis.registry import run_analysis

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/gaussian/vibrations/water_freq.log"


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


def test_python_high_level_api_matches_registry_for_spectroscopy() -> None:
    calculation = openwfn.load(FIXTURE)
    assert calculation.data.calculation is not None

    for name, parameters in (
        ("vibrations", {}),
        ("ir-spectrum", {"fwhm_cm1": 12.0, "points": 321}),
        ("raman-spectrum", {"fwhm_cm1": 18.0, "points": 257}),
        ("normal-mode", {"mode": 2}),
    ):
        high_level = calculation.analyze(name, **parameters)
        registry = run_analysis(calculation.data.calculation, name, **parameters)
        _assert_scientific_parity(high_level, registry)
