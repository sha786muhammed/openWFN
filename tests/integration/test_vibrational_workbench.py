import json
from pathlib import Path

import openwfn

from openwfn.workbench.export import export_workbench
from openwfn.workbench.payload import WorkbenchPayload

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "gaussian" / "vibrations" / "water_freq.log"
NO_VECTORS = ROOT / "tests" / "fixtures" / "gaussian" / "vibrations" / "no_vectors.log"


def test_workbench_payload_reuses_registered_spectroscopy_results() -> None:
    calculation = openwfn.load(FIXTURE)
    data = calculation.data.calculation
    assert data is not None

    payload = WorkbenchPayload.from_calculation(data)
    properties = json.loads(payload.to_json())["properties"]

    vibrations = calculation.analyze("vibrations")
    ir = calculation.analyze("ir-spectrum")
    raman = calculation.analyze("raman-spectrum")
    assert properties["vibrations"]["modes"] == vibrations.data["modes"]
    assert properties["vibrations"]["displacements_available"] is True
    assert properties["ir-spectrum"]["frequency_cm1"] == ir.data["frequency_cm1"]
    assert properties["ir-spectrum"]["intensity"] == ir.data["intensity"]
    assert properties["raman-spectrum"]["frequency_cm1"] == raman.data["frequency_cm1"]
    assert properties["raman-spectrum"]["intensity"] == raman.data["intensity"]
    assert properties["normal_modes"]["available"] is True
    assert len(properties["normal_modes"]["modes"]) == vibrations.data["mode_count"]
    assert properties["normal_modes"]["modes"][0]["displacements"] == calculation.analyze(
        "normal-mode", mode=1
    ).data["displacements"]


def test_workbench_payload_marks_missing_vectors_unavailable() -> None:
    calculation = openwfn.load(NO_VECTORS)
    data = calculation.data.calculation
    assert data is not None

    properties = json.loads(WorkbenchPayload.from_calculation(data).to_json())["properties"]

    assert properties["vibrations"]["displacements_available"] is False
    assert properties["normal_modes"] == {
        "available": False,
        "modes": [],
        "message": "Normal-mode displacement vectors are unavailable for this source file.",
    }


def test_workbench_html_contains_vibrations_workspace_and_controls(tmp_path: Path) -> None:
    calculation = openwfn.load(FIXTURE)
    data = calculation.data.calculation
    assert data is not None
    output = tmp_path / "workbench.html"

    export_workbench(data, output)

    text = output.read_text(encoding="utf-8")
    assert 'data-workspace="vibrations"' in text
    assert 'id="vibration-controls"' in text
    assert 'id="vibration-mode-select"' in text
    assert 'id="vibration-amplitude"' in text
    assert 'id="ir-spectrum-svg"' in text
    assert 'id="raman-spectrum-svg"' in text
    assert "Normal-mode displacement vectors" in text
    assert "renderVibrationalSpectrum" in text
    assert "renderNormalMode" in text
