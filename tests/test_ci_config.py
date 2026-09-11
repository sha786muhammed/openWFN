import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _workflow(name: str) -> str:
    return (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")


def test_test_workflow_has_required_quality_and_platform_gates() -> None:
    text = _workflow("tests.yml")
    for version in ('"3.10"', '"3.11"', '"3.12"', '"3.13"'):
        assert version in text
    for gate in ("ruff check", "pytest --strict-markers", "run_validation.py", "twine check"):
        assert gate in text
    assert "macos-latest" in text
    assert "windows-latest" in text
    assert "wheel-smoke" in text


def test_security_workflow_runs_pip_audit_without_write_permissions() -> None:
    text = _workflow("security.yml")
    assert "pip-audit" in text
    assert "contents: read" in text
    assert "schedule:" in text
    assert "id-token: write" not in text


def test_actions_are_pinned_to_full_commit_shas() -> None:
    for name in ("tests.yml", "docs.yml", "security.yml"):
        text = _workflow(name)
        action_refs = re.findall(r"uses:\s+[^\s@]+@([^\s#]+)", text)
        assert action_refs, name
        assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in action_refs), (name, action_refs)
