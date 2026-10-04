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
        "vibrations": "Vibrational Modes",
        "ir-spectrum": "IR Spectrum",
        "raman-spectrum": "Raman Spectrum",
    }
    if name in titles:
        return titles[name]
    return name.replace("-", " ").replace("_", " ").title()


def _display_optional(value: object) -> str:
    return "—" if value is None else str(value)


def _vibrational_mode_table(section: dict[str, Any]) -> str:
    rows = []
    for mode in section["data"].get("modes", []):
        rows.append(
            "<tr>"
            f"<td>{escape(str(mode['mode']))}</td>"
            f"<td>{escape(str(mode['frequency_cm1']))}</td>"
            f"<td>{escape(_display_optional(mode.get('symmetry')))}</td>"
            f"<td>{escape(_display_optional(mode.get('reduced_mass_amu')))}</td>"
            f"<td>{escape(_display_optional(mode.get('force_constant_mdyne_per_angstrom')))}</td>"
            f"<td>{escape(_display_optional(mode.get('ir_intensity_km_mol')))}</td>"
            f"<td>{escape(_display_optional(mode.get('raman_activity_a4_amu')))}</td>"
            f"<td>{'yes' if mode.get('imaginary') else 'no'}</td>"
            "</tr>"
        )
    return (
        '<div class="table-scroll"><table class="vibrational-mode-table">'
        "<thead><tr><th>Mode</th><th>Frequency (cm^-1)</th><th>Symmetry</th>"
        "<th>Reduced mass (amu)</th><th>Force constant (mDyne/angstrom)</th>"
        "<th>IR intensity (km/mol)</th><th>Raman activity (angstrom^4/amu)</th>"
        "<th>Imaginary</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def _spectrum_svg(section: dict[str, Any]) -> str:
    data = section["data"]
    frequencies = [float(value) for value in data.get("frequency_cm1", [])]
    intensities = [float(value) for value in data.get("intensity", [])]
    if len(frequencies) < 2 or len(frequencies) != len(intensities):
        return '<p class="unavailable">Spectrum curve is unavailable.</p>'

    width, height = 760.0, 300.0
    left, right, top, bottom = 72.0, 22.0, 20.0, 54.0
    plot_width = width - left - right
    plot_height = height - top - bottom
    x_min, x_max = min(frequencies), max(frequencies)
    y_min = min(0.0, min(intensities))
    y_max = max(intensities)
    if x_max == x_min:
        x_max = x_min + 1.0
    if y_max == y_min:
        y_max = y_min + 1.0

    def point(x_value: float, y_value: float) -> str:
        x = left + (x_value - x_min) / (x_max - x_min) * plot_width
        y = top + (y_max - y_value) / (y_max - y_min) * plot_height
        return f"{x:.2f},{y:.2f}"

    polyline = " ".join(point(x, y) for x, y in zip(frequencies, intensities, strict=True))
    spectrum_type = data.get("spectrum_type")
    is_ir = spectrum_type == "ir"
    ylabel = "IR intensity (km/mol)" if is_ir else "Raman activity (angstrom^4/amu)"
    analysis = "ir-spectrum" if is_ir else "raman-spectrum"
    sticks = []
    for line in data.get("lines", []):
        if line.get("imaginary"):
            continue
        strength = line.get("intensity") if is_ir else line.get("activity")
        if strength is None:
            continue
        x = left + (float(line["frequency_cm1"]) - x_min) / (x_max - x_min) * plot_width
        y = top + (y_max - float(strength)) / (y_max - y_min) * plot_height
        baseline = top + (y_max - 0.0) / (y_max - y_min) * plot_height
        sticks.append(
            f'<line x1="{x:.2f}" y1="{baseline:.2f}" x2="{x:.2f}" y2="{y:.2f}" '
            'class="spectrum-stick" />'
        )
    return (
        f'<svg class="spectrum-plot" data-analysis="{analysis}" viewBox="0 0 760 300" '
        'role="img" aria-label="Vibrational spectrum">'
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" '
        f'y2="{top + plot_height}" class="axis" />'
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" class="axis" />'
        f'<polyline points="{polyline}" class="spectrum-curve" />'
        + "".join(sticks)
        + f'<text x="{left + plot_width / 2:.1f}" y="287" text-anchor="middle">Wavenumber (cm^-1)</text>'
        + f'<text x="18" y="{top + plot_height / 2:.1f}" text-anchor="middle" '
        'transform="rotate(-90 18 133)">'
        + escape(ylabel)
        + "</text>"
        + f'<text x="{left}" y="{top + plot_height + 19:.1f}" class="tick-label">{x_min:.1f}</text>'
        + f'<text x="{left + plot_width}" y="{top + plot_height + 19:.1f}" text-anchor="end" '
        f'class="tick-label">{x_max:.1f}</text>'
        + "</svg>"
    )


def _spectrum_table(section: dict[str, Any]) -> str:
    data = section["data"]
    is_ir = data.get("spectrum_type") == "ir"
    strength_key = "intensity" if is_ir else "activity"
    strength_label = "IR intensity (km/mol)" if is_ir else "Raman activity (angstrom^4/amu)"
    rows = "".join(
        "<tr>"
        f"<td>{escape(str(line['mode']))}</td>"
        f"<td>{escape(str(line['frequency_cm1']))}</td>"
        f"<td>{escape(str(line[strength_key]))}</td>"
        f"<td>{'yes' if line.get('imaginary') else 'no'}</td>"
        "</tr>"
        for line in data.get("lines", [])
    )
    return (
        '<div class="table-scroll"><table class="spectrum-stick-table"><thead><tr>'
        f"<th>Mode</th><th>Frequency (cm^-1)</th><th>{escape(strength_label)}</th>"
        "<th>Imaginary</th></tr></thead><tbody>"
        + rows
        + "</tbody></table></div>"
    )


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


def _available_html(section: dict[str, Any]) -> str:
    if section["name"] == "hirshfeld":
        return _hirshfeld_html(section)
    warnings = "".join(f"<li>{escape(w)}</li>" for w in section.get("warnings", []))
    prefix = (
        f"<p>Result status: {escape(section.get('result_status', 'success'))}</p>"
        + (f'<ul class="warnings">{warnings}</ul>' if warnings else "")
    )
    if section["name"] == "vibrations":
        data = section["data"]
        summary = (
            '<div class="spectroscopy-summary">'
            f"<span>Modes: {escape(str(data.get('mode_count', 0)))}</span>"
            f"<span>Imaginary: {escape(str(data.get('imaginary_mode_count', 0)))}</span>"
            f"<span>IR: {'available' if data.get('ir_available') else 'unavailable'}</span>"
            f"<span>Raman: {'available' if data.get('raman_available') else 'unavailable'}</span>"
            "</div>"
        )
        return prefix + summary + _vibrational_mode_table(section)
    if section["name"] in {"ir-spectrum", "raman-spectrum"}:
        broadening = section["data"].get("broadening", {})
        details = (
            '<p class="spectrum-details">Gaussian visualization · FWHM '
            f"{escape(str(broadening.get('fwhm_cm1', '—')))} cm^-1 · source sticks preserved</p>"
        )
        return prefix + details + _spectrum_svg(section) + _spectrum_table(section)
    rows = "".join(
        f"<tr><th>{escape(_title(key))}</th><td>{escape(str(value))}</td>"
        f"<td>{escape(section['units'].get(key, ''))}</td></tr>"
        for key, value in section["data"].items()
    )
    return prefix + f"<table>{rows}</table>"


def _html(manifest: dict[str, Any]) -> str:
    sections = []
    for section in manifest["sections"]:
        heading = escape(_title(section["name"]))
        if section["status"] == "Unavailable":
            body = f'<p class="unavailable"><strong>Unavailable:</strong> {escape(section["error"])}</p>'
        else:
            body = _available_html(section)
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
.table-scroll{{overflow-x:auto}}.vibrational-mode-table th,.spectrum-stick-table th{{width:auto;white-space:nowrap}}.spectroscopy-summary{{display:flex;flex-wrap:wrap;gap:.65rem 1.2rem;margin:.8rem 0 1rem;color:#40516b}}.spectrum-details{{color:#40516b}}.spectrum-plot{{display:block;width:100%;height:auto;margin:1rem 0 1.25rem;background:#fbfcfe;border:1px solid #e5eaf1;border-radius:8px}}.axis{{stroke:#607089;stroke-width:1}}.spectrum-curve{{fill:none;stroke:#123d6a;stroke-width:2}}.spectrum-stick{{stroke:#7890ad;stroke-width:1;opacity:.55}}.tick-label{{font-size:12px;fill:#607089}}.warnings{{color:#7b4e12}}
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
