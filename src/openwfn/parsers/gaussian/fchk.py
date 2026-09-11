"""Strict reader for Gaussian formatted checkpoint files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import TypeAlias

from ...constants import BOHR_TO_ANGSTROM
from ...errors import ParseError
from ...model import (
    Atom,
    BasisSet,
    BasisShell,
    CalculationData,
    CalculationMetadata,
    DensityMatrix,
    MolecularOrbitals,
    Molecule,
    Provenance,
)

Scalar: TypeAlias = int | float | str
Array: TypeAlias = tuple[int, ...] | tuple[float, ...] | tuple[str, ...]
RecordValue: TypeAlias = Scalar | Array

_HEADER = re.compile(
    r"^(?P<label>.*?)\s+(?P<kind>[IRC])\s+(?:(?:N\s*=\s*(?P<count>\d+))|(?P<value>.*?))\s*$"
)


def _convert_numeric(token: str, kind: str, label: str, line_number: int) -> int | float:
    try:
        if kind == "I":
            return int(token)
        return float(token.replace("D", "E").replace("d", "e"))
    except ValueError as exc:
        description = "not-an-integer" if kind == "I" else "not-a-real-number"
        raise ParseError(
            f"Malformed FCHK record '{label}' at line {line_number}: "
            f"token {token!r} is {description}."
        ) from exc


@dataclass(frozen=True, slots=True)
class FCHKDocument:
    """Validated scalar and array records from one FCHK document."""

    records: dict[str, RecordValue]

    @classmethod
    def from_lines(cls, lines: list[str]) -> FCHKDocument:
        records: dict[str, RecordValue] = {}
        index = 0
        while index < len(lines):
            match = _HEADER.match(lines[index].rstrip("\n"))
            if match is None:
                index += 1
                continue

            label = match.group("label").strip()
            kind = match.group("kind")
            count_text = match.group("count")
            if count_text is None:
                raw_value = match.group("value").strip()
                if kind == "C":
                    records[label] = raw_value
                else:
                    records[label] = _convert_numeric(raw_value, kind, label, index + 1)
                index += 1
                continue

            count = int(count_text)
            header_line = index + 1
            values: list[int | float | str] = []
            index += 1
            while len(values) < count and index < len(lines):
                candidate = lines[index].rstrip("\n")
                if _HEADER.match(candidate):
                    break
                if kind == "C":
                    chunks = [candidate[start : start + 12].strip() for start in range(0, len(candidate), 12)]
                    values.extend(chunks)
                else:
                    values.extend(
                        _convert_numeric(token, kind, label, index + 1)
                        for token in candidate.split()
                    )
                if len(values) > count:
                    raise ParseError(
                        f"Malformed FCHK record '{label}' at line {header_line}: "
                        f"expected {count} values but found at least {len(values)}."
                    )
                index += 1

            if len(values) != count:
                raise ParseError(
                    f"Malformed FCHK record '{label}' at line {header_line}: "
                    f"expected {count} values but found {len(values)}."
                )
            records[label] = tuple(values)  # type: ignore[assignment]

        return cls(records=records)

    def scalar(self, name: str) -> Scalar:
        value = self.records.get(name)
        if value is None or isinstance(value, tuple):
            raise ParseError(f"Required scalar FCHK record '{name}' is missing.")
        return value

    def array(self, name: str) -> Array:
        value = self.records.get(name)
        if value is None or not isinstance(value, tuple):
            raise ParseError(f"Required array FCHK record '{name}' is missing.")
        return value


def _basis_from_document(document: FCHKDocument) -> BasisSet | None:
    required = (
        "Shell types",
        "Number of primitives per shell",
        "Shell to atom map",
        "Primitive exponents",
        "Contraction coefficients",
    )
    if not all(name in document.records for name in required):
        return None
    shell_types = tuple(int(value) for value in document.array("Shell types"))
    primitive_counts = tuple(int(value) for value in document.array("Number of primitives per shell"))
    shell_atoms = tuple(int(value) for value in document.array("Shell to atom map"))
    exponents = tuple(float(value) for value in document.array("Primitive exponents"))
    coefficients = tuple(float(value) for value in document.array("Contraction coefficients"))
    p_values = document.records.get("P(S=P) Contraction coefficients")
    p_coefficients = tuple(float(value) for value in p_values) if isinstance(p_values, tuple) else None
    if not (len(shell_types) == len(primitive_counts) == len(shell_atoms)):
        raise ParseError("FCHK shell types, primitive counts, and atom map have different lengths.")
    if sum(primitive_counts) != len(exponents) or len(exponents) != len(coefficients):
        raise ParseError("FCHK primitive counts do not match exponent and contraction arrays.")
    if p_coefficients is not None and len(p_coefficients) != len(exponents):
        raise ParseError("FCHK P(S=P) coefficients do not match primitive exponents.")

    shells: list[BasisShell] = []
    start = 0
    for shell_type, primitive_count, atom_number in zip(shell_types, primitive_counts, shell_atoms):
        stop = start + primitive_count
        angular_momentum = abs(shell_type) if shell_type < -1 else shell_type
        shells.append(
            BasisShell(
                atom_index=atom_number - 1,
                angular_momentum=angular_momentum,
                exponents=exponents[start:stop],
                coefficients=coefficients[start:stop],
                pure=shell_type < -1,
                p_coefficients=p_coefficients[start:stop]
                if shell_type == -1 and p_coefficients is not None
                else None,
            )
        )
        start = stop
    return BasisSet(tuple(shells))


def _orbital_channel(
    document: FCHKDocument,
    energy_record: str,
    coefficient_record: str,
    occupations: tuple[float, ...],
    spin: str,
) -> MolecularOrbitals | None:
    energy_values = document.records.get(energy_record)
    coefficient_values = document.records.get(coefficient_record)
    if not isinstance(energy_values, tuple) or not isinstance(coefficient_values, tuple):
        return None
    energies = tuple(float(value) for value in energy_values)
    coefficients_flat = tuple(float(value) for value in coefficient_values)
    orbital_count = len(energies)
    if orbital_count == 0 or len(coefficients_flat) % orbital_count:
        raise ParseError(f"FCHK {coefficient_record} length is incompatible with orbital energies.")
    basis_count = len(coefficients_flat) // orbital_count
    coefficients = tuple(
        tuple(coefficients_flat[orbital * basis_count + basis] for orbital in range(orbital_count))
        for basis in range(basis_count)
    )
    if len(occupations) != orbital_count:
        raise ParseError(f"FCHK electron counts are incompatible with {energy_record}.")
    return MolecularOrbitals(energies, coefficients, occupations, spin=spin)  # type: ignore[arg-type]


def _orbitals_from_document(
    document: FCHKDocument,
) -> tuple[MolecularOrbitals | None, MolecularOrbitals | None]:
    alpha_energy_record = (
        "Alpha Orbital Energies"
        if "Alpha Orbital Energies" in document.records
        else "Alpha MO energies"
    )
    beta_energy_record = (
        "Beta Orbital Energies"
        if "Beta Orbital Energies" in document.records
        else "Beta MO energies"
    )
    alpha_values = document.records.get(alpha_energy_record)
    if not isinstance(alpha_values, tuple):
        return None, None
    orbital_count = len(alpha_values)
    alpha_electrons = int(document.scalar("Number of alpha electrons"))
    beta_electrons = int(document.scalar("Number of beta electrons"))
    has_beta = isinstance(document.records.get(beta_energy_record), tuple)
    if has_beta:
        alpha_occupations = tuple(1.0 if index < alpha_electrons else 0.0 for index in range(orbital_count))
        beta_values = document.array(beta_energy_record)
        beta_occupations = tuple(1.0 if index < beta_electrons else 0.0 for index in range(len(beta_values)))
        alpha = _orbital_channel(
            document, alpha_energy_record, "Alpha MO coefficients", alpha_occupations, "alpha"
        )
        beta = _orbital_channel(
            document, beta_energy_record, "Beta MO coefficients", beta_occupations, "beta"
        )
        return alpha, beta
    restricted_occupations = tuple(
        2.0 if index < beta_electrons else 1.0 if index < alpha_electrons else 0.0
        for index in range(orbital_count)
    )
    return (
        _orbital_channel(
            document,
            alpha_energy_record,
            "Alpha MO coefficients",
            restricted_occupations,
            "restricted",
        ),
        None,
    )


def _density_from_document(
    document: FCHKDocument, record: str, kind: str
) -> DensityMatrix | None:
    packed = document.records.get(record)
    if not isinstance(packed, tuple):
        return None
    count = len(packed)
    size = int((-1.0 + (1.0 + 8.0 * count) ** 0.5) / 2.0)
    if size * (size + 1) // 2 != count:
        raise ParseError(f"FCHK {record} is not a packed symmetric matrix.")
    matrix = [[0.0 for _ in range(size)] for _ in range(size)]
    index = 0
    for row in range(size):
        for column in range(row + 1):
            value = float(packed[index])
            matrix[row][column] = value
            matrix[column][row] = value
            index += 1
    return DensityMatrix(tuple(tuple(row) for row in matrix), kind=kind)  # type: ignore[arg-type]

def parse_fchk(path: Path) -> CalculationData:
    """Parse an FCHK file into the unified typed domain model."""

    raw = path.read_bytes()
    text = raw.decode("utf-8")
    lines = text.splitlines(keepends=True)
    document = FCHKDocument.from_lines(lines)

    atom_count = int(document.scalar("Number of atoms"))
    atomic_numbers = tuple(int(value) for value in document.array("Atomic numbers"))
    raw_coordinates = tuple(float(value) for value in document.array("Current cartesian coordinates"))
    if len(atomic_numbers) != atom_count or len(raw_coordinates) != atom_count * 3:
        raise ParseError(
            "FCHK 'Number of atoms' does not match Atomic numbers and Current cartesian coordinates."
        )

    method: str | None = None
    basis: str | None = None
    if len(lines) >= 2:
        tokens = lines[1].split()
        if len(tokens) >= 3:
            method, basis = tokens[-2], tokens[-1]

    metadata = CalculationMetadata(
        source_program="Gaussian",
        method=method,
        basis=basis,
        energy_hartree=float(document.records["Total Energy"])
        if isinstance(document.records.get("Total Energy"), (int, float))
        else None,
    )
    provenance = Provenance(
        source_path=str(path),
        sha256=sha256(raw).hexdigest(),
        parser="gaussian-fchk",
    )
    atoms = tuple(
        Atom(
            atomic_number=atomic_numbers[index],
            coordinates=tuple(
                raw_coordinates[index * 3 + axis] * BOHR_TO_ANGSTROM for axis in range(3)
            ),  # type: ignore[arg-type]
        )
        for index in range(atom_count)
    )
    molecule = Molecule(
        atoms=atoms,
        charge=int(document.scalar("Charge")),
        multiplicity=int(document.scalar("Multiplicity")),
        metadata=metadata,
        provenance=provenance,
    )
    alpha_orbitals, beta_orbitals = _orbitals_from_document(document)
    total_density = _density_from_document(document, "Total SCF Density", "total")
    spin_density = _density_from_document(document, "Spin SCF Density", "spin")
    return CalculationData(
        molecule=molecule,
        basis=_basis_from_document(document),
        alpha_orbitals=alpha_orbitals,
        beta_orbitals=beta_orbitals,
        total_density=total_density,
        spin_density=spin_density,
        records=document.records,
    )
