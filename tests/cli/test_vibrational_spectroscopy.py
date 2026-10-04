import csv
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from openwfn.analysis.registry import run_analysis
from openwfn.app import CommandContext
from openwfn.parsers.gaussian.output import parse_gaussian_output
from openwfn.presentation import render

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "gaussian" / "vibrations"
WATER = FIXTURES / "water_freq.log"


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "openwfn.cli", *arguments],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        check=False,
    )


def test_vibrations_cli_renders_compact_mode_table() -> None:
    result = _run(str(WATER), "vibrations")

    assert result.returncode == 0, result.stderr
    assert "Vibrational Modes" in result.stdout
    assert "Mode" in result.stdout
    assert "Frequency" in result.stdout
    assert "1595.1234" in result.stdout
    assert "3755.6789" in result.stdout
    assert "Analysis Validation Status: Experimental" in result.stdout
    assert "displacements" not in result.stdout.lower()


def test_vibrations_mode_cli_routes_to_normal_mode_json() -> None:
    result = _run("--format", "json", str(WATER), "vibrations", "mode", "2")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["analysis_name"] == "normal-mode"
    assert payload["kind"] == "normal_mode"
    assert payload["data"]["mode"] == 2
    assert payload["data"]["frequency_cm1"] == pytest.approx(3657.4567)
    assert len(payload["data"]["displacements"]) == 3


def test_ir_spectrum_cli_forwards_parameters_and_abbreviates_curve() -> None:
    result = _run(
        str(WATER), "spectra", "ir", "--fwhm", "12", "--min", "1500",
        "--max", "3900", "--points", "101",
    )

    assert result.returncode == 0, result.stderr
    assert "IR Vibrational Spectrum" in result.stdout
    assert "FWHM: 12.0 cm^-1" in result.stdout
    assert "Grid Points: 101" in result.stdout
    assert "1595.1234" in result.stdout
    assert "100.0" in result.stdout
    assert "frequency_cm1" not in result.stdout
    assert "[1500.0" not in result.stdout


def test_spectrum_json_keeps_complete_curve_arrays() -> None:
    result = _run("--format", "json", str(WATER), "spectra", "raman", "--points", "77")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["analysis_name"] == "raman-spectrum"
    assert payload["data"]["quantity"] == "raman_activity"
    assert len(payload["data"]["frequency_cm1"]) == 77
    assert len(payload["data"]["intensity"]) == 77


def test_human_csv_renderers_are_row_oriented() -> None:
    calculation = parse_gaussian_output(WATER)
    modes = run_analysis(calculation, "vibrations")
    spectrum = run_analysis(calculation, "ir-spectrum", points=5)

    mode_rows = list(csv.reader(io.StringIO(render(modes, CommandContext(format="csv")))))
    spectrum_rows = list(csv.reader(io.StringIO(render(spectrum, CommandContext(format="csv")))))

    assert mode_rows[0][:4] == ["mode", "frequency_cm1", "imaginary", "symmetry"]
    assert len(mode_rows) == 4
    assert mode_rows[1][0:2] == ["1", "1595.1234"]
    assert "[" not in mode_rows[1][0]

    assert spectrum_rows[0] == ["frequency_cm1", "intensity"]
    assert len(spectrum_rows) == 6
    assert all(len(row) == 2 for row in spectrum_rows)


def test_vibrations_and_spectra_export_row_oriented_csv(tmp_path: Path) -> None:
    modes_csv = tmp_path / "modes.csv"
    ir_csv = tmp_path / "ir.csv"

    modes = _run(str(WATER), "vibrations", "--export", str(modes_csv))
    ir = _run(str(WATER), "spectra", "ir", "--points", "11", "--export", str(ir_csv))

    assert modes.returncode == 0, modes.stderr
    assert ir.returncode == 0, ir.stderr
    mode_rows = list(csv.reader(modes_csv.open(encoding="utf-8")))
    ir_rows = list(csv.reader(ir_csv.open(encoding="utf-8")))
    assert len(mode_rows) == 4
    assert mode_rows[0][0:2] == ["mode", "frequency_cm1"]
    assert len(ir_rows) == 12
    assert ir_rows[0] == ["frequency_cm1", "intensity"]


def test_spectrum_png_and_svg_export_are_publication_ready(tmp_path: Path) -> None:
    png = tmp_path / "ir.png"
    svg = tmp_path / "raman.svg"

    ir = _run(
        str(WATER), "spectra", "ir", "--points", "101", "--export", str(png), "--dpi", "200"
    )
    raman = _run(
        str(WATER), "spectra", "raman", "--points", "101", "--export", str(svg)
    )

    assert ir.returncode == 0, ir.stderr
    assert raman.returncode == 0, raman.stderr
    assert png.read_bytes().startswith(b"\x89PNG")
    svg_text = svg.read_text(encoding="utf-8")
    assert "Wavenumber (cm" in svg_text
    assert "Raman activity" in svg_text
    assert "openwfn" in svg_text.lower()


def test_missing_raman_cli_fails_without_invented_values() -> None:
    result = _run(str(FIXTURES / "no_raman.log"), "spectra", "raman")

    assert result.returncode != 0
    assert "raman" in (result.stdout + result.stderr).lower()
