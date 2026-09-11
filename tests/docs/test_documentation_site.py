import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_mkdocs_navigation_references_existing_pages() -> None:
    config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    referenced = re.findall(r":\s+([\w/-]+\.md)\s*$", config, flags=re.MULTILINE)

    assert referenced
    for relative in referenced:
        assert (ROOT / "docs" / relative).is_file(), relative


def test_documentation_covers_required_user_and_scientific_topics() -> None:
    required = (
        "index.md", "installation.md", "quick-start.md", "cli.md", "python-api.md",
        "workbench.md", "formats.md", "methods.md", "validation.md", "limitations.md",
        "citation.md", "tutorials/geometry.md", "tutorials/orbitals-density.md",
        "tutorials/reports.md",
    )
    for relative in required:
        assert (ROOT / "docs" / relative).is_file(), relative


def test_documented_capability_states_are_defined() -> None:
    validation = (ROOT / "docs" / "validation.md").read_text(encoding="utf-8")
    for state in ("Stable", "Validated", "Experimental", "Unsupported"):
        assert f"**{state}**" in validation


def test_pages_workflow_uses_least_privilege_and_main_only() -> None:
    workflow = (ROOT / ".github" / "workflows" / "docs.yml").read_text(encoding="utf-8")
    assert "branches: [main]" in workflow
    assert "pages: write" in workflow
    assert "id-token: write" in workflow
    assert "contents: read" in workflow
    assert "cancel-in-progress: true" in workflow
    assert "mkdocs build --strict" in workflow
