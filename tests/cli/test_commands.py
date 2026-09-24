import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from openwfn import __version__

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / "examples" / "water" / "water.fchk"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "openwfn.cli", *args],
        capture_output=True,
        text=True,
        env=environment,
    )


def test_version_does_not_require_input_file() -> None:
    result = run_cli("--version")

    assert result.returncode == 0
    assert result.stdout.strip() == f"openWFN {__version__}"


def test_nested_geometry_distance_supports_json_output() -> None:
    result = run_cli("--format", "json", str(WATER), "geometry", "distance", "1", "2")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["kind"] == "distance"
    assert payload["data"]["value"] == 0.966598
    assert payload["units"]["value"] == "angstrom"


def test_summary_json_uses_the_registered_analysis_envelope() -> None:
    result = run_cli("--format", "json", str(WATER), "summary")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["analysis_name"] == "summary"
    assert payload["analysis_version"] == "1"
    assert payload["schema_version"] == "1.0"
    assert payload["status"] == "success"
    assert payload["provenance"]["source_format"] == "fchk"
    assert len(payload["provenance"]["input_sha256"]) == 64


def test_non_interactive_file_without_command_defaults_to_summary() -> None:
    result = run_cli("--non-interactive", "--format", "json", str(WATER))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["kind"] == "summary"
    assert payload["data"]["formula"] == "H2O"


def test_doctor_describes_gaussian_output_metadata_without_traceback(tmp_path: Path) -> None:
    source = tmp_path / "job.log"
    source.write_text(
        "# RHF/3-21G\nSCF Done: E(RHF) = -7.5\nNormal termination of Gaussian\n",
        encoding="utf-8",
    )

    result = run_cli("--format", "json", str(source), "doctor")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["data"]["input_kind"] == "calculation-metadata"
    assert payload["data"]["capabilities"] == {
        "basis": False,
        "density": False,
        "metadata": True,
        "orbitals": False,
        "volumetric_grid": False,
    }
    assert "Traceback" not in result.stderr


def test_doctor_describes_cube_grid_without_traceback(tmp_path: Path) -> None:
    source = tmp_path / "density.cube"
    source.write_text(
        "density\nfixture\n0 0 0 0\n1 1 0 0\n1 0 1 0\n1 0 0 1\n0.5\n",
        encoding="utf-8",
    )

    result = run_cli("--format", "json", str(source), "doctor")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["data"]["input_kind"] == "volumetric-grid"
    assert payload["data"]["capabilities"] == {
        "basis": False,
        "density": True,
        "metadata": False,
        "orbitals": False,
        "volumetric_grid": True,
    }
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("suffix", ["log", "cube"])
def test_summary_rejects_non_molecular_input_cleanly(tmp_path: Path, suffix: str) -> None:
    source = tmp_path / f"input.{suffix}"
    if suffix == "log":
        source.write_text("# RHF/3-21G\nSCF Done: E(RHF) = -7.5\n", encoding="utf-8")
    else:
        source.write_text(
            "density\nfixture\n0 0 0 0\n1 1 0 0\n1 0 1 0\n1 0 0 1\n0.5\n",
            encoding="utf-8",
        )

    result = run_cli(str(source), "summary")

    assert result.returncode == 4
    assert "does not contain a molecular calculation" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    ("suffix", "contents", "command"),
    [
        (
            "log",
            "# RHF/3-21G\nSCF Done: E(RHF) = -7.5\n",
            ("orbitals", "frontier"),
        ),
        (
            "cube",
            "density\nfixture\n0 0 0 0\n1 1 0 0\n1 0 1 0\n1 0 0 1\n0.5\n",
            ("validate",),
        ),
    ],
)
def test_molecular_analysis_commands_reject_other_input_kinds_cleanly(
    tmp_path: Path,
    suffix: str,
    contents: str,
    command: tuple[str, ...],
) -> None:
    source = tmp_path / f"input.{suffix}"
    source.write_text(contents, encoding="utf-8")

    result = run_cli(str(source), *command)

    assert result.returncode == 4
    assert "does not contain a molecular calculation" in result.stderr
    assert "Traceback" not in result.stderr


def test_nested_geometry_angle_runs_without_legacy_retranslation() -> None:
    result = run_cli(str(WATER), "geometry", "angle", "2", "1", "3")

    assert result.returncode == 0
    assert "107.693231" in result.stdout


def test_nested_geometry_dihedral_runs_without_legacy_retranslation() -> None:
    result = run_cli(str(WATER), "geometry", "dihedral", "1", "2", "3", "1")

    assert result.returncode != 2
    assert "invalid choice: 'geometry'" not in result.stderr


def test_legacy_and_nested_distance_report_same_value() -> None:
    legacy = run_cli(str(WATER), "dist", "1", "2")
    nested = run_cli(str(WATER), "geometry", "distance", "1", "2")

    assert legacy.returncode == nested.returncode == 0
    assert "0.966598" in legacy.stdout
    assert "0.966598" in nested.stdout


def test_help_lists_complete_v070_command_groups() -> None:
    result = run_cli("--help")

    for command in (
        "geometry", "orbitals", "density", "esp", "population", "cube",
        "convert", "export", "plot", "view", "report", "batch", "validate",
        "workbench", "doctor",
    ):
        assert command in result.stdout


def test_population_mulliken_supports_json_output() -> None:
    result = run_cli("--format", "json", str(WATER), "population", "mulliken")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["kind"] == "mulliken_population"
    assert payload["data"]["electron_count"] == 10.0
    assert sum(payload["data"]["atomic_charges"]) == pytest.approx(0.0, abs=1e-6)
    assert payload["validation_status"] == "Stable"


def test_population_lowdin_runs_from_fchk() -> None:
    result = run_cli(str(WATER), "population", "lowdin")

    assert result.returncode == 0
    assert "Lowdin Population" in result.stdout
    assert "Electron Count: 10.0 electron" in result.stdout


def test_orbitals_frontier_reports_water_homo_lumo_gap() -> None:
    result = run_cli("--format", "json", str(WATER), "orbitals", "frontier")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["kind"] == "frontier_orbitals"
    assert payload["data"]["homo_number"] == 5
    assert payload["data"]["lumo_number"] == 6
    assert payload["data"]["gap_ev"] == pytest.approx(20.09080139)
    assert payload["validation_status"] == "Stable"


def test_density_integrate_validates_water_electron_count() -> None:
    result = run_cli(
        "--format", "json", str(WATER), "density", "integrate",
        "--spacing", "0.15", "--padding", "6.0",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["kind"] == "density_integration"
    assert payload["data"]["expected_electrons"] == 10.0
    assert payload["data"]["relative_error"] < 0.005
    assert payload["validation_status"] == "Validated"


def test_density_cube_exports_parseable_file(tmp_path: Path) -> None:
    output = tmp_path / "water-density.cube"

    result = run_cli(
        str(WATER), "density", "cube", str(output),
        "--spacing", "0.3", "--padding", "2.0",
    )

    assert result.returncode == 0
    assert output.exists()
    assert "Density Cube" in result.stdout


def test_esp_point_supports_mulliken_atomic_charge_model() -> None:
    result = run_cli(
        "--format", "json", str(WATER), "esp", "point", "10", "0", "0",
        "--component", "mulliken",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["kind"] == "electrostatic_potential"
    assert payload["data"]["component"] == "mulliken"
    assert payload["units"]["value"] == "hartree/e"
    assert payload["validation_status"] == "Stable"


def test_esp_point_total_is_marked_experimental() -> None:
    result = run_cli(
        "--format", "json", str(WATER), "esp", "point", "5", "0", "0",
        "--component", "total", "--spacing", "0.3", "--padding", "4.0",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["component"] == "total"
    assert payload["validation_status"] == "Experimental"


def test_report_build_exports_self_contained_html(tmp_path: Path) -> None:
    output = tmp_path / "water-report.html"
    result = run_cli(
        str(WATER), "report", "build", str(output),
        "--analyses", "summary,frontier,mulliken",
    )

    assert result.returncode == 0
    assert output.exists()
    assert "Research Report" in result.stdout
    assert WATER.read_bytes()
    assert "openWFN Research Report" in output.read_text(encoding="utf-8")


def test_convert_mol_includes_inferred_connectivity(tmp_path: Path) -> None:
    output = tmp_path / "water.mol"
    result = run_cli(str(WATER), "convert", "--to", "mol", "--output", str(output))

    assert result.returncode == 0
    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[3].split()[:2] == ["3", "2"]
    assert len(lines[7:9]) == 2


def test_convert_sdf_includes_inferred_connectivity(tmp_path: Path) -> None:
    output = tmp_path / "water.sdf"
    result = run_cli(str(WATER), "convert", "--to", "sdf", "--output", str(output))

    assert result.returncode == 0
    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[3].split()[:2] == ["3", "2"]
    assert lines[-1] == "$$$$"


def test_workbench_command_exports_offline_application(tmp_path: Path) -> None:
    output = tmp_path / "water-workbench.html"

    result = run_cli(str(WATER), "workbench", str(output))

    assert result.returncode == 0
    assert output.exists()
    payload = output.read_text(encoding="utf-8")
    assert 'id="openwfn-workbench"' in payload
    assert "Molecular Workbench" in result.stdout
    assert "Status: Experimental" in result.stdout


def test_workbench_command_protects_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "water-workbench.html"
    output.write_text("keep", encoding="utf-8")

    result = run_cli(str(WATER), "workbench", str(output))

    assert result.returncode == 1
    assert "Output exists" in result.stderr
    assert output.read_text(encoding="utf-8") == "keep"
