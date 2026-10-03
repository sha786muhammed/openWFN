import csv
import json
from pathlib import Path

import pytest

from openwfn.cli import main

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "gaussian" / "excited" / "tddft_states.log"


def test_excited_states_cli_human_output(capsys) -> None:
    status = main([str(FIXTURE), "excited", "states"])
    captured = capsys.readouterr()
    assert status == 0
    assert "Excited States" in captured.out
    assert "Energy (eV)" in captured.out
    assert "Experimental" in captured.out


def test_excited_state_cli_json(capsys) -> None:
    status = main(["--format", "json", str(FIXTURE), "excited", "state", "1"])
    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["kind"] == "excited_state"
    assert payload["data"]["state"] == 1
    assert payload["data"]["energy_ev"] == pytest.approx(4.0)


def test_excited_states_cli_csv_is_row_oriented(capsys) -> None:
    status = main(["--format", "csv", str(FIXTURE), "excited", "states"])
    rows = list(csv.reader(capsys.readouterr().out.splitlines()))
    assert status == 0
    assert rows[0][:5] == ["job", "source_program", "method_family", "state", "source_state"]
    assert len(rows) == 3


def test_uvvis_cli_json_and_export(tmp_path: Path, capsys) -> None:
    output = tmp_path / "uvvis.svg"
    status = main([
        "--format",
        "json",
        str(FIXTURE),
        "spectra",
        "uvvis",
        "--fwhm",
        "0.2",
        "--points",
        "101",
        "--export",
        str(output),
    ])
    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["kind"] == "uvvis_spectrum"
    assert payload["data"]["broadening"]["fwhm_ev"] == pytest.approx(0.2)
    assert len(payload["data"]["energy_ev"]) == 101
    assert output.read_text(encoding="utf-8").startswith("<?xml")


def test_uvvis_cli_rejects_input_without_oscillator_strengths(capsys) -> None:
    source = Path(__file__).resolve().parents[1] / "fixtures" / "qchem" / "excited" / "eom.out"
    status = main([str(source), "spectra", "uvvis", "--input-format", "qchemlog"])
    captured = capsys.readouterr()
    assert status != 0
    assert "oscillator" in captured.err.lower() or "oscillator" in captured.out.lower()
