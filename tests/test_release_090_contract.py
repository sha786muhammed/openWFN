from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_published_082_release_notes_are_retained() -> None:
    assert (ROOT / "docs/releases/0.8.2.md").is_file()


def test_changelog_marks_082_released() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [0.8.2] - 2026-09-28" in changelog
    assert "## [0.8.2] - Unreleased" not in changelog


def test_citation_targets_090_release() -> None:
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert 'version: "0.9.0"' in citation
    assert 'url: "https://github.com/sha786muhammed/openWFN/releases/tag/v0.9.0"' in citation


def test_readme_pins_090_and_keeps_dynamic_pypi_badge() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "python -m pip install openwfn==0.9.0" in readme
    assert "https://img.shields.io/pypi/v/openwfn?label=PyPI" in readme


def test_security_supports_090() -> None:
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert "| `0.9.0` | Supported |" in security
    assert "| `0.8.2` | Not supported |" in security
    assert "| `0.8.1` | Not supported |" in security
