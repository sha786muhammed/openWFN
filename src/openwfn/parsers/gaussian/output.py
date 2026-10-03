"""Conservative native parser for Gaussian output and vibrational records."""

import re
from hashlib import sha256
from pathlib import Path
from typing import Any

from ...model import Atom, CalculationData, CalculationMetadata, Molecule, Provenance
from ...vibrational import VibrationalMode, VibrationalRecord

_SCF_ENERGY = re.compile(r"SCF Done:\s+E\([^)]+\)\s*=\s*([-+0-9.DEde]+)")
_CHARGE_MULTIPLICITY = re.compile(
    r"Charge\s*=\s*(-?\d+)\s+Multiplicity\s*=\s*(\d+)", re.IGNORECASE
)


def _float(value: str) -> float:
    return float(value.replace("D", "E").replace("d", "e"))


def _metadata(lines: list[str]) -> CalculationMetadata:
    route_lines = [line.strip() for line in lines if line.lstrip().startswith("#")]
    route = " ".join(route_lines) if route_lines else None
    method: str | None = None
    basis: str | None = None
    if route:
        method_basis = next((token for token in route.split() if "/" in token), None)
        if method_basis:
            method, basis = method_basis.split("/", maxsplit=1)

    energy: float | None = None
    for line in lines:
        match = _SCF_ENERGY.search(line)
        if match:
            energy = _float(match.group(1))

    return CalculationMetadata(
        source_program="Gaussian",
        route=route,
        method=method,
        basis=basis,
        energy_hartree=energy,
        terminated_normally=any("Normal termination of Gaussian" in line for line in lines),
    )


def _charge_and_multiplicity(lines: list[str]) -> tuple[int, int] | None:
    result: tuple[int, int] | None = None
    for line in lines:
        match = _CHARGE_MULTIPLICITY.search(line)
        if match:
            result = (int(match.group(1)), int(match.group(2)))
    return result


def _is_dash(line: str) -> bool:
    stripped = line.strip()
    return len(stripped) >= 5 and set(stripped) == {"-"}


def _parse_orientation(
    lines: list[str], start: int
) -> tuple[tuple[int, tuple[float, float, float]], ...] | None:
    index = start + 1
    dash_count = 0
    while index < len(lines):
        if _is_dash(lines[index]):
            dash_count += 1
            if dash_count == 2:
                index += 1
                break
        index += 1
    if dash_count < 2:
        return None

    rows: list[tuple[int, tuple[float, float, float]]] = []
    while index < len(lines) and not _is_dash(lines[index]):
        tokens = lines[index].split()
        if len(tokens) >= 6:
            try:
                atomic_number = int(tokens[1])
                coordinates = (_float(tokens[3]), _float(tokens[4]), _float(tokens[5]))
            except ValueError:
                return None
            rows.append((atomic_number, coordinates))
        index += 1
    return tuple(rows) if rows else None


def _orientations(
    lines: list[str],
) -> list[tuple[int, tuple[tuple[int, tuple[float, float, float]], ...]]]:
    parsed = []
    for index, line in enumerate(lines):
        if "Standard orientation:" in line or "Input orientation:" in line:
            orientation = _parse_orientation(lines, index)
            if orientation is not None:
                parsed.append((index, orientation))
    return parsed


def _values(line: str) -> tuple[float, ...]:
    try:
        payload = line.split("--", maxsplit=1)[1]
    except IndexError as exc:
        raise ValueError(f"Malformed Gaussian vibrational property line: {line.strip()}") from exc
    return tuple(_float(token) for token in payload.split())


def _symmetry_labels(lines: list[str], frequency_index: int, count: int) -> tuple[str | None, ...]:
    previous = lines[frequency_index - 1].split() if frequency_index > 0 else []
    if len(previous) != count:
        return tuple(None for _ in range(count))
    if all(token.lstrip("+-").isdigit() for token in previous):
        return tuple(None for _ in range(count))
    return tuple(previous)


def _parse_frequency_block(lines: list[str], start: int) -> dict[str, Any]:
    frequencies = _values(lines[start])
    count = len(frequencies)
    if count == 0:
        raise ValueError("Gaussian frequency block contains no frequencies")
    block: dict[str, Any] = {
        "line_index": start,
        "frequencies": frequencies,
        "symmetry": _symmetry_labels(lines, start, count),
        "reduced_masses": None,
        "force_constants": None,
        "ir_intensities": None,
        "raman_activities": None,
        "displacements": None,
    }

    index = start + 1
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("Frequencies --"):
            break
        if stripped.startswith("Red. masses --"):
            block["reduced_masses"] = _values(lines[index])
        elif stripped.startswith("Frc consts") and "--" in stripped:
            block["force_constants"] = _values(lines[index])
        elif stripped.startswith("IR Inten") and "--" in stripped:
            block["ir_intensities"] = _values(lines[index])
        elif stripped.startswith("Raman Activ") and "--" in stripped:
            block["raman_activities"] = _values(lines[index])
        elif stripped.startswith("Atom") and "AN" in stripped.split():
            rows: list[tuple[int, int, tuple[tuple[float, float, float], ...]]] = []
            index += 1
            while index < len(lines):
                tokens = lines[index].split()
                if len(tokens) < 2:
                    break
                try:
                    atom_index = int(tokens[0])
                    atomic_number = int(tokens[1])
                except ValueError:
                    break
                expected = 2 + 3 * count
                if len(tokens) != expected:
                    raise ValueError(
                        "Gaussian vibrational displacement row has inconsistent dimensionality"
                    )
                values = tuple(_float(token) for token in tokens[2:])
                vectors = tuple(
                    (values[offset], values[offset + 1], values[offset + 2])
                    for offset in range(0, len(values), 3)
                )
                rows.append((atom_index, atomic_number, vectors))
                index += 1
            block["displacements"] = tuple(rows)
            continue
        index += 1

    for key in ("reduced_masses", "force_constants", "ir_intensities", "raman_activities"):
        values = block[key]
        if values is not None and len(values) != count:
            raise ValueError(f"Gaussian vibrational {key} count does not match frequencies")
    return block


def _frequency_blocks(lines: list[str]) -> list[dict[str, Any]]:
    return [
        _parse_frequency_block(lines, index)
        for index, line in enumerate(lines)
        if line.strip().startswith("Frequencies --")
    ]


def _selected_frequency_job(
    orientations: list[tuple[int, tuple[tuple[int, tuple[float, float, float]], ...]]],
    blocks: list[dict[str, Any]],
) -> tuple[tuple[tuple[int, tuple[float, float, float]], ...], list[dict[str, Any]]] | None:
    if not orientations or not blocks:
        return None
    final_frequency_index = int(blocks[-1]["line_index"])
    eligible = [(index, atoms) for index, atoms in orientations if index < final_frequency_index]
    if not eligible:
        return None
    orientation_index, atoms = eligible[-1]
    selected = [block for block in blocks if int(block["line_index"]) > orientation_index]
    return atoms, selected


def _modes(
    blocks: list[dict[str, Any]], atom_count: int
) -> tuple[VibrationalMode, ...]:
    modes: list[VibrationalMode] = []
    for block in blocks:
        frequencies = block["frequencies"]
        displacement_rows = block["displacements"]
        per_mode_displacements: tuple[tuple[tuple[float, float, float], ...], ...] | None = None
        if displacement_rows is not None:
            if len(displacement_rows) != atom_count:
                raise ValueError(
                    "Gaussian vibrational displacement atom count does not match molecular geometry"
                )
            atom_indices = tuple(row[0] for row in displacement_rows)
            if atom_indices != tuple(range(1, atom_count + 1)):
                raise ValueError("Gaussian vibrational displacement atom ordering is inconsistent")
            per_mode_displacements = tuple(
                tuple(row[2][mode_offset] for row in displacement_rows)
                for mode_offset in range(len(frequencies))
            )

        for offset, frequency in enumerate(frequencies):
            modes.append(
                VibrationalMode(
                    index=len(modes) + 1,
                    frequency_cm1=frequency,
                    reduced_mass_amu=(
                        block["reduced_masses"][offset]
                        if block["reduced_masses"] is not None
                        else None
                    ),
                    force_constant_mdyne_per_angstrom=(
                        block["force_constants"][offset]
                        if block["force_constants"] is not None
                        else None
                    ),
                    ir_intensity_km_mol=(
                        block["ir_intensities"][offset]
                        if block["ir_intensities"] is not None
                        else None
                    ),
                    raman_activity_a4_amu=(
                        block["raman_activities"][offset]
                        if block["raman_activities"] is not None
                        else None
                    ),
                    symmetry=block["symmetry"][offset],
                    displacements=(
                        per_mode_displacements[offset]
                        if per_mode_displacements is not None
                        else None
                    ),
                )
            )
    return tuple(modes)


def parse_gaussian_output(path: Path) -> CalculationData | CalculationMetadata:
    """Parse Gaussian metadata and typed harmonic vibrational data when available.

    Minimal Gaussian outputs retain the historical metadata-only return. A frequency
    output becomes a structure-bearing ``CalculationData`` only when a complete
    orientation and charge/multiplicity record can be associated with its modes.
    """

    source = Path(path)
    content = source.read_bytes()
    lines = content.decode("utf-8", errors="replace").splitlines()
    metadata = _metadata(lines)
    blocks = _frequency_blocks(lines)
    selected = _selected_frequency_job(_orientations(lines), blocks)
    charge_multiplicity = _charge_and_multiplicity(lines)
    if selected is None or charge_multiplicity is None:
        return metadata

    geometry, selected_blocks = selected
    charge, multiplicity = charge_multiplicity
    provenance = Provenance(
        source_path=str(source),
        sha256=sha256(content).hexdigest(),
        parser="gaussian-output",
        source_format="gaussianlog",
        parser_version="2",
    )
    atoms = tuple(
        Atom(atomic_number=atomic_number, coordinates=coordinates, nuclear_charge=float(atomic_number))
        for atomic_number, coordinates in geometry
    )
    molecule = Molecule(
        atoms=atoms,
        charge=charge,
        multiplicity=multiplicity,
        metadata=metadata,
        provenance=provenance,
    )
    modes = _modes(selected_blocks, len(atoms))
    record = VibrationalRecord(
        modes=modes,
        source_program="Gaussian",
        source_program_version=metadata.source_program_version,
        source_method=metadata.method,
        provenance=provenance,
    )
    return CalculationData(molecule=molecule, records={"vibrations": record})
