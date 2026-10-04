"""Hirshfeld results remain identical across workflow and presentation layers."""

import asyncio
import csv
import json
from pathlib import Path

import pytest

from openwfn.api import load
from openwfn.batch import run_batch
from openwfn.exporters.tables import ExportRequest, write_result_table
from openwfn.reporting import build_report

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / "examples" / "water" / "water.fchk"


def test_hirshfeld_csv_is_one_atom_per_row(tmp_path: Path) -> None:
    result = load(WATER).analyze("hirshfeld")
    output = tmp_path / "hirshfeld.csv"

    write_result_table(result, ExportRequest(output, "csv"))

    rows = list(csv.DictReader(output.read_text(encoding="utf-8").splitlines()))
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
    for row, atom in zip(rows, result.data["atoms"], strict=True):
        assert int(row["atom_index"]) == atom["atom_index"]
        assert row["element"] == atom["element"]
        assert float(row["electron_population [electron]"]) == pytest.approx(
            atom["electron_population"]
        )
        assert float(row["charge [e]"]) == pytest.approx(atom["charge"])
        assert row["result_status"] == result.status
        assert row["validation_status"] == result.validation_status


def test_hirshfeld_report_renders_atomic_table_and_preserves_manifest(tmp_path: Path) -> None:
    calc = load(WATER)
    reference = calc.analyze("hirshfeld")
    output = tmp_path / "hirshfeld.html"

    build_report(
        calc.data.calculation,
        ("hirshfeld",),
        output,
        "html",
        "parity",
        {},
        generated_at="2026-10-03T12:00:00Z",
    )

    text = output.read_text(encoding="utf-8")
    assert "Hirshfeld Population" in text
    assert "Atom" in text and "Element" in text
    assert "Electron Population" in text and "Charge" in text
    assert "Reference Library" in text
    payload = text.split('<script id="openwfn-report" type="application/json">', 1)[1].split(
        "</script>", 1
    )[0]
    manifest = json.loads(payload)
    assert manifest["sections"][0]["data"] == reference.data


def test_hirshfeld_batch_uses_registry_result_without_recalculation_contract(tmp_path: Path) -> None:
    reference = load(WATER).analyze("hirshfeld")

    batch = run_batch([WATER], None, 1, tmp_path / "batch", analyses=("hirshfeld",))

    record = batch.records[0].results[0]
    assert record.data == reference.data
    assert record.status == reference.status
    assert record.validation_status == reference.validation_status
    assert record.analysis_name == reference.analysis_name
    assert record.analysis_version == reference.analysis_version


def test_hirshfeld_mcp_uses_same_registry_result(tmp_path: Path) -> None:
    pytest.importorskip("mcp")
    from mcp import Client

    from openwfn.mcp_server import create_server

    reference = load(WATER).analyze("hirshfeld")

    async def check() -> None:
        async with Client(create_server(WATER.parent)) as client:
            listing = (await client.call_tool("list_analyses", {})).structured_content
            assert "hirshfeld" in listing["analyses"]
            response = await client.call_tool(
                "run_analysis", {"path": WATER.name, "analysis": "hirshfeld"}
            )
            record = response.structured_content
            assert record["data"] == reference.data
            assert record["status"] == reference.status
            assert record["validation_status"] == reference.validation_status
            assert record["analysis_name"] == reference.analysis_name
            assert record["analysis_version"] == reference.analysis_version

    asyncio.run(check())
