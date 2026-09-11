import csv
import json
from pathlib import Path

import matplotlib.image as mpimg
import pytest

from openwfn.analysis.orbitals import FrontierOrbitals
from openwfn.exporters.images import write_frontier_diagram
from openwfn.exporters.tables import ExportRequest, write_result_table
from openwfn.results import ResultRecord


def _result() -> ResultRecord:
    return ResultRecord(
        kind="population",
        data={"atom": [1, 2], "charge": [-0.4, 0.4]},
        units={"charge": "e"},
        validation_status="Stable",
    )


def test_json_table_export_is_deterministic_and_contains_units(tmp_path: Path) -> None:
    output = tmp_path / "population.json"

    write_result_table(_result(), ExportRequest(output, "json"))

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert list(payload) == ["data", "kind", "units", "validation_status"]
    assert payload["units"]["charge"] == "e"


def test_csv_table_export_places_units_in_headers(tmp_path: Path) -> None:
    output = tmp_path / "population.csv"

    write_result_table(_result(), ExportRequest(output, "csv"))

    rows = list(csv.reader(output.read_text(encoding="utf-8").splitlines()))
    assert rows[0] == ["atom", "charge [e]", "validation_status"]
    assert json.loads(rows[1][0]) == [1, 2]


def test_export_request_checks_extension_and_overwrite(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="extension"):
        ExportRequest(tmp_path / "wrong.csv", "json")
    output = tmp_path / "exists.json"
    output.write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError, match="Output exists"):
        write_result_table(_result(), ExportRequest(output, "json"))


def test_frontier_svg_contains_accessible_scientific_metadata(tmp_path: Path) -> None:
    output = tmp_path / "frontier.svg"
    frontier = FrontierOrbitals(4, 5, -0.4, 0.2, 0.6, 16.3268, "restricted")

    write_frontier_diagram(frontier, ExportRequest(output, "svg"))

    text = output.read_text(encoding="utf-8")
    assert "openWFN frontier orbital energy diagram" in text
    assert "Energy (eV)" in text
    assert "HOMO" in text and "LUMO" in text


def test_frontier_png_honors_requested_dpi(tmp_path: Path) -> None:
    output = tmp_path / "frontier.png"
    frontier = FrontierOrbitals(4, 5, -0.4, 0.2, 0.6, 16.3268, "restricted")

    write_frontier_diagram(frontier, ExportRequest(output, "png", dpi=200))

    image = mpimg.imread(output)
    assert image.shape[0] >= 700
    assert image.shape[1] >= 900
