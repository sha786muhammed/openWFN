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
        lines.append(f"{_display_name(key)}: {_plain_value(key, value, result.units)}")
    lines.append(f"Status: {result.validation_status}")
    if result.status != "success":
        lines.append(f"Result: {result.status}")
    if result.error is not None:
        lines.append(f"Error: {result.error.message}")
    lines.extend(f"Warning: {warning}" for warning in result.warnings)
    return "\n".join(lines) + "\n"
