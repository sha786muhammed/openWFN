import pytest

from openwfn.results import RESULT_SCHEMA_VERSION, ResultRecord


def test_result_record_serializes_a_versioned_success_envelope() -> None:
    result = ResultRecord(
        kind="summary",
        data={"atoms": 3},
        units={"energy": "hartree"},
        validation_status="Validated",
        analysis_name="summary",
        analysis_version="2",
        warnings=("Source omitted method metadata.",),
        provenance={"sha256": "abc123"},
        elapsed_seconds=0.25,
    )

    assert RESULT_SCHEMA_VERSION == "1.0"
    assert result.as_dict() == {
        "analysis_name": "summary",
        "analysis_version": "2",
        "data": {"atoms": 3},
        "elapsed_seconds": 0.25,
        "error": None,
        "kind": "summary",
        "provenance": {"sha256": "abc123"},
        "schema_version": "1.0",
        "status": "success",
        "units": {"energy": "hartree"},
        "validation_status": "Validated",
        "warnings": ["Source omitted method metadata."],
    }


def test_result_record_builds_a_structured_failure_envelope() -> None:
    result = ResultRecord.failure(
        kind="frontier_orbitals",
        analysis_name="beta-frontier",
        analysis_version="1",
        exception=ValueError("Beta orbitals are unavailable."),
        elapsed_seconds=0.01,
    )

    assert result.status == "failed"
    assert result.as_dict()["error"] == {
        "category": "ValueError",
        "message": "Beta orbitals are unavailable.",
        "recoverable": True,
    }


def test_result_record_rejects_negative_elapsed_time() -> None:
    with pytest.raises(ValueError, match="elapsed_seconds must be non-negative"):
        ResultRecord(kind="summary", data={}, elapsed_seconds=-0.1)


def test_result_record_round_trips_a_failure_envelope() -> None:
    original = ResultRecord.failure(
        kind="frontier_orbitals",
        analysis_name="frontier",
        analysis_version="1",
        exception=ValueError("unavailable"),
        elapsed_seconds=0.5,
        provenance={"input_sha256": "abc"},
    )

    restored = ResultRecord.from_dict(original.as_dict())

    assert restored == original


def test_result_record_rejects_an_unknown_schema_when_restoring() -> None:
    with pytest.raises(ValueError, match="Unsupported result schema version: 9.0"):
        ResultRecord.from_dict(
            {
                "schema_version": "9.0",
                "kind": "summary",
                "data": {},
            }
        )
