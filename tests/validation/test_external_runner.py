import json
from hashlib import sha256
from pathlib import Path

import pytest

from scripts.run_external_benchmarks import compare_metric, run

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / "examples" / "water" / "water.fchk"


def active_case(*, metric: str = "energy_hartree", digest: str | None = None) -> dict:
    return {
        "id": "water",
        "status": "active",
        "input_scope": "repository",
        "input": "examples/water/water.fchk",
        "sha256": digest or sha256(WATER.read_bytes()).hexdigest(),
        "provenance": {
            "origin": "test fixture",
            "generation_procedure": "existing fixture",
            "upstream_commit": "local-test",
            "redistribution_status": "test",
        },
        "reference": {
            "program": "independent-test",
            "version": "1",
            "procedure": "literal expectation",
        },
        "metrics": [
            {
                "name": metric,
                "expected": -75.58595974892307,
                "unit": "hartree",
                "absolute_tolerance": 1e-10,
            }
        ],
    }


def write_manifest(tmp_path: Path, cases: list[dict]) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps({"schema_version": "1.0", "cases": cases}),
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize(
    ("expected", "observed", "tolerance", "error", "status"),
    [
        (1.0, 1.0, 0.0, 0.0, "passed"),
        (1.0, 1.001, 0.001, 0.001, "passed"),
        (1.0, 1.01, 0.001, 0.01, "failed"),
        ([0.0, 1.0], [0.0, 1.01], 0.001, 0.01, "failed"),
    ],
)
def test_compare_metric_uses_maximum_absolute_error(
    expected: float | list[float],
    observed: float | list[float],
    tolerance: float,
    error: float,
    status: str,
) -> None:
    actual_error, actual_status = compare_metric(expected, observed, tolerance)

    assert actual_error == pytest.approx(error)
    assert actual_status == status


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), float("-inf")])
def test_compare_metric_rejects_non_finite_values(invalid: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        compare_metric(invalid, 1.0, 0.1)


def test_compare_metric_rejects_vector_length_mismatch() -> None:
    with pytest.raises(ValueError, match="length"):
        compare_metric([1.0], [1.0, 2.0], 0.1)


def test_runner_passes_active_case_and_preserves_metric_details(tmp_path: Path) -> None:
    payload = run(write_manifest(tmp_path, [active_case()]))

    assert payload["status"] == "passed"
    assert payload["summary"] == {"passed": 1, "failed": 0, "pending": 0}
    assert payload["results"][0]["metric"] == "energy_hartree"
    assert payload["results"][0]["observed"] == pytest.approx(-75.58595974892307)
    assert payload["results"][0]["status"] == "passed"


def test_runner_resolves_external_input_only_from_explicit_root(tmp_path: Path) -> None:
    external = tmp_path / "external"
    source = external / "sample.fchk"
    source.parent.mkdir()
    source.write_bytes(WATER.read_bytes())
    case = active_case(digest=sha256(source.read_bytes()).hexdigest())
    case["input_scope"] = "external"
    case["input"] = "sample.fchk"

    missing = run(write_manifest(tmp_path, [case]))
    present = run(write_manifest(tmp_path, [case]), external)

    assert missing["status"] == "failed"
    assert "--input-root" in missing["results"][0]["error"]
    assert present["status"] == "passed"


def test_runner_fails_before_analysis_on_checksum_mismatch(tmp_path: Path) -> None:
    payload = run(write_manifest(tmp_path, [active_case(digest="0" * 64)]), ROOT)

    assert payload["status"] == "failed"
    assert payload["results"] == [
        {"case": "water", "status": "failed", "error": "SHA-256 mismatch"}
    ]


def test_runner_rejects_unknown_or_missing_metric(tmp_path: Path) -> None:
    payload = run(write_manifest(tmp_path, [active_case(metric="unknown_metric")]), ROOT)

    assert payload["status"] == "failed"
    assert payload["results"][0]["status"] == "failed"
    assert "Unsupported benchmark metric" in payload["results"][0]["error"]


def test_runner_preserves_pending_case_without_counting_it_as_passed(tmp_path: Path) -> None:
    pending = {
        "id": "benzene",
        "status": "pending",
        "reason": "reference unavailable",
        "provenance": {"origin": "upstream", "redistribution_status": "external"},
    }

    payload = run(write_manifest(tmp_path, [pending]), None)

    assert payload["status"] == "pending"
    assert payload["summary"] == {"passed": 0, "failed": 0, "pending": 1}
    assert payload["results"] == [
        {
            "case": "benzene",
            "status": "pending",
            "reason": "reference unavailable",
        }
    ]


def test_runner_records_grid_points_and_convergence_decision(tmp_path: Path) -> None:
    case = active_case()
    case["metrics"] = [
        {
            "kind": "grid_convergence",
            "name": "total_density_convergence",
            "density_kind": "total",
            "spacings": [0.5, 0.4],
            "padding": 3.0,
            "maximum_relative_error": 1.0,
            "maximum_successive_change": 1.0,
            "unit": "electron",
        }
    ]

    payload = run(write_manifest(tmp_path, [case]), ROOT)

    result = payload["results"][0]
    assert result["metric"] == "total_density_convergence"
    assert len(result["points"]) == 2
    assert result["points"][0]["spacing"] == 0.5
    assert result["points"][1]["spacing"] == 0.4
    assert result["status"] == "passed"
