import hashlib
import json
from pathlib import Path

import pytest

from openwfn.formats import iodata_format_ids

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
