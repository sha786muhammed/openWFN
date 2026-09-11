"""Validated exports for renderer-independent command results."""

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from ..results import ResultRecord


@dataclass(frozen=True, slots=True)
class ExportRequest:
    path: Path
    format: str
    overwrite: bool = False
    dpi: int = 300

    def __post_init__(self) -> None:
        normalized = self.format.lower().lstrip(".")
        if normalized not in {"csv", "json", "png", "svg"}:
            raise ValueError(f"Unsupported export format: {self.format}")
        if self.path.suffix.lower() != f".{normalized}":
            raise ValueError(
                f"Output extension {self.path.suffix or '(none)'} does not match {normalized} format"
            )
        if self.dpi < 72:
            raise ValueError("DPI must be at least 72")

    def ensure_writable(self) -> None:
        if self.path.exists() and not self.overwrite:
            raise FileExistsError(
                f"Output exists: {self.path}. Pass overwrite=True to replace it."
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)


def write_result_table(result: ResultRecord, request: ExportRequest) -> Path:
    normalized = request.format.lower().lstrip(".")
    if normalized not in {"json", "csv"}:
        raise ValueError("Result tables support JSON and CSV formats")
    request.ensure_writable()
    if normalized == "json":
        payload = {
            "data": result.data,
            "kind": result.kind,
            "units": result.units,
            "validation_status": result.validation_status,
        }
        request.path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return request.path
    with request.path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            [
                f"{key} [{result.units[key]}]" if key in result.units else key
                for key in result.data
            ]
            + ["validation_status"]
        )
        writer.writerow(
            [
                json.dumps(value, separators=(",", ":"))
                if isinstance(value, (list, dict, tuple))
                else value
                for value in result.data.values()
            ]
            + [result.validation_status]
        )
    return request.path
