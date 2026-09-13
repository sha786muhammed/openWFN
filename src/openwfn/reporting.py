"""Self-contained, reproducible HTML and Markdown research reports."""

import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Iterable

from . import __version__
from .analysis.registry import run_analysis_safe
from .model import CalculationData
from .results import ResultRecord


def _sections(data: CalculationData, analyses: Iterable[str]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for name in analyses:
        result = run_analysis_safe(data, name)
        if result.status == "failed":
            sections.append(
                {
                    "name": name,
                    "status": "Unavailable",
                    "validation_status": "Unsupported",
                    "error": result.error.message if result.error else "Unknown analysis failure",
                }
            )
        else:
            sections.append(
                {
                    "name": name,
                    "status": "Available",
                    "validation_status": result.validation_status,
                    "analysis_version": result.analysis_version,
                    "data": result.data,
                    "units": result.units,
                    "warnings": list(result.warnings),
                }
            )
    return sections


def _title(name: str) -> str:
    titles = {
        "frontier": "Frontier Orbitals",
        "beta-frontier": "Beta Frontier",
        "mulliken": "Mulliken Population",
        "lowdin": "Lowdin Population",
    }
    if name in titles:
        return titles[name]
    return name.replace("-", " ").replace("_", " ").title()


def _html(manifest: dict[str, Any]) -> str:
    sections = []
    for section in manifest["sections"]:
        heading = escape(_title(section["name"]))
        if section["status"] == "Unavailable":
            body = f'<p class="unavailable"><strong>Unavailable:</strong> {escape(section["error"])}</p>'
        else:
            rows = "".join(
                f"<tr><th>{escape(_title(key))}</th><td>{escape(str(value))}</td>"
                f"<td>{escape(section['units'].get(key, ''))}</td></tr>"
                for key, value in section["data"].items()
            )
            body = f"<table>{rows}</table>"
        sections.append(
            f'<section><h2>{heading}</h2><p>Validation status: '
            f'<strong>{escape(section["validation_status"])}</strong></p>{body}</section>'
        )
    encoded = json.dumps(manifest, indent=2, sort_keys=True).replace("<", "\\u003c")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>openWFN Research Report</title><style>
body{{font:16px/1.55 system-ui,sans-serif;margin:0;color:#172033;background:#f4f7fb}}
main{{max-width:960px;margin:auto;padding:2rem}}header,section{{background:white;padding:1.4rem;margin:1rem 0;border:1px solid #dce3ee;border-radius:10px}}
h1,h2{{color:#123d6a}}table{{border-collapse:collapse;width:100%}}th,td{{text-align:left;padding:.55rem;border-bottom:1px solid #e5eaf1}}th{{width:34%}}.unavailable{{color:#8b2e2e}}
</style></head><body><main><header><h1>openWFN Research Report</h1>
<p>Generated: {escape(manifest['generated_at'])}</p><p>openWFN version: {escape(manifest['openwfn_version'])}</p>
<p>Input SHA-256: <code>{escape(manifest['input']['sha256'])}</code></p></header>
{''.join(sections)}<section><h2>Reproducibility</h2><p>Command: <code>{escape(manifest['command'])}</code></p></section>
<script id="openwfn-report" type="application/json">{encoded}</script></main></body></html>
"""


def _markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# openWFN Research Report", "", f"Generated: {manifest['generated_at']}  ",
        f"openWFN version: {manifest['openwfn_version']}  ",
        f"Input SHA-256: `{manifest['input']['sha256']}`", "",
    ]
    for section in manifest["sections"]:
        lines.extend((f"## {_title(section['name'])}", ""))
        if section["status"] == "Unavailable":
            lines.extend((f"**Unavailable:** {section['error']}", ""))
            continue
        lines.extend((f"Validation status: **{section['validation_status']}**", ""))
        for key, value in section["data"].items():
            unit = section["units"].get(key, "")
            lines.append(f"- {_title(key)}: {value}{f' {unit}' if unit else ''}")
        lines.append("")
    lines.extend(("## Reproducibility", "", f"Command: `{manifest['command']}`", ""))
    return "\n".join(lines)


def build_report(
    data: CalculationData,
    analyses: Iterable[str],
    output: Path,
    report_format: str,
    command: str,
    parameters: dict[str, Any],
    *,
    generated_at: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Build a self-contained research report without network dependencies."""

    if report_format not in {"html", "markdown"}:
        raise ValueError("report_format must be 'html' or 'markdown'")
    expected_suffix = ".html" if report_format == "html" else ".md"
    if output.suffix.lower() != expected_suffix:
        raise ValueError(f"{report_format} reports require a {expected_suffix} output path")
    if output.exists() and not overwrite:
        raise FileExistsError(f"Output exists: {output}. Pass overwrite=True to replace it.")
    provenance = data.molecule.provenance
    manifest = {
        "schema_version": "1.0",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "openwfn_version": __version__,
        "command": command,
        "parameters": dict(sorted(parameters.items())),
        "input": {
            "path": provenance.source_path if provenance else "Unavailable",
            "sha256": provenance.sha256 if provenance else "Unavailable",
            "source_program": data.molecule.metadata.source_program,
            "method": data.molecule.metadata.method,
            "basis": data.molecule.metadata.basis,
        },
        "sections": _sections(data, analyses),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    text = _html(manifest) if report_format == "html" else _markdown(manifest)
    output.write_text(text, encoding="utf-8")
    return output


def build_report_record(
    data: CalculationData,
    analyses: tuple[str, ...],
    output: Path,
    report_format: str,
    command: str,
    overwrite: bool = False,
) -> ResultRecord:
    path = build_report(
        data,
        analyses,
        output,
        report_format,
        command,
        {"analyses": list(analyses), "format": report_format},
        overwrite=overwrite,
    )
    return ResultRecord(
        kind="research_report",
        data={"output": str(path), "format": report_format, "analyses": list(analyses)},
        validation_status="Stable",
    )
