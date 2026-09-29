import re
import subprocess
import sys
from datetime import date
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

import openwfn
from scripts.sync_release_metadata import rendered_citation

ROOT = Path(__file__).resolve().parents[1]


def project_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)["project"]["version"]


def project_metadata() -> dict[str, object]:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)["project"]


def citation_version() -> str:
    text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    match = re.search(r"(?m)^version:\s*[\"']?([^\"'\s]+)", text)
    assert match is not None
    return match.group(1)


def citation_release_date() -> str:
    text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    match = re.search(r"(?m)^date-released:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", text)
    assert match is not None
    return match.group(1)


def test_release_version_is_082() -> None:
    assert project_version() == "0.8.2"


def test_runtime_version_matches_project() -> None:
    assert openwfn.__version__ == project_version()


def test_citation_version_matches_project() -> None:
    assert citation_version() == project_version()


def test_citation_release_date_is_valid_iso_date() -> None:
    parsed = date.fromisoformat(citation_release_date())
    assert parsed.isoformat() == citation_release_date()


def test_project_uses_current_spdx_license_metadata() -> None:
    metadata = project_metadata()
    assert metadata["license"] == "MIT"
    assert "License :: OSI Approved :: MIT License" not in metadata["classifiers"]


def test_project_urls_cover_public_resources() -> None:
    urls = project_metadata()["urls"]

    assert urls == {
        "Homepage": "https://sha786muhammed.github.io/openWFN/",
        "Documentation": "https://sha786muhammed.github.io/openWFN/",
        "Repository": "https://github.com/sha786muhammed/openWFN",
        "Issues": "https://github.com/sha786muhammed/openWFN/issues",
        "Changelog": "https://github.com/sha786muhammed/openWFN/blob/main/CHANGELOG.md",
        "Releases": "https://github.com/sha786muhammed/openWFN/releases",
    }


def test_sync_script_is_idempotent() -> None:
    before = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "scripts/sync_release_metadata.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    after = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert result.returncode == 0, result.stderr
    assert after == before


def test_citation_contains_verified_software_fields() -> None:
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")

    for required in (
        "type: software",
        'title: "openWFN: Wavefunction post-processing analysis toolkit"',
        'version: "0.8.2"',
        "date-released: 2026-09-28",
        "family-names: Shaji",
        "given-names: Muhammed Shah",
        "license: MIT",
        'repository-code: "https://github.com/sha786muhammed/openWFN"',
        'url: "https://github.com/sha786muhammed/openWFN/releases/tag/v0.8.2"',
    ):
        assert required in citation


def test_active_citation_omits_deferred_identity_and_paper_fields() -> None:
    active = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in ("CITATION.cff", "docs/citation.md", "README.md")
    ).lower()

    for forbidden in (
        "university of louisville",
        "affiliation:",
        "email:",
        "doi:",
        "orcid:",
        "preferred-citation:",
        "journal:",
        "research-grade gaussian wavefunction analysis",
    ):
        assert forbidden not in active


def test_citation_guide_matches_cff() -> None:
    guide = (ROOT / "docs" / "citation.md").read_text(encoding="utf-8")

    for field in (
        "Muhammed Shah Shaji",
        "openWFN: Wavefunction post-processing analysis toolkit",
        "0.8.2",
        "2026",
        "https://github.com/sha786muhammed/openWFN/releases/tag/v0.8.2",
        "@software{shaji_openwfn_2026",
    ):
        assert field in guide


def test_citation_guide_records_reproducibility_fields() -> None:
    guide = (ROOT / "docs" / "citation.md").read_text(encoding="utf-8").lower()

    for field in (
        "exact openwfn version",
        "input sha-256",
        "source program",
        "method",
        "basis",
        "charge",
        "multiplicity",
        "numerical controls",
    ):
        assert field in guide
    assert "archival deposit or publication" in guide
    assert "does not determine authorship" in guide


def test_sync_script_preserves_citation_contract() -> None:
    original = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    rendered = rendered_citation(
        original,
        "0.8.0a3",
        "2026-10-01",
        "https://github.com/sha786muhammed/openWFN/releases/tag/v0.8.0a3",
    )

    assert 'version: "0.8.0a3"' in rendered
    assert "date-released: 2026-10-01" in rendered
    assert 'url: "https://github.com/sha786muhammed/openWFN/releases/tag/v0.8.0a3"' in rendered
    assert "given-names: Muhammed Shah" in rendered
    assert "affiliation:" not in rendered.lower()


def test_readme_documents_binary_checkpoint_requirement() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "proprietary binary" in readme
    assert "formchk" in readme
    assert "openwfn molecule.fchk summary" in readme


def test_changelog_contains_current_release() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [0.8.2] - 2026-09-28" in changelog


def test_release_notes_document_capability_boundaries() -> None:
    notes = (ROOT / "docs" / "releases" / "0.8.2.md").read_text(encoding="utf-8")
    for required in (
        "corrective patch release",
        "Validated",
        "Experimental",
        "Unsupported",
        "openwfn==0.8.2",
        "partial",
        "0.15 bohr",
        "Python 3.10–3.13",
    ):
        assert required in notes
    assert (ROOT / "docs" / "releases" / "0.8.1.md").is_file()


def test_release_guide_contains_required_gates() -> None:
    guide = (ROOT / "docs/releasing.md").read_text(encoding="utf-8")
    for required in (
        "sync_release_metadata.py --check",
        "pytest",
        "python -m build",
        "python -m twine check",
        "git tag -a",
        "0.8.2",
    ):
        assert required in guide
    assert "dist/openwfn-0.7.2" not in guide


def test_publish_workflow_is_oidc_only_pinned_and_version_gated() -> None:
    workflow = (ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
    assert "id-token: write" in workflow
    assert "password:" not in workflow
    assert "API_TOKEN" not in workflow
    assert "dc37677b2e1c63e2034f94d8a5b11f265b73ba33" in workflow
    assert "Verify release tag matches package version" in workflow
