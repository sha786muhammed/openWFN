"""Deterministic output renderers for typed command results."""

import csv
import io
import json
from typing import Any

from .app import CommandContext
from .constants import Z_TO_SYMBOL
from .results import ResultRecord


def _display_name(name: str) -> str:
    return name.replace("_", " ").title()


def _plain_value(key: str, value: Any, units: dict[str, str]) -> str:
    if value is None:
        return 'Unavailable'
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


def _csv_vibrational_modes(result: ResultRecord) -> str:
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
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
    writer.writerow(columns)
    for row in result.data.get("modes", []):
        writer.writerow([row.get(column) for column in columns])
    return stream.getvalue()


def _csv_vibrational_spectrum(result: ResultRecord) -> str:
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("frequency_cm1", "intensity"))
    for frequency, intensity in zip(
        result.data.get("frequency_cm1", []), result.data.get("intensity", []), strict=True
    ):
        writer.writerow((frequency, intensity))
    return stream.getvalue()


def _csv_excited_states(result: ResultRecord) -> str:
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    columns = (
        "job",
        "source_program",
        "method_family",
        "state",
        "source_state",
        "energy_ev",
        "wavelength_nm",
        "oscillator_strength",
        "multiplicity",
        "symmetry",
    )
    writer.writerow(columns)
    for job in result.data.get("jobs", []):
        for state in job.get("states", []):
            writer.writerow(
                (
                    job.get("job"),
                    job.get("source_program"),
                    job.get("method_family"),
                    state.get("state"),
                    state.get("source_state"),
                    state.get("energy_ev"),
                    state.get("wavelength_nm"),
                    state.get("oscillator_strength"),
                    state.get("multiplicity"),
                    state.get("symmetry"),
                )
            )
    return stream.getvalue()


def _csv_uvvis(result: ResultRecord) -> str:
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("energy_ev", "intensity"))
    writer.writerows(
        zip(result.data.get("energy_ev", []), result.data.get("intensity", []), strict=True)
    )
    return stream.getvalue()


def _status_lines(result: ResultRecord, context: CommandContext) -> list[str]:
    lines = [
        f"Analysis Validation Status: {result.validation_status}",
        f"Result Status: {result.status}",
    ]
    source_format = result.provenance.get("source_format")
    if source_format == "fchk" or (
        context.input_path is not None
        and context.input_path.suffix.lower() in {".fchk", ".fch", ".chk"}
    ):
        lines.append("Source Calculation Status: Unknown from FCHK (convergence is not established)")
    if result.error is not None:
        lines.append(f"Error: {result.error.message}")
    lines.extend(f"Warning: {warning}" for warning in result.warnings)
    return lines


def _render_vibrational_modes(result: ResultRecord, context: CommandContext) -> str:
    lines = [
        "Vibrational Modes",
        "Mode  Frequency (cm^-1)  Imaginary  Symmetry  IR (km/mol)  Raman activity (A^4/amu)",
    ]
    for row in result.data.get("modes", []):
        symmetry = row.get("symmetry") or "-"
        ir = "-" if row.get("ir_intensity_km_mol") is None else str(row["ir_intensity_km_mol"])
        raman = (
            "-"
            if row.get("raman_activity_a4_amu") is None
            else str(row["raman_activity_a4_amu"])
        )
        lines.append(
            f"{row['mode']:>4}  {row['frequency_cm1']:>17.4f}  "
            f"{str(row['imaginary']):>9}  {symmetry:<8}  {ir:>11}  {raman:>24}"
        )
    lines.extend(
        (
            f"IR Available: {result.data.get('ir_available')}",
            f"Raman Available: {result.data.get('raman_available')}",
            f"Normal-mode Vectors Available: {result.data.get('displacements_available')}",
        )
    )
    lines.extend(_status_lines(result, context))
    return "\n".join(lines) + "\n"


def _render_vibrational_spectrum(result: ResultRecord, context: CommandContext) -> str:
    spectrum_type = str(result.data.get("spectrum_type", "spectrum"))
    is_ir = spectrum_type == "ir"
    title = "IR Vibrational Spectrum" if is_ir else "Raman Vibrational Spectrum"
    strength_key = "intensity" if is_ir else "activity"
    strength_label = "IR Intensity (km/mol)" if is_ir else "Raman Activity (A^4/amu)"
    lines = [title, f"Mode  Frequency (cm^-1)  {strength_label}  Imaginary"]
    for row in result.data.get("lines", []):
        strength = str(row[strength_key])
        lines.append(
            f"{row['mode']:>4}  {row['frequency_cm1']:>17.4f}  "
            f"{strength:>23}  {str(row['imaginary']):>9}"
        )
    broadening = result.data.get("broadening", {})
    lines.append(f"FWHM: {broadening.get('fwhm_cm1')} cm^-1")
    lines.append(f"Grid Points: {len(result.data.get('frequency_cm1', []))}")
    frequency_range = result.data.get("frequency_range_cm1")
    if frequency_range:
        lines.append(f"Frequency Range: {frequency_range[0]} to {frequency_range[1]} cm^-1")
    lines.extend(_status_lines(result, context))
    return "\n".join(lines) + "\n"


def _render_excited_states(result: ResultRecord, context: CommandContext) -> str:
    lines = [
        "Excited States",
        "Job  State  Energy (eV)  Wavelength (nm)  f          Mult  Symmetry  Method",
    ]
    for job in result.data.get("jobs", []):
        for state in job.get("states", []):
            wavelength = state.get("wavelength_nm")
            strength = state.get("oscillator_strength")
            lines.append(
                f"{job['job']:>3}  {state['state']:>5}  {state['energy_ev']:>11.6f}  "
                f"{('-' if wavelength is None else f'{wavelength:.3f}'):>15}  "
                f"{('-' if strength is None else f'{strength:.6g}'):>9}  "
                f"{('-' if state.get('multiplicity') is None else state['multiplicity']):>4}  "
                f"{(state.get('symmetry') or '-'):>8}  {job.get('method_family', '-')}"
            )
    lines.extend(_status_lines(result, context))
    return "\n".join(lines) + "\n"


def _render_uvvis(result: ResultRecord, context: CommandContext) -> str:
    lines = [
        "UV-Vis Spectrum",
        "State  Energy (eV)  Wavelength (nm)  Oscillator Strength  Curve",
    ]
    for row in result.data.get("lines", []):
        wavelength = row.get("wavelength_nm")
        strength = row.get("oscillator_strength")
        curve_status = "included" if row.get("eligible") else f"excluded: {row.get('exclusion_reason')}"
        lines.append(
            f"{row['state']:>5}  {row['energy_ev']:>11.6f}  "
            f"{('-' if wavelength is None else f'{wavelength:.3f}'):>15}  "
            f"{('-' if strength is None else f'{strength:.6g}'):>19}  {curve_status}"
        )
    broadening = result.data.get("broadening", {})
    lines.append(f"Gaussian FWHM: {broadening.get('fwhm_ev')} eV")
    lines.append(f"Energy Grid Points: {len(result.data.get('energy_ev', []))}")
    if result.data.get("wavelength_nm"):
        lines.append(f"Wavelength Grid Points: {len(result.data['wavelength_nm'])}")
    lines.append("Curve Quantity: simulated oscillator-strength profile (not absorbance/extinction)")
    lines.extend(_status_lines(result, context))
    return "\n".join(lines) + "\n"


def render(result: ResultRecord, context: CommandContext) -> str:
    """Render a result without performing scientific calculations."""

    if context.format == "json":
        return json.dumps(result.as_dict(), indent=2, sort_keys=True) + "\n"

    if context.format == "csv":
        if result.kind == "vibrational_modes":
            return _csv_vibrational_modes(result)
        if result.kind == "vibrational_spectrum":
            return _csv_vibrational_spectrum(result)
        if result.kind == "excited_states":
            return _csv_excited_states(result)
        if result.kind == "uvvis_spectrum":
            return _csv_uvvis(result)
        stream = io.StringIO()
        writer = csv.writer(stream, lineterminator="\n")
        headings = [
            f"{key} [{result.units[key]}]" if key in result.units else key for key in result.data
        ]
        writer.writerow([*headings, "validation_status"])
        writer.writerow([*result.data.values(), result.validation_status])
        return stream.getvalue()

    if result.kind == 'overview':
        sections = ['Input overview']
        for payload in result.data.get('results', {}).values():
            sections.append(render(ResultRecord.from_dict(payload), context).rstrip())
        sections.append('Next actions: ' + ', '.join(result.data.get('next_actions', [])))
        sections.extend(_status_lines(result, context))
        return '\n\n'.join(sections) + '\n'

    if result.kind == "viewer_export":
        lines = [f"Standalone molecule viewer exported to: {result.data['output']}"]
        if result.data.get("browser_opened"):
            lines.append("Viewer opened in your default browser.")
        else:
            lines.append("Use this HTML file directly or share it for download; no extra viewer assets are required.")
        lines.extend(result.warnings)
        return "\n".join(lines) + "\n"

    if result.kind == "vibrational_modes" and not context.verbose:
        return _render_vibrational_modes(result, context)
    if result.kind == "vibrational_spectrum" and not context.verbose:
        return _render_vibrational_spectrum(result, context)
    if result.kind == "excited_states" and not context.verbose:
        return _render_excited_states(result, context)
    if result.kind == "uvvis_spectrum" and not context.verbose:
        return _render_uvvis(result, context)

    lines = [_display_name(result.kind)]
    table_keys = set()
    if result.kind == "orbital_composition" and not context.verbose:
        lines.append("Atom  Element  Contribution (%)")
        for row in result.data.get("atom_contributions", []):
            lines.append(f"{row['atom_number']:>4}  {Z_TO_SYMBOL.get(row['atomic_number'], '?'):<7}  {row['percent']:>16.4f}")
        table_keys.add("atom_contributions")
    if result.kind == "mayer_bond_order" and not context.verbose:
        lines.append("Atom 1  Atom 2  Mayer bond order")
        for row in result.data.get("pairs", []):
            lines.append(f"{row['atom1']:>6}  {row['atom2']:>6}  {row['bond_order']:>16.6f}")
        table_keys.add("pairs")
    for key, value in result.data.items():
        if key in table_keys:
            continue
        if key == "normal_termination":
            label = "Normal" if value is True else "Not normal" if value is False else "Unknown"
            lines.append(f"Source Job Termination: {label}")
            continue
        if not context.verbose:
            value = _summarize_arrays(value)
        lines.append(f"{_display_name(key)}: {_plain_value(key, value, result.units)}")
    lines.extend(_status_lines(result, context))
    return "\n".join(lines) + "\n"
