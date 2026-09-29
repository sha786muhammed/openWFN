from __future__ import annotations

import hashlib
import json
from pathlib import Path

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


def test_stable_interop_manifest_covers_exact_pinned_inventory() -> None:
    assert MANIFEST.is_file(), "stable interoperability manifest is missing"
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = payload["formats"]

    ids = tuple(entry["format_id"] for entry in entries)
    assert ids == iodata_format_ids()
    assert len(ids) == len(set(ids)) == 25
    assert not any(entry.get("pending", False) for entry in entries)

    for entry in entries:
        assert REQUIRED_KEYS <= set(entry)
        assert len(entry["sha256"]) == 64
        assert entry["provenance"]["redistribution_allowed"] is True
        assert entry["provenance"]["origin"]
        fixture = ROOT / entry["path"]
        assert fixture.is_file(), f"fixture missing for {entry['format_id']}: {fixture}"
        digest = hashlib.sha256(fixture.read_bytes()).hexdigest()
        assert digest == entry["sha256"]
