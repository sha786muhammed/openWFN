from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_current_validation_page_has_no_stale_release_instructions() -> None:
    text = (ROOT / "docs/project/everyday-qc-validation.md").read_text(encoding="utf-8")
    stale = (
        "Keep 0.9.2 as the stable release",
        "No release version was changed",
        "a stable 0.10.0 needs",
    )
    for phrase in stale:
        assert phrase not in text


def test_validation_manifest_declares_current_and_historical_evidence() -> None:
    manifest_path = ROOT / "validation/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1.0"
    assert manifest["current_release"] == "0.10.1"
    assert manifest["resource_benchmark"]["establishes_scientific_validation"] is False
    assert manifest["historical_captures"]["everyday-qc/report.json"]["authoritative_status"] is False
    assert manifest["historical_captures"]["everyday-qc/esp-report.json"]["authoritative_status"] is False
    for capability in ("orbital-composition", "mayer", "dos", "pdos", "point-esp"):
        assert capability in manifest["capabilities"]
        assert manifest["capabilities"][capability]["status"] in {"Validated", "Experimental"}


def test_release_resource_claim_is_explicitly_not_scientific_validation() -> None:
    text = (ROOT / "docs/releases/0.10.1.md").read_text(encoding="utf-8")
    assert "99/99 prescribed CLI workflows completed successfully within resource limits" in text
    assert "scientific result status is evaluated separately" in text


def test_publish_workflow_is_version_driven_and_retests_public_package() -> None:
    text = (ROOT / ".github/workflows/publish.yml").read_text(encoding="utf-8")
    assert 'RELEASE_VERSION: "0.10.0"' not in text
    assert 'RELEASE_TAG: "v0.10.0"' not in text
    assert 'contains(github.event.head_commit.message, \'release:0.10.0\')' not in text
    assert "paths:" not in text
    assert "openwfn[interop,resources]==${RELEASE_VERSION}" in text
    assert "benchmark_resources.py" in text
    assert "--examples-dir" in text
    assert "published-examples/everyday-qc" in text


def test_package_data_includes_everyday_qc_corpus() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'example_data/everyday-qc/*.molden' in text
    assert 'example_data/everyday-qc/*.json' in text
    assert 'example_data/everyday-qc/*.md' in text


def test_benchmark_can_be_pointed_at_installed_corpus() -> None:
    text = (ROOT / "scripts/benchmark_resources.py").read_text(encoding="utf-8")
    assert "--examples-dir" in text
    assert "args.examples_dir" in text


def test_current_method_docs_do_not_retain_pre_release_labels() -> None:
    pages = {
        "docs/science/mayer.md": ("# Mayer bond orders (Experimental)",),
        "docs/science/orbital-composition.md": ("# Orbital composition (Experimental)",),
        "docs/science/dos-pdos.md": ("Experimental development",),
        "docs/reference/cli.md": ("Development branch:", "Development spectrum commands"),
    }
    for relative_path, stale_phrases in pages.items():
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        for phrase in stale_phrases:
            assert phrase not in text


def test_source_and_packaged_everyday_qc_readmes_are_synchronized() -> None:
    source = (ROOT / "examples/everyday-qc/README.md").read_text(encoding="utf-8")
    packaged = (
        ROOT / "src/openwfn/example_data/everyday-qc/README.md"
    ).read_text(encoding="utf-8")
    assert source == packaged
    assert "not bundled wheel assets" not in source
    assert "openwfn examples install installed-examples" in source
