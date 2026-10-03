import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "gaussian" / "excited" / "tddft_states.log"


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "openwfn.cli", *arguments],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        check=False,
    )


def test_excited_states_cli_renders_compact_table() -> None:
    result = _run(str(FIXTURE), "excited", "states")
    assert result.returncode == 0, result.stderr
    assert "Excited States" in result.stdout
    assert "Energy (eV)" in result.stdout
    assert "4.000000" in result.stdout
    assert "Analysis Validation Status: Experimental" in result.stdout


def test_excited_state_cli_json_is_one_based() -> None:
    result = _run("--format", "json", str(FIXTURE), "excited", "state", "1")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["analysis_name"] == "excited-state"
    assert payload["data"]["state"] == 1
    assert payload["data"]["energy_ev"] == pytest.approx(4.0)


def test_transition_dipoles_cli_json_preserves_source_vector() -> None:
    result = _run("--format", "json", str(FIXTURE), "excited", "dipoles")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["analysis_name"] == "transition-dipoles"
    assert payload["data"]["dipoles"][0]["transition_dipole"] == pytest.approx([0.1, 0.2, 0.3])


def test_uvvis_cli_forwards_parameters_and_abbreviates_curve() -> None:
    result = _run(
        str(FIXTURE), "spectra", "uvvis", "--fwhm", "0.15", "--min", "3.5",
        "--max", "6.0", "--points", "101",
    )
    assert result.returncode == 0, result.stderr
    assert "UV-Vis Spectrum" in result.stdout
    assert "Gaussian FWHM: 0.15 eV" in result.stdout
    assert "Energy Grid Points: 101" in result.stdout
    assert "not absorbance/extinction" in result.stdout
    assert "energy_ev" not in result.stdout


def test_uvvis_json_keeps_complete_arrays() -> None:
    result = _run("--format", "json", str(FIXTURE), "spectra", "uvvis", "--points", "77")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["analysis_name"] == "uvvis-spectrum"
    assert len(payload["data"]["energy_ev"]) == 77
    assert len(payload["data"]["intensity"]) == 77
    assert payload["data"]["quantity"] == "oscillator_strength_broadened"


def test_excited_states_and_uvvis_export_row_oriented_csv(tmp_path: Path) -> None:
    states_csv = tmp_path / "states.csv"
    uv_csv = tmp_path / "uvvis.csv"
    states = _run(str(FIXTURE), "excited", "states", "--export", str(states_csv))
    uvvis = _run(str(FIXTURE), "spectra", "uvvis", "--points", "11", "--export", str(uv_csv))
    assert states.returncode == 0, states.stderr
    assert uvvis.returncode == 0, uvvis.stderr
    state_rows = list(csv.reader(states_csv.open(encoding="utf-8")))
    uv_rows = list(csv.reader(uv_csv.open(encoding="utf-8")))
    assert state_rows[0][:4] == ["job", "source_program", "method_family", "state"]
    assert len(state_rows) == 3
    assert uv_rows[0][0:2] in (["energy_ev", "intensity"], ["domain", "x"])


def test_uvvis_png_and_svg_export(tmp_path: Path) -> None:
    png = tmp_path / "uvvis.png"
    svg = tmp_path / "uvvis.svg"
    first = _run(str(FIXTURE), "spectra", "uvvis", "--points", "101", "--export", str(png), "--dpi", "200")
    second = _run(str(FIXTURE), "spectra", "uvvis", "--points", "101", "--export", str(svg))
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert png.read_bytes().startswith(b"\x89PNG")
    svg_text = svg.read_text(encoding="utf-8")
    assert "Excitation energy" in svg_text
    assert "oscillator-strength" in svg_text
    assert "openwfn" in svg_text.lower()
