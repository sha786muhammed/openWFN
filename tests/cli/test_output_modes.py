import csv
import io
import json

from openwfn.app import CommandContext
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
        "data": {"atom_i": 1, "atom_j": 2, "value": 0.966598},
        "kind": "distance",
        "units": {"value": "angstrom"},
        "validation_status": "Stable",
    }
    assert output.index('"data"') < output.index('"kind"')


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
