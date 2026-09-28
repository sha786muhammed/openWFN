import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_required_repository_policy_files_exist() -> None:
    required = (
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "CONTRIBUTORS.md",
        "MAINTAINERS.md",
        "ROADMAP.md",
        "SECURITY.md",
    )

    for relative in required:
        assert (ROOT / relative).is_file(), relative


def test_contributors_match_verified_git_identity_without_affiliation() -> None:
    contributors = read("CONTRIBUTORS.md")

    assert "Muhammed Shah Shaji" in contributors
    assert "@" not in contributors
    assert "affiliation" not in contributors.lower()
    assert "correction" in contributors.lower()


def test_security_policy_uses_private_reporting_and_supported_versions() -> None:
    policy = read("SECURITY.md")

    assert "0.8.0" in policy
    assert "private security advisory" in policy.lower()
    assert "https://github.com/sha786muhammed/openWFN/security/advisories/new" in policy
    assert "scientific discrepancy" in policy.lower()
    assert not re.search(r"[\w.+-]+@[\w.-]+", policy)


def test_scientific_contribution_policy_requires_evidence() -> None:
    policy = read("CONTRIBUTING.md").lower()

    for required in (
        "expected value",
        "units",
        "tolerance",
        "reference procedure",
        "shareable fixture",
        "redistribution",
        "format specification",
        "compatible license",
    ):
        assert required in policy


def test_issue_forms_cover_bug_scientific_discrepancy_and_feature_request() -> None:
    forms = {
        path.name: path.read_text(encoding="utf-8")
        for path in (ROOT / ".github" / "ISSUE_TEMPLATE").glob("*.yml")
    }

    assert {"bug.yml", "scientific-discrepancy.yml", "feature.yml", "config.yml"} <= forms.keys()
    assert "openWFN version" in forms["bug.yml"]
    assert "Minimal reproduction" in forms["bug.yml"]
    for field in ("Expected value", "Units", "Tolerance", "Reference procedure", "Fixture rights"):
        assert field in forms["scientific-discrepancy.yml"]
    assert "Capability boundary" in forms["feature.yml"]


def test_pull_request_template_covers_tests_docs_provenance_and_license() -> None:
    template = read(".github/pull_request_template.md").lower()

    for required in ("tests", "documentation", "provenance", "license", "validation"):
        assert required in template


def test_roadmap_has_no_promised_dates() -> None:
    roadmap = read("ROADMAP.md")

    assert not re.search(r"\b20\d{2}\b", roadmap)
    assert not re.search(r"\bv?\d+\.\d+(?:\.\d+)?\b", roadmap, flags=re.IGNORECASE)
    assert not re.search(r"\bQ[1-4]\b", roadmap)
    assert "No item is assigned a release or delivery date" in roadmap
