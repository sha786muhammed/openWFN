from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_changelog_keeps_081_release_history() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [0.8.1] - 2026-09-28" in changelog
    assert "## [0.8.1] - Unreleased" not in changelog


def test_081_release_notes_remain_available() -> None:
    notes = ROOT / "docs" / "releases" / "0.8.1.md"
    assert notes.is_file()
    text = notes.read_text(encoding="utf-8")
    assert "openWFN 0.8.1" in text
    assert "openwfn==0.8.1" in text


def test_readme_keeps_dynamic_pypi_badge() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "https://img.shields.io/pypi/v/openwfn?label=PyPI" in readme
