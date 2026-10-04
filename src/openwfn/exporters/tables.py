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


def _write_hirshfeld_csv(result: ResultRecord, path: Path) -> None:
    atoms = result.data.get("atoms")
    diagnostics = result.data.get("diagnostics")
    if not isinstance(atoms, list) or not isinstance(diagnostics, dict):
        raise ValueError("Hirshfeld CSV export requires atomic rows and diagnostics")

    fieldnames = [
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
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for atom in atoms:
            if not isinstance(atom, dict):
                raise ValueError("Hirshfeld CSV export found a malformed atomic record")
            writer.writerow(
                {
                    "atom_index": atom.get("atom_index"),
                    "element": atom.get("element"),
                    "effective_nuclear_charge [e]": atom.get("effective_nuclear_charge"),
                    "electron_population [electron]": atom.get("electron_population"),
                    "charge [e]": atom.get("charge"),
                    "electron_count_residual [electron]": diagnostics.get(
                        "electron_count_residual"
                    ),
                    "charge_closure_residual [e]": diagnostics.get("charge_closure_residual"),
                    "result_status": result.status,
                    "validation_status": result.validation_status,
                }
            )


def _write_vibrational_modes_csv(result: ResultRecord, request: ExportRequest) -> Path:
    columns = (
        "mode",
        "frequency_cm1",
        "imaginary",
        "symmetry",
        "reduced_mass_amu",
        "force_constant_mdyne_per_angstrom",
        "ir_intensity_km_mol",
        "raman_activity_a4_amu",
    )
    with request.path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(columns)
        for row in result.data.get("modes", []):
            writer.writerow([row.get(column) for column in columns])
    return request.path


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
    if result.kind == "hirshfeld_population":
        _write_hirshfeld_csv(result, request.path)
        return request.path
    if result.kind == "vibrational_modes":
        return _write_vibrational_modes_csv(result, request)
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
