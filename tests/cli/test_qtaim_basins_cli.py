import json
import os
import subprocess
import sys
from pathlib import Path

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


def _small_args() -> tuple[str, ...]:
    return (
        "--radial-points", "2",
        "--theta-points", "2",
        "--phi-points", "4",
        "--radial-extent", "1.5",
        "--chunk-size", "16",
        "--max-flow-steps", "1",
    )


def test_population_qtaim_cli_emits_json_safe_result() -> None:
    result = run_cli(
        "--format", "json",
        str(WATER),
        "population", "qtaim",
        *_small_args(),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["kind"] == "qtaim_basins"
    assert payload["validation_status"] == "Experimental"
    assert payload["data"]["settings"]["max_flow_steps"] == 1


def test_population_qtaim_cli_boundary_flag_maps_to_same_setting() -> None:
    result = run_cli(
        "--format", "json",
        str(WATER),
        "population", "qtaim",
        *_small_args(),
        "--boundary-diagnostics",
        "--boundary-spacing", "3.0",
        "--boundary-padding", "0.1",
        "--boundary-min-neighbors", "3",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["data"]["boundary_diagnostics"]["status"] != "not_requested"
    assert payload["data"]["settings"]["boundary_spacing_bohr"] == 3.0
    assert payload["data"]["settings"]["boundary_padding_bohr"] == 0.1
    assert payload["data"]["settings"]["boundary_min_neighbors"] == 3


def test_population_qtaim_cli_rejects_invalid_numeric_controls() -> None:
    result = run_cli(
        "--format", "json",
        str(WATER),
        "population", "qtaim",
        *_small_args(),
        "--flow-step", "-0.1",
    )

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert "flow_step_bohr" in payload["error"]["message"]


def test_registry_api_cli_use_same_default_scientific_settings() -> None:
    result = run_cli(
        "--format", "json",
        str(WATER),
        "population", "qtaim",
        *_small_args(),
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    settings = payload["data"]["settings"]

    assert settings["flow_step_bohr"] == 0.05
    assert settings["attractor_capture_radius_bohr"] == 0.25
    assert settings["gradient_floor"] == 1.0e-10
    assert settings["max_backtracks"] == 8
    assert settings["bounds_padding_bohr"] == 6.0
    assert settings["attractor_match_tolerance_bohr"] == 0.35
    assert settings["max_zero_flux_p95"] == 0.15
