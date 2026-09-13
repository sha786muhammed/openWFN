from pathlib import Path

import pytest

from openwfn.analysis.registry import available_analyses, run_analysis, run_analysis_safe
from openwfn.parsers.gaussian.fchk import parse_fchk

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / "examples" / "water" / "water.fchk"


def test_registry_runs_summary_with_versioned_input_provenance() -> None:
    data = parse_fchk(WATER)

    result = run_analysis(data, "summary")

    assert available_analyses() == (
        "beta-frontier",
        "frontier",
        "lowdin",
        "mulliken",
        "summary",
    )
    assert result.analysis_name == "summary"
    assert result.analysis_version == "1"
    assert result.status == "success"
    assert result.elapsed_seconds is not None and result.elapsed_seconds >= 0
    assert result.provenance == {
        "input_sha256": data.molecule.provenance.sha256,
        "model_schema_version": "2.0",
        "parser": "gaussian-fchk",
        "parser_version": "1",
        "source_format": "fchk",
        "source_path": str(WATER),
        "source_program": "Gaussian",
        "source_program_version": None,
        "transformations": [],
    }


def test_registry_rejects_unknown_analysis_with_available_names() -> None:
    data = parse_fchk(WATER)

    with pytest.raises(ValueError, match="Unknown analysis 'missing'.*summary"):
        run_analysis(data, "missing")


def test_safe_registry_run_returns_structured_unavailable_result() -> None:
    data = parse_fchk(WATER)

    result = run_analysis_safe(data, "beta-frontier")

    assert result.analysis_name == "beta-frontier"
    assert result.status == "failed"
    assert result.error is not None
    assert result.error.category == "DataUnavailableError"
    assert "Beta orbitals are not available" in result.error.message
    assert result.elapsed_seconds is not None and result.elapsed_seconds >= 0


def test_safe_registry_run_captures_an_unknown_analysis_name() -> None:
    data = parse_fchk(WATER)

    result = run_analysis_safe(data, "missing")

    assert result.analysis_name == "missing"
    assert result.status == "failed"
    assert result.error is not None
    assert result.error.category == "ValueError"
    assert "Available analyses" in result.error.message
