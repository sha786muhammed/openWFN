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


def _write_excited_states_csv(result: ResultRecord, request: ExportRequest) -> Path:
    columns = (
        "job",
        "source_program",
        "method_family",
        "method_detail",
        "state",
        "source_state",
        "energy_ev",
        "wavelength_nm",
        "oscillator_strength",
        "multiplicity",
        "symmetry",
        "transition_kind",
    )
    with request.path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(columns)
        for job in result.data.get("jobs", []):
            for state in job.get("states", []):
                writer.writerow(
                    [
                        job.get("job"),
                        job.get("source_program"),
                        job.get("method_family"),
                        job.get("method_detail"),
                        state.get("state"),
                        state.get("source_state"),
                        state.get("energy_ev"),
                        state.get("wavelength_nm"),
                        state.get("oscillator_strength"),
                        state.get("multiplicity"),
                        state.get("symmetry"),
                        state.get("transition_kind"),
                    ]
                )
    return request.path


def _write_transition_dipoles_csv(result: ResultRecord, request: ExportRequest) -> Path:
    with request.path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("job", "state", "source_state", "energy_ev", "dipole_x", "dipole_y", "dipole_z", "unit"))
        for row in result.data.get("dipoles", []):
            vector = row.get("transition_dipole") or (None, None, None)
            writer.writerow(
                (
                    result.data.get("job"),
                    row.get("state"),
                    row.get("source_state"),
                    row.get("energy_ev"),
                    *vector,
                    row.get("unit"),
                )
            )
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
    if result.kind == "vibrational_modes":
        return _write_vibrational_modes_csv(result, request)
    if result.kind == "excited_states":
        return _write_excited_states_csv(result, request)
    if result.kind == "transition_dipoles":
        return _write_transition_dipoles_csv(result, request)
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
