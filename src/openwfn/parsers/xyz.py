"""Strict XYZ structure parser."""

from hashlib import sha256
from pathlib import Path

from ..constants import SYMBOL_TO_Z
from ..errors import ParseError
from ..model import Atom, CalculationData, CalculationMetadata, Molecule, Provenance


def parse_xyz(path: Path) -> CalculationData:
    raw = path.read_bytes()
    lines = raw.decode("utf-8").splitlines()
    if len(lines) < 2:
        raise ParseError("Malformed XYZ file: atom count and comment line are required.")
    try:
        atom_count = int(lines[0].strip())
    except ValueError as exc:
        raise ParseError("Malformed XYZ file: first line must be an integer atom count.") from exc
    if atom_count < 1 or len(lines) != atom_count + 2:
        raise ParseError(f"Malformed XYZ file: expected {atom_count} atom records.")

    atoms: list[Atom] = []
    for line_number, line in enumerate(lines[2:], start=3):
        fields = line.split()
        if len(fields) != 4:
            raise ParseError(f"Malformed XYZ atom record at line {line_number}.")
        symbol = fields[0][0].upper() + fields[0][1:].lower()
        atomic_number = SYMBOL_TO_Z.get(symbol)
        if atomic_number is None:
            raise ParseError(f"Unknown element symbol {fields[0]!r} at XYZ line {line_number}.")
        try:
            coordinates = tuple(float(value) for value in fields[1:4])
        except ValueError as exc:
            raise ParseError(f"Malformed XYZ coordinate at line {line_number}.") from exc
        atoms.append(Atom(atomic_number, coordinates))  # type: ignore[arg-type]

    provenance = Provenance(str(path), sha256(raw).hexdigest(), "xyz")
    molecule = Molecule(
        atoms=tuple(atoms),
        charge=0,
        multiplicity=1,
        metadata=CalculationMetadata(source_program="XYZ"),
        provenance=provenance,
    )
    return CalculationData(molecule=molecule)
