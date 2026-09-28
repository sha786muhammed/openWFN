from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_readme_scopes_population_and_density_claims() -> None:
    readme = _text("README.md")

    assert "effective nuclear charges" in readme
    assert "conservation failures return partial results" in readme
    assert "0.15 bohr" in readme


def test_python_api_documents_source_faithful_scientific_semantics() -> None:
    api = _text("docs/reference/python-api.md")

    for phrase in (
        "FCHK `Nuclear charges`",
        "FCHK `Number of electrons`",
        '`status="partial"`',
        "SCF density",
        '`spin="all"`',
        "0.15 bohr",
    ):
        assert phrase in api


def test_cli_documents_spin_complete_and_partial_behavior() -> None:
    cli = _text("docs/reference/cli.md")

    assert "--spin alpha|beta|all" in cli
    assert "frontier --spin all" in cli
    assert "partial" in cli
    assert "SCF density" in cli


def test_limitations_document_special_case_boundaries() -> None:
    limitations = _text("docs/limitations.md")

    for phrase in (
        "ECP",
        "ghost",
        "post-HF",
        "SCF density",
        "0.15 bohr",
    ):
        assert phrase in limitations


def test_changelog_records_scientific_correctness_hardening_release() -> None:
    changelog = _text("CHANGELOG.md")

    assert "## [0.8.1]" in changelog
    assert "effective nuclear charges" in changelog
    assert "spin-complete" in changelog
    assert "chunked" in changelog
