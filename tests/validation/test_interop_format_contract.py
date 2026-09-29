import hashlib
import json
from pathlib import Path

import pytest

from openwfn.errors import ParseError
from openwfn.formats import iodata_format_ids
from openwfn.ingest import load_input

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "validation" / "interop" / "manifest.json"
REQUIRED_KEYS = {
    "format_id",
    "path",
    "sha256",
    "provenance",
    "expected_components",
    "expected_capabilities",
    "expected_analyses",
}


def _entries() -> list[dict[str, object]]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    entries = payload["formats"]
    assert isinstance(entries, list)
    return entries


def test_stable_manifest_covers_exact_pinned_format_inventory() -> None:
    entries = _entries()
    ids = [str(entry["format_id"]) for entry in entries]

    assert len(ids) == len(set(ids))
    assert tuple(sorted(ids)) == iodata_format_ids()
    assert len(ids) == 25


def test_every_stable_format_entry_has_complete_contract_and_redistribution_provenance() -> None:
    for entry in _entries():
        assert REQUIRED_KEYS <= set(entry)
        assert entry.get("status", "Stable") == "Stable"
        assert entry.get("pending", False) is False
        assert isinstance(entry["sha256"], str) and len(entry["sha256"]) == 64
        provenance = entry["provenance"]
        assert isinstance(provenance, dict)
        assert provenance.get("redistribution_safe") is True
        assert provenance.get("origin")
        assert provenance.get("license")


def test_manifest_checksums_match_redistributable_fixtures() -> None:
    for entry in _entries():
        path = ROOT / str(entry["path"])
        assert path.is_file(), f"missing fixture for {entry['format_id']}: {path}"
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        assert observed == entry["sha256"]


def test_validation_runner_exposes_public_run_contract() -> None:
    try:
        from scripts.run_interop_validation import run
    except ImportError as exc:  # pragma: no cover - RED guard
        pytest.fail(f"interop validation runner is unavailable: {exc}")

    assert callable(run)
    report = run(MANIFEST)
    assert report["overall"] == "PASSED"
    assert report["passed"] == 25
    assert report["failed"] == 0


def test_qcschema_molecule_does_not_fabricate_integral_data() -> None:
    data = load_input(
        ROOT / "tests/fixtures/interop/json_qcschema/water.qcschema.json",
        format_hint="json_qcschema",
    )
    assert data.structure is not None
    assert data.integrals is None


def test_gaussian_log_records_omitted_ao_integral_provenance() -> None:
    data = load_input(
        ROOT / "tests/fixtures/interop/gaussianlog/water.log",
        format_hint="gaussianlog",
    )
    assert data.integrals is None
    assert any("olp" in warning for warning in data.provenance.warnings)


def test_cp2k_multicontraction_basis_keeps_wavefunction() -> None:
    data = load_input(
        ROOT / "tests/fixtures/interop/cp2klog/helium.cp2k.out",
        format_hint="cp2klog",
    )
    assert data.calculation is not None
    assert data.calculation.basis.n_functions == 2


def test_partial_qchem_output_reports_missing_frontier() -> None:
    from openwfn.analysis.registry import run_analysis_safe

    data = load_input(
        ROOT / "tests/fixtures/interop/qchemlog/water.qchemlog",
        format_hint="qchemlog",
    )
    assert data.structure is not None
    assert data.calculation is None
    assert any("incomplete wavefunction" in item for item in data.provenance.warnings)
    result = run_analysis_safe(data, "frontier")
    assert result.status == "failed"
    assert result.validation_status == "Unsupported"


def test_malformed_qchem_output_fails_at_ingestion(tmp_path: Path) -> None:
    malformed = tmp_path / "bad.qchemlog"
    malformed.write_text("$rem\njobtype sp\n$end\n", encoding="utf-8")
    with pytest.raises(ParseError, match="qchemlog"):
        load_input(malformed, format_hint="qchemlog")


def test_runner_fails_a_corrupted_fixture_checksum(tmp_path: Path) -> None:
    from scripts.run_interop_validation import run

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["formats"][0]["sha256"] = "0" * 64
    altered = tmp_path / "manifest.json"
    altered.write_text(json.dumps(manifest), encoding="utf-8")
    result = run(altered, output_dir=tmp_path)
    assert result["overall"] == "FAILED"
    assert result["failed"] == 1
    assert "SHA-256" in result["formats"][0]["errors"][0]
