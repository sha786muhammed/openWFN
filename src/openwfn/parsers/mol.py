"""MDL V2000 MOL structure parser."""

from hashlib import sha256
from pathlib import Path

from ..constants import SYMBOL_TO_Z
from ..errors import ParseError
from ..model import Atom, Bond, CalculationData, CalculationMetadata, Molecule, Provenance


def parse_mol_text(text: str, path: Path, parser_name: str = "mol") -> CalculationData:
    lines = text.splitlines()
    if len(lines) < 4 or "V2000" not in lines[3]:
        raise ParseError("Only MDL V2000 MOL/SDF records are supported.")
    try:
        atom_count = int(lines[3][0:3])
        bond_count = int(lines[3][3:6])
    except ValueError as exc:
        raise ParseError("Malformed V2000 counts line.") from exc
    if len(lines) < 4 + atom_count + bond_count:
        raise ParseError("Truncated V2000 atom or bond block.")
    atoms: list[Atom] = []
    for offset, line in enumerate(lines[4 : 4 + atom_count], start=5):
        try:
            coordinates = (float(line[0:10]), float(line[10:20]), float(line[20:30]))
        except ValueError as exc:
            raise ParseError(f"Malformed V2000 coordinate at line {offset}.") from exc
        symbol = line[31:34].strip().title()
        if symbol not in SYMBOL_TO_Z:
            raise ParseError(f"Unknown V2000 element {symbol!r} at line {offset}.")
        atoms.append(Atom(SYMBOL_TO_Z[symbol], coordinates))
    bonds: list[Bond] = []
    for offset, line in enumerate(
        lines[4 + atom_count : 4 + atom_count + bond_count], start=5 + atom_count
    ):
        try:
            bonds.append(Bond(int(line[0:3]) - 1, int(line[3:6]) - 1, int(line[6:9])))
        except ValueError as exc:
            raise ParseError(f"Malformed V2000 bond at line {offset}.") from exc
    raw = text.encode("utf-8")
    molecule = Molecule(
        tuple(atoms),
        0,
        1,
        CalculationMetadata(parser_name.upper()),
        Provenance(str(path), sha256(raw).hexdigest(), parser_name),
        tuple(bonds),
    )
    return CalculationData(molecule)


def parse_mol(path: Path) -> CalculationData:
    return parse_mol_text(path.read_text(encoding="utf-8"), path)
