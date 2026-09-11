from pathlib import Path

import pytest

from openwfn.parsers.gaussian.fchk import parse_fchk
from openwfn.workbench.export import export_workbench

WATER = Path(__file__).resolve().parents[2] / "examples" / "water" / "water.fchk"


def test_workbench_export_is_offline_and_contains_required_shell(tmp_path: Path) -> None:
    output = tmp_path / "water-workbench.html"

    export_workbench(parse_fchk(WATER), output, title='Water <study>')

    text = output.read_text(encoding="utf-8")
    assert "Water &lt;study&gt;" in text
    assert 'id="workflow-sidebar"' in text
    assert 'id="viewer"' in text
    assert 'id="property-panel"' in text
    assert 'id="status-line"' in text
    assert 'id="openwfn-workbench"' in text
    assert "3Dmol" in text
    assert '<script src="http' not in text
    assert '<link href="http' not in text
    for workspace in ("Structure", "Orbitals", "Density", "ESP", "Measurements"):
        assert f'data-workspace="{workspace.lower()}"' in text


def test_workbench_export_protects_existing_file(tmp_path: Path) -> None:
    output = tmp_path / "workbench.html"
    output.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="Output exists"):
        export_workbench(parse_fchk(WATER), output)

    assert output.read_text(encoding="utf-8") == "keep"
