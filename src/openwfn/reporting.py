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
                    "result_status": result.status,
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
        "hirshfeld": "Hirshfeld Population",
    }
    if name in titles:
        return titles[name]
    return name.replace("-", " ").replace("_", " ").title()


def _hirshfeld_html(section: dict[str, Any]) -> str:
    data = section["data"]
    atoms = data.get("atoms", [])
    diagnostics = data.get("diagnostics", {})
    quadrature = data.get("quadrature", {})
    reference = data.get("reference_library", {})
    warnings = "".join(f"<li>{escape(w)}</li>" for w in section.get("warnings", []))

    atom_rows = "".join(
        "<tr>"
        f"<td>{escape(str(atom.get('atom_index', '')))}</td>"
        f"<td>{escape(str(atom.get('element', '')))}</td>"
        f"<td>{escape(str(atom.get('effective_nuclear_charge', '')))}</td>"
        f"<td>{escape(str(atom.get('electron_population', '')))}</td>"
        f"<td>{escape(str(atom.get('charge', '')))}</td>"
        "</tr>"
        for atom in atoms
        if isinstance(atom, dict)
    )
    diagnostic_rows = "".join(
        f"<tr><th>{escape(_title(key))}</th><td>{escape(str(value))}</td>"
        f"<td>{escape(section['units'].get(key, ''))}</td></tr>"
        for key, value in diagnostics.items()
    )
    quadrature_rows = "".join(
        f"<tr><th>{escape(_title(key))}</th><td>{escape(str(value))}</td>"
        f"<td>{escape(section['units'].get(key, ''))}</td></tr>"
        for key, value in quadrature.items()
    )
    reference_rows = "".join(
        f"<tr><th>{escape(_title(key))}</th><td>{escape(str(value))}</td><td></td></tr>"
        for key, value in reference.items()
    )

    return (
        f"<p>Result status: {escape(section.get('result_status', 'success'))}</p>"
        f"<ul>{warnings}</ul>"
        "<h3>Atomic Populations and Charges</h3>"
        "<table><thead><tr><th>Atom</th><th>Element</th>"
        "<th>Effective Nuclear Charge (e)</th><th>Electron Population (electron)</th>"
        f"<th>Charge (e)</th></tr></thead><tbody>{atom_rows}</tbody></table>"
        "<h3>Closure Diagnostics</h3>"
        f"<table>{diagnostic_rows}</table>"
        "<h3>Quadrature</h3>"
        f"<table>{quadrature_rows}</table>"
        "<h3>Reference Library</h3>"
        f"<table>{reference_rows}</table>"
        f"<p>Density source: {escape(str(data.get('density_source', 'Unavailable')))}</p>"
    )


def _generic_html(section: dict[str, Any]) -> str:
    rows = "".join(
        f"<tr><th>{escape(_title(key))}</th><td>{escape(str(value))}</td>"
        f"<td>{escape(section['units'].get(key, ''))}</td></tr>"
        for key, value in section["data"].items()
    )
    warnings = "".join(f"<li>{escape(w)}</li>" for w in section.get("warnings", []))
    return (
        f"<p>Result status: {escape(section.get('result_status', 'success'))}</p>"
        f"<ul>{warnings}</ul><table>{rows}</table>"
    )


def _html(manifest: dict[str, Any]) -> str:
    sections = []
    for section in manifest["sections"]:
        heading = escape(_title(section["name"]))
        if section["status"] == "Unavailable":
            body = f'<p class="unavailable"><strong>Unavailable:</strong> {escape(section["error"])}</p>'
        elif section["name"] == "hirshfeld":
            body = _hirshfeld_html(section)
        else:
            body = _generic_html(section)
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
h1,h2{{color:#123d6a}}table{{border-collapse:collapse;width:100%;margin:.75rem 0 1.25rem}}th,td{{text-align:left;padding:.55rem;border-bottom:1px solid #e5eaf1}}.unavailable{{color:#8b2e2e}}
</style></head><body><main><header><h1>openWFN Research Report</h1>
<p>Generated: {escape(manifest['generated_at'])}</p><p>openWFN version: {escape(manifest['openwfn_version'])}</p>
<p>Input SHA-256: <code>{escape(manifest['input']['sha256'])}</code></p></header>
{''.join(sections)}<section><h2>Reproducibility</h2><p>Command: <code>{escape(manifest['command'])}</code></p></section>
<script id="openwfn-report" type="application/json">{encoded}</script></main></body></html>
"""


def _hirshfeld_markdown(section: dict[str, Any]) -> list[str]:
    data = section["data"]
    atoms = data.get("atoms", [])
    diagnostics = data.get("diagnostics", {})
    quadrature = data.get("quadrature", {})
    reference = data.get("reference_library", {})
    lines = [
        "### Atomic Populations and Charges",
        "",
        "| Atom | Element | Effective Nuclear Charge (e) | Electron Population (electron) | Charge (e) |",
        "| ---: | :--- | ---: | ---: | ---: |",
    ]
    for atom in atoms:
        if not isinstance(atom, dict):
            continue
        lines.append(
            f"| {atom.get('atom_index', '')} | {atom.get('element', '')} | "
            f"{atom.get('effective_nuclear_charge', '')} | {atom.get('electron_population', '')} | "
            f"{atom.get('charge', '')} |"
        )
    lines.extend(("", "### Closure Diagnostics", ""))
    for key, value in diagnostics.items():
        unit = section["units"].get(key, "")
        lines.append(f"- {_title(key)}: {value}{f' {unit}' if unit else ''}")
    lines.extend(("", "### Quadrature", ""))
    for key, value in quadrature.items():
        unit = section["units"].get(key, "")
        lines.append(f"- {_title(key)}: {value}{f' {unit}' if unit else ''}")
    lines.extend(("", "### Reference Library", ""))
    for key, value in reference.items():
        lines.append(f"- {_title(key)}: {value}")
    lines.extend(("", f"Density source: {data.get('density_source', 'Unavailable')}", ""))
    return lines


def _markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# openWFN Research Report",
        "",
        f"Generated: {manifest['generated_at']}  ",
        f"openWFN version: {manifest['openwfn_version']}  ",
        f"Input SHA-256: `{manifest['input']['sha256']}`",
        "",
    ]
    for section in manifest["sections"]:
        lines.extend((f"## {_title(section['name'])}", ""))
        if section["status"] == "Unavailable":
            lines.extend((f"**Unavailable:** {section['error']}", ""))
            continue
        lines.extend((f"Validation status: **{section['validation_status']}**", ""))
        lines.extend((f"Result status: **{section.get('result_status', 'success')}**", ""))
        for warning in section.get("warnings", []):
            lines.extend((f"Warning: {warning}", ""))
        if section["name"] == "hirshfeld":
            lines.extend(_hirshfeld_markdown(section))
            continue
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
    results = [run_analysis_safe(data, name) for name in analyses]
    warnings = tuple(dict.fromkeys(w for result in results for w in result.warnings))
    return ResultRecord(
        kind="research_report",
        data={"output": str(path), "format": report_format, "analyses": list(analyses)},
        validation_status="Stable",
        status="partial" if any(result.status != "success" for result in results) else "success",
        warnings=warnings,
    )
