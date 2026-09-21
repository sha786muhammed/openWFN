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


def test_release_version_is_080a1() -> None:
    assert project_version() == "0.8.0a1"


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


def test_readme_documents_binary_checkpoint_requirement() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "proprietary binary" in readme
    assert "formchk" in readme
    assert "openwfn molecule.fchk summary" in readme


def test_changelog_contains_current_release() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [0.8.0a1] - 2026-09-21" in changelog


def test_release_notes_document_capability_boundaries() -> None:
    notes = (ROOT / "docs" / "releases" / "0.8.0a1.md").read_text(encoding="utf-8")
    for required in (
        "alpha",
        "Validated",
        "Experimental",
        "Unsupported",
        "GitHub Pages",
    ):
        assert required in notes


def test_release_guide_contains_required_gates() -> None:
    guide = (ROOT / "docs/releasing.md").read_text(encoding="utf-8")
    for required in (
        "sync_release_metadata.py --check",
        "pytest",
        "python -m build",
        "python -m twine check",
        "git tag -a",
        "0.8.0a1",
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
