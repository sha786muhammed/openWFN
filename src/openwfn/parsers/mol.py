"""MDL V2000 MOL structure parser."""

from hashlib import sha256
from pathlib import Path

from ..constants import SYMBOL_TO_Z
from ..errors import ParseError
from ..model import Atom, Bond, CalculationData, CalculationMetadata, Molecule, Provenance


def parse_mol_text(
    text: str,
    path: Path,
    parser_name: str = "mol",
    provenance_bytes: bytes | None = None,
) -> CalculationData:
    lines = text.splitlines()
    if len(lines) < 4 or "V2000" not in lines[3].upper():
        raise ParseError("Only MDL V2000 MOL/SDF records are supported.")
    try:
        atom_count = int(lines[3][0:3])
        bond_count = int(lines[3][3:6])
    except ValueError as exc:
        raise ParseError("Malformed V2000 counts line.") from exc
    if len(lines) < 4 + atom_count + bond_count:
        raise ParseError("Truncated V2000 atom or bond block.")
    atoms: list[Atom] = []
    charges: dict[int, int] = {}
    for offset, line in enumerate(lines[4 : 4 + atom_count], start=5):
        try:
            coordinates = (float(line[0:10]), float(line[10:20]), float(line[20:30]))
        except ValueError as exc:
            raise ParseError(f"Malformed V2000 coordinate at line {offset}.") from exc
        symbol = line[31:34].strip().title()
        if symbol not in SYMBOL_TO_Z:
            raise ParseError(f"Unknown V2000 element {symbol!r} at line {offset}.")
        atoms.append(Atom(SYMBOL_TO_Z[symbol], coordinates))
        try:
            code = int(line[36:39].strip() or "0")
        except ValueError as exc:
            raise ParseError(f"Malformed V2000 charge at line {offset}.") from exc
        if code not in range(8):
            raise ParseError(f"Unsupported V2000 charge code at line {offset}.")
        charges[len(atoms)] = {1: 3, 2: 2, 3: 1, 5: -1, 6: -2, 7: -3}.get(code, 0)
    bonds: list[Bond] = []
    for offset, line in enumerate(
        lines[4 + atom_count : 4 + atom_count + bond_count], start=5 + atom_count
    ):
        try:
            bonds.append(Bond(int(line[0:3]) - 1, int(line[3:6]) - 1, int(line[6:9])))
        except ValueError as exc:
            raise ParseError(f"Malformed V2000 bond at line {offset}.") from exc
    for line in lines[4 + atom_count + bond_count:]:
        if line.startswith("M  CHG"):
            fields = line.split()
            try:
                count = int(fields[2])
                if count < 1 or len(fields) != 3 + 2 * count:
                    raise ValueError
                for i in range(count):
                    index, value = int(fields[3 + 2*i]), int(fields[4 + 2*i])
                    if not 1 <= index <= atom_count:
                        raise ValueError
                    charges[index] = value
            except (ValueError, IndexError) as exc:
                raise ParseError("Malformed V2000 M CHG record.") from exc
    raw = provenance_bytes if provenance_bytes is not None else text.encode("utf-8")
    molecule = Molecule(
        atoms=tuple(atoms),
        charge=sum(charges.values()),
        multiplicity=1,
        metadata=CalculationMetadata(source_program=parser_name.upper()),
        provenance=Provenance(
            source_path=str(path),
            sha256=sha256(raw).hexdigest(),
            parser=parser_name,
            source_format=parser_name,
            parser_version="1",
        ),
        bonds=tuple(bonds),
    )
    return CalculationData(molecule)


def parse_mol(path: Path) -> CalculationData:
    return parse_mol_text(path.read_text(encoding="utf-8"), path)
