import json
from pathlib import Path

import pytest

from openwfn import __version__
from openwfn.parsers.gaussian.fchk import parse_fchk
from openwfn.reporting import build_report

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / "examples" / "water" / "water.fchk"


def test_html_report_contains_reproducibility_and_analysis_sections(tmp_path: Path) -> None:
    data = parse_fchk(WATER)
    output = tmp_path / "water-report.html"

    result = build_report(
        data,
        analyses=("summary", "frontier", "mulliken"),
        output=output,
        report_format="html",
        command="openwfn water.fchk report build water-report.html",
        parameters={"analyses": ["summary", "frontier", "mulliken"]},
        generated_at="2026-09-11T12:00:00Z",
    )

    text = result.read_text(encoding="utf-8")
    assert result == output
    assert "openWFN Research Report" in text
    assert __version__ in text
    assert data.molecule.provenance.sha256 in text
    assert "2026-09-11T12:00:00Z" in text
    assert "Frontier Orbitals" in text
    assert "Mulliken Population" in text
    assert "Validation status" in text
    assert "http://" not in text and "https://" not in text


def test_markdown_report_records_unavailable_analysis_instead_of_omitting_it(tmp_path: Path) -> None:
    data = parse_fchk(WATER)
    output = tmp_path / "water-report.md"

    build_report(
        data,
        analyses=("beta-frontier",),
        output=output,
        report_format="markdown",
        command="fixture",
        parameters={},
        generated_at="2026-09-11T12:00:00Z",
    )

    text = output.read_text(encoding="utf-8")
    assert "## Beta Frontier" in text
    assert "Unavailable" in text
    assert "Beta orbitals are not available" in text


def test_report_refuses_to_replace_existing_output_without_overwrite(tmp_path: Path) -> None:
    data = parse_fchk(WATER)
    output = tmp_path / "report.html"
    output.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="Output exists"):
        build_report(
            data,
            analyses=("summary",),
            output=output,
            report_format="html",
            command="fixture",
            parameters={},
            generated_at="2026-09-11T12:00:00Z",
        )

    assert output.read_text(encoding="utf-8") == "keep"


def test_report_manifest_json_is_deterministically_embedded(tmp_path: Path) -> None:
    data = parse_fchk(WATER)
    output = tmp_path / "report.html"
    build_report(
        data,
        analyses=("summary",),
        output=output,
        report_format="html",
        command="fixture",
        parameters={"z": 2, "a": 1},
        generated_at="2026-09-11T12:00:00Z",
    )

    text = output.read_text(encoding="utf-8")
    payload = text.split('<script id="openwfn-report" type="application/json">', 1)[1].split(
        "</script>", 1
    )[0]
    manifest = json.loads(payload)
    assert list(manifest["parameters"]) == ["a", "z"]
    assert manifest["schema_version"] == "1.0"
