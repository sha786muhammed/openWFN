from pathlib import Path

import openwfn
from openwfn.batch import _run_one
from openwfn.results import ResultRecord

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "scientific"
WATER = ROOT / "examples" / "water" / "water.fchk"


def test_python_api_preserves_analysis_warning_when_attaching_provenance() -> None:
    calculation = openwfn.load(FIXTURES / "uhf_beta_homo.fchk")

    result = calculation.orbitals("alpha")

    assert any(
        "beta" in warning.lower() and "complete" in warning.lower()
        for warning in result.warnings
    )
    assert result.provenance["input_sha256"] == calculation.molecule.provenance.sha256


def test_batch_all_partial_results_remain_partial_and_keep_usable_data(monkeypatch) -> None:
    partial = ResultRecord(
        kind="summary",
        data={"diagnostic": 42},
        status="partial",
        validation_status="Experimental",
        warnings=("scientific consistency warning",),
    )

    monkeypatch.setattr("openwfn.batch.run_analysis_safe", lambda _data, _name: partial)

    record = _run_one((WATER, ("summary",)))

    assert record.status == "partial"
    assert record.result == {"diagnostic": 42}
    assert record.error is None
    assert record.results == (partial,)
