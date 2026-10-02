import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

from openwfn.examples import install_examples

ROOT = Path(__file__).resolve().parents[2]
SOURCE_WATER = ROOT / "examples" / "water" / "water.fchk"
SOURCE_EVERYDAY_QC = ROOT / "examples" / "everyday-qc"
EVERYDAY_QC_FILENAMES = tuple(sorted(path.name for path in SOURCE_EVERYDAY_QC.glob("*.molden")))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "openwfn.cli", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        check=False,
    )


def test_install_examples_copies_exact_maintained_fixture(tmp_path: Path) -> None:
    installed = install_examples(tmp_path / "examples")

    assert installed == (tmp_path / "examples" / "water.fchk",)
    assert digest(installed[0]) == digest(SOURCE_WATER)


def test_install_everyday_qc_suite_copies_exact_maintained_corpus(tmp_path: Path) -> None:
    destination = tmp_path / "examples"
    installed = install_examples(destination, suite="everyday-qc")
    suite_dir = destination / "everyday-qc"

    assert len(installed) == 11
    assert tuple(path.name for path in installed) == EVERYDAY_QC_FILENAMES
    for target in installed:
        assert target.parent == suite_dir
        assert digest(target) == digest(SOURCE_EVERYDAY_QC / target.name)


def test_install_examples_checks_all_conflicts_before_writing(tmp_path: Path) -> None:
    destination = tmp_path / "examples"
    destination.mkdir()
    conflict = destination / "water.fchk"
    conflict.write_text("private data", encoding="utf-8")

    with pytest.raises(FileExistsError, match="water.fchk"):
        install_examples(destination)

    assert conflict.read_text(encoding="utf-8") == "private data"


def test_examples_install_cli_and_summary_workflow(tmp_path: Path) -> None:
    destination = tmp_path / "openwfn-examples"
    installed = run_cli("examples", "install", str(destination))
    summary = run_cli("--format", "json", str(destination / "water.fchk"), "summary")

    assert installed.returncode == 0, installed.stderr
    assert summary.returncode == 0, summary.stderr
    assert '"formula": "H2O"' in summary.stdout


def test_examples_install_cli_everyday_qc_suite(tmp_path: Path) -> None:
    destination = tmp_path / "openwfn-examples"
    installed = run_cli("examples", "install", str(destination), "--suite", "everyday-qc")

    assert installed.returncode == 0, installed.stderr
    suite_dir = destination / "everyday-qc"
    assert tuple(sorted(path.name for path in suite_dir.glob("*.molden"))) == EVERYDAY_QC_FILENAMES


def test_examples_install_cli_refuses_overwrite(tmp_path: Path) -> None:
    destination = tmp_path / "openwfn-examples"
    assert run_cli("examples", "install", str(destination)).returncode == 0

    repeated = run_cli("examples", "install", str(destination))

    assert repeated.returncode != 0
    assert "--overwrite" in repeated.stderr
