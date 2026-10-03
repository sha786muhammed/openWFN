"""Tabular and publication-style export of shared spectrum ResultRecords."""

import csv
import json
from pathlib import Path

from ..results import ResultRecord
from .tables import ExportRequest


def _write_vibrational_spectrum(
    result: ResultRecord, path: Path, request: ExportRequest, dpi: int
) -> Path:
    frequency = result.data["frequency_cm1"]
    intensity = result.data["intensity"]
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(result.as_dict(), indent=2) + "\n", encoding="utf-8")
        return path
    if path.suffix.lower() == ".csv":
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["frequency_cm1", "intensity"])
            writer.writerows(zip(frequency, intensity, strict=True))
        return path

    from matplotlib.figure import Figure

    spectrum_type = result.data.get("spectrum_type")
    is_ir = spectrum_type == "ir"
    ylabel = "IR intensity (km/mol)" if is_ir else "Raman activity (angstrom^4/amu)"
    figure = Figure(figsize=(6.4, 4.2), layout="constrained")
    axis = figure.subplots()
    axis.plot(frequency, intensity, lw=1.4)
    for line in result.data.get("lines", []):
        if line.get("imaginary"):
            continue
        strength = line.get("intensity") if is_ir else line.get("activity")
        if strength is not None:
            axis.vlines(line["frequency_cm1"], 0.0, strength, lw=0.7, alpha=0.45)
    axis.set(xlabel="Wavenumber (cm$^{-1}$)", ylabel=ylabel)
    axis.spines[["top", "right"]].set_visible(False)
    axis.tick_params(direction="in")
    axis.margins(x=0)
    metadata = None
    if path.suffix.lower() == ".svg":
        metadata = {
            "Description": json.dumps(
                {
                    "software": "openWFN",
                    "analysis": result.analysis_name,
                    "validation_status": result.validation_status,
                    "warnings": result.warnings,
                    "provenance": result.provenance,
                },
                sort_keys=True,
            )
        }
    figure.savefig(path, dpi=dpi, metadata=metadata)
    figure.clear()
    return path


def _write_uvvis_spectrum(result: ResultRecord, path: Path, dpi: int) -> Path:
    energy = result.data["energy_ev"]
    intensity = result.data["intensity"]
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(result.as_dict(), indent=2) + "\n", encoding="utf-8")
        return path
    if path.suffix.lower() == ".csv":
        wavelength = result.data.get("wavelength_nm")
        wavelength_intensity = result.data.get("wavelength_intensity")
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            if wavelength is None:
                writer.writerow(["energy_ev", "intensity"])
                writer.writerows(zip(energy, intensity, strict=True))
            else:
                writer.writerow(["domain", "x", "intensity"])
                writer.writerows(("energy_ev", x, y) for x, y in zip(energy, intensity, strict=True))
                writer.writerows(
                    ("wavelength_nm", x, y)
                    for x, y in zip(wavelength, wavelength_intensity, strict=True)
                )
        return path

    from matplotlib.figure import Figure

    figure = Figure(figsize=(6.4, 4.2), layout="constrained")
    axis = figure.subplots()
    axis.plot(energy, intensity, lw=1.4)
    for line in result.data.get("lines", []):
        strength = line.get("oscillator_strength")
        if line.get("eligible") and strength is not None:
            axis.vlines(line["energy_ev"], 0.0, strength, lw=0.7, alpha=0.45)
    axis.set(xlabel="Excitation energy (eV)", ylabel="Relative oscillator-strength profile")
    axis.spines[["top", "right"]].set_visible(False)
    axis.tick_params(direction="in")
    axis.margins(x=0)
    metadata = None
    if path.suffix.lower() == ".svg":
        metadata = {
            "Description": json.dumps(
                {
                    "software": "openWFN",
                    "analysis": result.analysis_name,
                    "validation_status": result.validation_status,
                    "warnings": result.warnings,
                    "provenance": result.provenance,
                    "quantity": result.data.get("quantity"),
                },
                sort_keys=True,
            )
        }
    figure.savefig(path, dpi=dpi, metadata=metadata)
    figure.clear()
    return path


def write_spectrum(
    result: ResultRecord,
    path: str | Path,
    *,
    overwrite: bool = False,
    dpi: int = 300,
) -> Path:
    """Write an orbital, vibrational, or UV-Vis spectrum without recalculating it."""

    if result.status == "failed" or result.kind not in {
        "orbital_dos",
        "orbital_pdos",
        "vibrational_spectrum",
        "uvvis_spectrum",
    }:
        raise ValueError("spectrum export requires a usable spectrum result")
    path = Path(path)
    request = ExportRequest(path, path.suffix.lstrip("."), overwrite, dpi)
    if path.suffix.lower() not in {".csv", ".json", ".png", ".svg"}:
        raise ValueError("spectrum supports CSV, JSON, PNG or SVG")
    request.ensure_writable()

    if result.kind == "vibrational_spectrum":
        return _write_vibrational_spectrum(result, path, request, dpi)
    if result.kind == "uvvis_spectrum":
        return _write_uvvis_spectrum(result, path, dpi)

    series = {
        "total_dos": result.data["total_dos"],
        **result.data["channels"],
        **result.data.get("projections", {}),
    }
    energy = result.data["energy_ev"]
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(result.as_dict(), indent=2) + "\n", encoding="utf-8")
    elif path.suffix.lower() == ".csv":
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["energy_ev", *series])
            for i, value in enumerate(energy):
                writer.writerow([value, *(values[i] for values in series.values())])
    else:
        from matplotlib.figure import Figure

        figure = Figure(figsize=(6.4, 4.2), layout="constrained")
        axis = figure.subplots()
        for label, values in series.items():
            axis.plot(energy, values, lw=1.3, label=label)
        axis.set(xlabel="Orbital energy (eV)", ylabel="Orbital DOS (orbitals/eV)")
        axis.spines[["top", "right"]].set_visible(False)
        if len(series) <= 12:
            axis.legend(frameon=False, fontsize=8)
        axis.tick_params(direction="in")
        axis.margins(x=0)
        metadata = (
            {
                "Description": json.dumps(
                    {
                        "analysis": result.analysis_name,
                        "validation_status": result.validation_status,
                        "warnings": result.warnings,
                        "provenance": result.provenance,
                    },
                    sort_keys=True,
                )
            }
            if path.suffix.lower() == ".svg"
            else None
        )
        figure.savefig(path, dpi=dpi, metadata=metadata)
        figure.clear()
    return path
