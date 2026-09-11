"""PDB structure parser for ATOM/HETATM and CONECT records."""

from hashlib import sha256
from pathlib import Path

from ..constants import SYMBOL_TO_Z
from ..errors import ParseError
from ..model import Atom, Bond, CalculationData, CalculationMetadata, Molecule, Provenance


def parse_pdb(path: Path) -> CalculationData:
    raw = path.read_bytes()
    atoms: list[Atom] = []
    serial_to_index: dict[int, int] = {}
    bond_pairs: set[tuple[int, int]] = set()
    for line_number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        record = line[:6].strip().upper()
        if record in {"ATOM", "HETATM"}:
            try:
                serial = int(line[6:11])
                coordinates = (float(line[30:38]), float(line[38:46]), float(line[46:54]))
            except ValueError as exc:
                raise ParseError(f"Malformed PDB atom record at line {line_number}.") from exc
            symbol = line[76:78].strip().title()
            if not symbol:
                symbol = "".join(
                    character for character in line[12:16] if character.isalpha()
                ).title()
                if len(symbol) > 2:
                    symbol = symbol[:1]
            if symbol not in SYMBOL_TO_Z:
                raise ParseError(f"Unknown PDB element {symbol!r} at line {line_number}.")
            serial_to_index[serial] = len(atoms)
            atoms.append(Atom(SYMBOL_TO_Z[symbol], coordinates))
        elif record == "CONECT":
            try:
                serials = [int(value) for value in line[6:].split()]
            except ValueError as exc:
                raise ParseError(f"Malformed PDB CONECT record at line {line_number}.") from exc
            if serials:
                for target in serials[1:]:
                    pair = tuple(sorted((serials[0], target)))
                    bond_pairs.add(pair)  # type: ignore[arg-type]
    if not atoms:
        raise ParseError("PDB file contains no ATOM or HETATM records.")
    try:
        bonds = tuple(sorted(Bond(serial_to_index[a], serial_to_index[b]) for a, b in bond_pairs))
    except KeyError as exc:
        raise ParseError(f"PDB CONECT references unknown atom serial {exc.args[0]}.") from exc
    molecule = Molecule(
        tuple(atoms),
        0,
        1,
        CalculationMetadata("PDB"),
        Provenance(str(path), sha256(raw).hexdigest(), "pdb"),
        bonds,
    )
    return CalculationData(molecule)
