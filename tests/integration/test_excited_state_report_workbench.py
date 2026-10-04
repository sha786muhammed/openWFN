import json
from pathlib import Path

import openwfn
from openwfn.reporting import build_report
from openwfn.workbench.export import export_workbench
from openwfn.workbench.payload import WorkbenchPayload

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "gaussian" / "excited" / "tddft_states.log"


def _embedded_manifest(text: str) -> dict:
    payload = text.split('<script id="openwfn-report" type="application/json">', 1)[1].split(
        "</script>", 1
    )[0]
    return json.loads(payload)


def test_excited_state_report_renders_table_and_inline_uvvis(tmp_path: Path) -> None:
    calculation = openwfn.load(FIXTURE)
    data = calculation.data.calculation
    assert data is not None
    output = tmp_path / "excited-report.html"

    build_report(
        data,
        analyses=("excited-states", "uvvis-spectrum"),
        output=output,
        report_format="html",
        command="openwfn tddft_states.log report build excited-report.html",
        parameters={"analyses": ["excited-states", "uvvis-spectrum"]},
        generated_at="2026-10-03T12:00:00Z",
    )

    text = output.read_text(encoding="utf-8")
    assert 'class="excited-state-table"' in text
    assert "Oscillator strength" in text
    assert 'data-analysis="uvvis-spectrum"' in text
    assert "Excitation energy (eV)" in text
    assert 'class="uvvis-stick-table"' in text
    assert "Validation status: <strong>Experimental</strong>" in text
    assert "http://" not in text and "https://" not in text


def test_excited_state_report_embedded_json_matches_python_results(tmp_path: Path) -> None:
    calculation = openwfn.load(FIXTURE)
    data = calculation.data.calculation
    assert data is not None
    output = tmp_path / "excited-parity.html"
    analyses = ("excited-states", "uvvis-spectrum")

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


def test_workbench_payload_reuses_excited_state_results() -> None:
    calculation = openwfn.load(FIXTURE)
    data = calculation.data.calculation
    assert data is not None

    properties = json.loads(WorkbenchPayload.from_calculation(data).to_json())["properties"]
    states = calculation.analyze("excited-states")
    uvvis = calculation.analyze("uvvis-spectrum")

    assert properties["excited-states"]["jobs"] == states.data["jobs"]
    assert properties["uvvis-spectrum"]["energy_ev"] == uvvis.data["energy_ev"]
    assert properties["uvvis-spectrum"]["intensity"] == uvvis.data["intensity"]
    assert properties["uvvis-spectrum"]["lines"] == uvvis.data["lines"]


def test_workbench_html_contains_excited_states_workspace(tmp_path: Path) -> None:
    calculation = openwfn.load(FIXTURE)
    data = calculation.data.calculation
    assert data is not None
    output = tmp_path / "workbench.html"

    export_workbench(data, output)

    text = output.read_text(encoding="utf-8")
    assert 'data-workspace="excited-states"' in text
    assert 'id="excited-state-controls"' in text
    assert 'id="excited-state-select"' in text
    assert 'id="uvvis-spectrum-svg"' in text
    assert "renderExcitedStateSpectrum" in text
    assert "selectExcitedState" in text
    assert "Oscillator strength" in text
    assert "source values" in text.lower()
