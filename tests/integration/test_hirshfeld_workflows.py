import csv
from pathlib import Path

import pytest

from openwfn.analysis.registry import run_analysis
from openwfn.batch import _configuration_fingerprint, run_batch
from openwfn.exporters.tables import ExportRequest, write_result_table
from openwfn.parsers.gaussian.fchk import parse_fchk
from openwfn.reporting import build_report

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / "examples" / "water" / "water.fchk"
WATER_XYZ = ROOT / "examples" / "water" / "water.xyz"


def _reference():
    return run_analysis(parse_fchk(WATER), "hirshfeld")


def test_hirshfeld_csv_exports_one_row_per_atom(tmp_path: Path) -> None:
    reference = _reference()
    output = tmp_path / "hirshfeld.csv"

    write_result_table(reference, ExportRequest(output, "csv"))

    with output.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 3
    assert list(rows[0]) == [
        "atom_index",
        "element",
        "effective_nuclear_charge [e]",
        "electron_population [electron]",
        "charge [e]",
        "electron_count_residual [electron]",
        "charge_closure_residual [e]",
        "result_status",
        "validation_status",
    ]
    assert [row["element"] for row in rows] == ["O", "H", "H"]
    for row, atom in zip(rows, reference.data["atoms"], strict=True):
        assert int(row["atom_index"]) == atom["atom_index"]
        assert float(row["effective_nuclear_charge [e]"]) == pytest.approx(
            atom["effective_nuclear_charge"]
        )
        assert float(row["electron_population [electron]"]) == pytest.approx(
            atom["electron_population"]
        )
        assert float(row["charge [e]"]) == pytest.approx(atom["charge"])
        assert row["result_status"] == reference.status
        assert row["validation_status"] == reference.validation_status


def test_hirshfeld_reports_render_atomic_table_and_diagnostics(tmp_path: Path) -> None:
    data = parse_fchk(WATER)
    html = tmp_path / "hirshfeld.html"
    markdown = tmp_path / "hirshfeld.md"

    build_report(
        data,
        analyses=("hirshfeld",),
        output=html,
        report_format="html",
        command="openwfn water.fchk report build hirshfeld.html --analyses hirshfeld",
        parameters={"analyses": ["hirshfeld"]},
        generated_at="2026-10-03T00:00:00Z",
    )
    build_report(
        data,
        analyses=("hirshfeld",),
        output=markdown,
        report_format="markdown",
        command="openwfn water.fchk report build hirshfeld.md --analyses hirshfeld",
        parameters={"analyses": ["hirshfeld"]},
        generated_at="2026-10-03T00:00:00Z",
    )

    html_text = html.read_text(encoding="utf-8")
    md_text = markdown.read_text(encoding="utf-8")
    for text in (html_text, md_text):
        assert "Hirshfeld Population" in text
        assert "Atomic Populations and Charges" in text
        assert "Closure Diagnostics" in text
        assert "Reference Library" in text
        assert "openwfn-hirshfeld-proatoms-v1" in text
        assert "Charge Closure Residual" in text
    assert "Effective Nuclear Charge (e)" in html_text
    assert "| Atom | Element | Effective Nuclear Charge (e)" in md_text


def test_hirshfeld_batch_uses_registry_defaults_and_records_unsupported_input(
    tmp_path: Path,
) -> None:
    reference = _reference()
    manifest = run_batch(
        inputs=[WATER, WATER_XYZ],
        operation=None,
        analyses=("hirshfeld",),
        workers=1,
        output_dir=tmp_path / "batch",
    )

    assert manifest.analyses == ("hirshfeld",)
    assert manifest.configuration_fingerprint == _configuration_fingerprint(("hirshfeld",))
    assert [record.status for record in manifest.records] == ["success", "error"]
    assert manifest.records[0].results[0].data == reference.data
    failed = manifest.records[1].results[0]
    assert failed.status == "failed"
    assert failed.error is not None
    assert failed.error.category == "DataUnavailableError"
    assert "basis" in failed.error.message.lower() or "density" in failed.error.message.lower()

    resumed = run_batch(
        inputs=[WATER, WATER_XYZ],
        operation=None,
        analyses=("hirshfeld",),
        workers=1,
        output_dir=tmp_path / "batch",
        resume=True,
    )
    assert resumed.records[0].skipped is True
    assert resumed.records[0].results[0].data == reference.data
    assert resumed.records[1].skipped is False
