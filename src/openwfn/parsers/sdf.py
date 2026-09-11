"""Single-record MDL V2000 SDF parser."""

from pathlib import Path

from ..errors import ParseError
from ..model import CalculationData
from .mol import parse_mol_text


def parse_sdf(path: Path) -> CalculationData:
    text = path.read_text(encoding="utf-8")
    records = text.split("$$$$")
    nonempty = [record.strip("\r\n") for record in records if record.strip()]
    if len(nonempty) != 1:
        raise ParseError("Version 0.7.0 accepts one structure per SDF input.")
    return parse_mol_text(nonempty[0] + "\n", path, parser_name="sdf")
