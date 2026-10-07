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
    assert "python scripts/check_repository.py --root ." in text
    assert "run_external_benchmarks.py" in text
    assert "--repository-only" in text
    assert "macos-latest" in text
    assert "windows-latest" in text
    assert "report build report.html" in text
    assert "workbench workbench.html" in text
    assert "Molecular rendering: 3Dmol.js (BSD-3-Clause)" in text
    assert '"formula"] == "H2O"' in text
    assert "wheel-smoke" in text
    for required in (
        "openwfn examples install",
        "installed-examples/water.fchk summary",
        "benchmark_batch.py --count 20 --workers 2",
    ):
        assert required in text
    wheel_smoke = text.split("  wheel-smoke:", maxsplit=1)[1]
    assert "examples/water/water.fchk" not in wheel_smoke


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


def test_documentation_workflow_runs_repository_preflight_after_install() -> None:
    text = _workflow("docs.yml")

    install = text.index("python -m pip install .[test,docs]")
    preflight = text.index("python scripts/check_repository.py --root .")
    assert preflight > install


def test_interop_ci_keeps_core_isolated_and_checks_multiple_platforms() -> None:
    text = _workflow("tests.yml")
    assert "  interop:" in text
    assert 'python -m pip install -e ".[test,interop]"' in text
    assert "scripts/run_interop_validation.py" in text
    assert "tests/validation/test_cross_format_equivalence.py" in text
    assert "matrix.os" in text and "macos-latest" in text and "windows-latest" in text
    assert "molden/water.molden capabilities" in text
    core = text.split("  wheel-smoke:", 1)[1].split("  interop-wheel-smoke:", 1)[0]
    assert "find dist -name '*.whl'" in core
    assert '"${wheel_file}[resources]"' in core
    assert "benchmark_resources.py --examples-dir installed-examples/everyday-qc" in core
    assert "installed-wheel-resource-report" in core
    assert "qc-iodata" not in core
    assert 'import iodata, cclib' in core
    assert "  interop-wheel-smoke:" in text
    assert '"${wheel_file}[interop]"' in text
