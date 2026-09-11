from pathlib import Path

from openwfn.parsers.gaussian.fchk import parse_fchk
from openwfn.workbench.export import export_workbench

WATER = Path(__file__).resolve().parents[2] / "examples" / "water" / "water.fchk"


def test_workbench_contains_interactive_measurement_contract(tmp_path: Path) -> None:
    output = tmp_path / "workbench.html"
    export_workbench(parse_fchk(WATER), output)
    text = output.read_text(encoding="utf-8")

    for identifier in (
        "measurement-controls",
        "measurement-selection",
        "measurement-result",
        "measurement-reset",
    ):
        assert f'id="{identifier}"' in text
    for mode in ("distance", "angle", "dihedral"):
        assert f'data-measurement="{mode}"' in text
    for function in (
        "calculateDistance",
        "calculateAngle",
        "calculateDihedral",
        "selectMeasurementAtom",
        "resetMeasurement",
    ):
        assert f"function {function}" in text
    assert "viewer.setClickable" in text
    assert "Å" in text
    assert "°" in text


def test_measurement_controls_have_accessible_labels_and_keyboard_focus(tmp_path: Path) -> None:
    output = tmp_path / "workbench.html"
    export_workbench(parse_fchk(WATER), output)
    text = output.read_text(encoding="utf-8")

    assert 'aria-label="Measurement type"' in text
    assert 'aria-live="polite"' in text
    assert ".measure-button:focus-visible" in text


def test_workbench_embeds_scientific_surface_controls_and_metadata(tmp_path: Path) -> None:
    output = tmp_path / "workbench.html"
    export_workbench(parse_fchk(WATER), output)
    text = output.read_text(encoding="utf-8")

    for identifier in ("surface-controls", "field-select", "isovalue", "surface-legend"):
        assert f'id="{identifier}"' in text
    assert "HOMO" in text
    assert "Total electron density" in text
    assert "Mulliken ESP" in text
    assert "electron/bohr^3" in text
    assert "hartree/e" in text
    assert "addIsosurface" in text
    assert "removeAllSurfaces" in text
    assert "validation_status" in text
