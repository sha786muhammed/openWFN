from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]


def test_project_version_is_082() -> None:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        version = tomllib.load(stream)["project"]["version"]
    assert version == "0.8.2"


def test_changelog_marks_082_released() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [0.8.2] - 2026-09-28" in changelog
    assert "## [0.8.2] - Unreleased" not in changelog


def test_citation_targets_082_release() -> None:
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert 'version: "0.8.2"' in citation
    assert 'url: "https://github.com/sha786muhammed/openWFN/releases/tag/v0.8.2"' in citation


def test_readme_pins_082_and_keeps_dynamic_pypi_badge() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "python -m pip install openwfn==0.8.2" in readme
    assert "https://img.shields.io/pypi/v/openwfn?label=PyPI" in readme


def test_security_supports_082() -> None:
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert "| `0.8.2` | Supported |" in security
    assert "| `0.8.1` | Not supported |" in security
