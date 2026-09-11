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
        payload = {
            "data": result.data,
            "kind": result.kind,
            "units": result.units,
            "validation_status": result.validation_status,
        }
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"

    if context.format == "csv":
        stream = io.StringIO()
        writer = csv.writer(stream, lineterminator="\n")
        headings = [
            f"{key} [{result.units[key]}]" if key in result.units else key for key in result.data
        ]
        writer.writerow([*headings, "validation_status"])
        writer.writerow([*result.data.values(), result.validation_status])
        return stream.getvalue()

    lines = [_display_name(result.kind)]
    for key, value in result.data.items():
        lines.append(f"{_display_name(key)}: {_plain_value(key, value, result.units)}")
    lines.append(f"Status: {result.validation_status}")
    return "\n".join(lines) + "\n"
