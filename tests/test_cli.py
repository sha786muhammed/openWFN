import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def run_cli(args, *, cwd=None):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "openwfn.cli", *args],
        cwd=ROOT if cwd is None else cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def test_cli_version():
    result = run_cli(["--version"])
    assert result.returncode == 0
    assert "openwfn" in result.stdout.lower()


def test_cli_summary(tmp_path):
    f = tmp_path / "a.fchk"
    f.write_text("""Test
SP        RHF                                           STO-3G
Number of atoms                            I              3
Charge                                     I              0
Multiplicity                               I              1
Atomic numbers                             I   N=           3
8 1 1
Current cartesian coordinates R N= 3
0.0 0.0 0.0
""")

    result = run_cli([str(f), "summary"])

    assert result.returncode == 0
    assert "Atoms:" in result.stdout


def test_cli_hirshfeld_population_json_contract():
    result = run_cli([
        "--format",
        "json",
        "examples/water/water.fchk",
        "population",
        "hirshfeld",
    ])

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["kind"] == "hirshfeld_population"
    assert payload["status"] == "success"
    assert payload["validation_status"] == "Validated"
    assert payload["data"]["method"] == "Hirshfeld"
    assert payload["data"]["reference_library"]["id"] == "openwfn-hirshfeld-proatoms-v1"
    assert payload["data"]["diagnostics"]["charge_closure_residual"] <= 5.0e-3


def test_cli_hirshfeld_expert_grid_controls_are_explicit():
    result = run_cli([
        "--format",
        "json",
        "examples/water/water.fchk",
        "population",
        "hirshfeld",
        "--radial-points",
        "8",
        "--theta-points",
        "4",
        "--phi-points",
        "8",
        "--radial-extent",
        "0.5",
        "--chunk-size",
        "512",
    ])

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "partial"
    assert payload["validation_status"] == "Experimental"
    assert payload["data"]["quadrature"] == {
        "radial_points": 8,
        "theta_points": 4,
        "phi_points": 8,
        "radial_extent_bohr": 0.5,
        "chunk_size": 512,
    }
    assert payload["data"]["diagnostics"]["charge_closure_residual"] > 0.1


def test_cli_csv_output():
    result = run_cli([
        "--format",
        "csv",
        "examples/water/water.fchk",
        "summary",
    ])
    assert result.returncode == 0
    assert "formula" in result.stdout


def test_cli_output_file(tmp_path):
    out = tmp_path / "summary.json"
    result = run_cli([
        "--format",
        "json",
        "--output",
        str(out),
        "examples/water/water.fchk",
        "summary",
    ])
    assert result.returncode == 0
    assert out.exists()
    payload = json.loads(out.read_text())
    assert payload["status"] == "success"


def test_cli_bad_input_returns_nonzero(tmp_path):
    missing = tmp_path / "missing.fchk"
    result = run_cli([str(missing), "summary"])
    assert result.returncode != 0


def test_cli_json_failure_is_structured(tmp_path):
    missing = tmp_path / "missing.fchk"
    result = run_cli(["--format", "json", str(missing), "summary"])
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert payload["error"]


def test_cli_help():
    result = run_cli(["--help"])
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()


def test_cli_unknown_command_is_nonzero():
    result = run_cli(["examples/water/water.fchk", "definitely-not-a-command"])
    assert result.returncode != 0


def test_cli_plain_output():
    result = run_cli(["--format", "plain", "examples/water/water.fchk", "summary"])
    assert result.returncode == 0
    assert "Formula:" in result.stdout


def test_cli_overwrite_guard(tmp_path):
    out = tmp_path / "summary.json"
    out.write_text("existing")
    result = run_cli([
        "--format",
        "json",
        "--output",
        str(out),
        "examples/water/water.fchk",
        "summary",
    ])
    assert result.returncode != 0
    assert out.read_text() == "existing"


def test_cli_overwrite_allows_replacement(tmp_path):
    out = tmp_path / "summary.json"
    out.write_text("existing")
    result = run_cli([
        "--overwrite",
        "--format",
        "json",
        "--output",
        str(out),
        "examples/water/water.fchk",
        "summary",
    ])
    assert result.returncode == 0
    assert json.loads(out.read_text())["status"] == "success"
