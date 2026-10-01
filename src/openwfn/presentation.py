"""Deterministic output renderers for typed command results."""

import csv
import io
import json
from typing import Any

from .app import CommandContext
from .results import ResultRecord


def _display_name(name: str) -> str:
    return name.replace("_", " ").title()


def _plain_value(key: str, value: Any, units: dict[str, str]) -> str:
    unit = units.get(key)
    return f"{value} {unit}" if unit else str(value)


def _summarize_arrays(value: Any) -> Any:
    """Abbreviate long arrays for human output, preserving nested diagnostics."""
    if isinstance(value, dict):
        return {key: _summarize_arrays(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        if len(value) > 8:
            return f"{len(value)} entries (use --verbose or --format json for full values)"
        return [_summarize_arrays(item) for item in value]
    return value


def render(result: ResultRecord, context: CommandContext) -> str:
    """Render a result without performing scientific calculations."""

    if context.format == "json":
        return json.dumps(result.as_dict(), indent=2, sort_keys=True) + "\n"

    if context.format == "csv":
        stream = io.StringIO()
        writer = csv.writer(stream, lineterminator="\n")
        headings = [
            f"{key} [{result.units[key]}]" if key in result.units else key for key in result.data
        ]
        writer.writerow([*headings, "validation_status"])
        writer.writerow([*result.data.values(), result.validation_status])
        return stream.getvalue()

    if result.kind == "viewer_export":
        lines = [f"Standalone molecule viewer exported to: {result.data['output']}"]
        if result.data.get("browser_opened"):
            lines.append("Viewer opened in your default browser.")
        else:
            lines.append("Use this HTML file directly or share it for download; no extra viewer assets are required.")
        lines.extend(result.warnings)
        return "\n".join(lines) + "\n"

    lines = [_display_name(result.kind)]
    for key, value in result.data.items():
        if key == "normal_termination":
            label = "Normal" if value is True else "Not normal" if value is False else "Unknown"
            lines.append(f"Source Job Termination: {label}")
            continue
        if result.kind == "output_properties" and not context.verbose:
            value = _summarize_arrays(value)
        lines.append(f"{_display_name(key)}: {_plain_value(key, value, result.units)}")
    lines.append(f"Analysis Validation Status: {result.validation_status}")
    lines.append(f"Result Status: {result.status}")
    source_format = result.provenance.get("source_format")
    if source_format == "fchk" or (
        context.input_path is not None and context.input_path.suffix.lower() in {".fchk", ".fch", ".chk"}
    ):
        lines.append("Source Calculation Status: Unknown from FCHK (convergence is not established)")
    if result.error is not None:
        lines.append(f"Error: {result.error.message}")
    lines.extend(f"Warning: {warning}" for warning in result.warnings)
    return "\n".join(lines) + "\n"
