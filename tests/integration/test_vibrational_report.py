import json
from pathlib import Path

import openwfn
from openwfn.reporting import build_report

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "gaussian" / "vibrations" / "water_freq.log"


def _embedded_manifest(text: str) -> dict:
    payload = text.split('<script id="openwfn-report" type="application/json">', 1)[1].split(
        "</script>", 1
    )[0]
    return json.loads(payload)


def test_vibrational_report_renders_mode_table_and_inline_spectra(tmp_path: Path) -> None:
    calculation = openwfn.load(FIXTURE)
    assert calculation.data.calculation is not None
    output = tmp_path / "vibrational-report.html"

    build_report(
        calculation.data.calculation,
        analyses=("vibrations", "ir-spectrum", "raman-spectrum"),
        output=output,
        report_format="html",
        command="openwfn water_freq.log report build vibrational-report.html",
        parameters={"analyses": ["vibrations", "ir-spectrum", "raman-spectrum"]},
        generated_at="2026-10-03T12:00:00Z",
    )

    text = output.read_text(encoding="utf-8")
    assert 'class="vibrational-mode-table"' in text
    assert "Frequency (cm^-1)" in text
    assert "IR intensity (km/mol)" in text
    assert "Raman activity (angstrom^4/amu)" in text
    assert 'data-analysis="ir-spectrum"' in text
    assert 'data-analysis="raman-spectrum"' in text
    assert "Wavenumber (cm^-1)" in text
    assert "<svg" in text
    assert "Validation status: <strong>Experimental</strong>" in text
    offline_text = text.replace("http://www.w3.org/2000/svg", "")
    assert "http://" not in offline_text and "https://" not in offline_text


def test_vibrational_report_embedded_json_matches_python_results(tmp_path: Path) -> None:
    calculation = openwfn.load(FIXTURE)
    data = calculation.data.calculation
    assert data is not None
    output = tmp_path / "parity.html"
    analyses = ("vibrations", "ir-spectrum", "raman-spectrum")

    build_report(
        data,
        analyses=analyses,
        output=output,
        report_format="html",
        command="parity",
        parameters={},
        generated_at="2026-10-03T12:00:00Z",
    )

    manifest = _embedded_manifest(output.read_text(encoding="utf-8"))
    sections = {section["name"]: section for section in manifest["sections"]}
    for analysis in analyses:
        reference = calculation.analyze(analysis)
        assert sections[analysis]["data"] == reference.data
        assert sections[analysis]["units"] == reference.units
        assert sections[analysis]["validation_status"] == reference.validation_status
        assert sections[analysis]["warnings"] == list(reference.warnings)
