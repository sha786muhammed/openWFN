import csv
import io
import json
from pathlib import Path

from openwfn.app import CommandContext, execute
from openwfn.presentation import render
from openwfn.results import ResultRecord


def _distance_result() -> ResultRecord:
    return ResultRecord(
        kind="distance",
        data={"atom_i": 1, "atom_j": 2, "value": 0.966598},
        units={"value": "angstrom"},
        validation_status="Stable",
    )


def test_json_output_is_deterministic_and_includes_units_and_status() -> None:
    output = render(_distance_result(), CommandContext(format="json"))

    assert json.loads(output) == {
        "analysis_name": "distance",
        "analysis_version": "1",
        "data": {"atom_i": 1, "atom_j": 2, "value": 0.966598},
        "elapsed_seconds": None,
        "error": None,
        "kind": "distance",
        "provenance": {},
        "schema_version": "1.0",
        "status": "success",
        "units": {"value": "angstrom"},
        "validation_status": "Stable",
        "warnings": [],
    }
    assert output.index('"analysis_name"') < output.index('"data"')


def test_csv_output_contains_unit_in_column_heading() -> None:
    output = render(_distance_result(), CommandContext(format="csv"))
    rows = list(csv.reader(io.StringIO(output)))

    assert rows == [
        ["atom_i", "atom_j", "value [angstrom]", "validation_status"],
        ["1", "2", "0.966598", "Stable"],
    ]


def test_plain_output_has_no_terminal_escape_codes() -> None:
    output = render(_distance_result(), CommandContext(format="plain", color=False))

    assert "Distance" in output
    assert "0.966598 angstrom" in output
    assert "\x1b[" not in output


def test_execute_writes_rendered_result_to_requested_output(tmp_path: Path) -> None:
    output = tmp_path / "distance.json"

    status = execute(
        _distance_result,
        CommandContext(output_path=output, format="json"),
    )

    assert status == 0
    assert json.loads(output.read_text(encoding="utf-8"))["kind"] == "distance"
