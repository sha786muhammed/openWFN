"""Pinned interoperability format inventory for openWFN 0.9."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class FormatDefinition:
    """One IOData-readable format and its filename-detection metadata."""

    format_id: str
    patterns: tuple[str, ...]
    backend: Literal["native", "iodata"]
    requires_explicit_hint: bool = False
    multi_record_capable: bool = False


IODATA_READABLE_FORMATS: tuple[FormatDefinition, ...] = (
    FormatDefinition("charmm", ("*.crd", "*.cor"), "iodata", multi_record_capable=True),
    FormatDefinition("chgcar", ("CHGCAR", "CHGCAR.*"), "iodata"),
    FormatDefinition("cp2klog", ("*.cp2k.out", "*.cp2k.log"), "iodata", requires_explicit_hint=True),
    FormatDefinition("cube", ("*.cube", "*.cub"), "iodata"),
    FormatDefinition("extxyz", ("*.extxyz",), "iodata", multi_record_capable=True),
    FormatDefinition("fchk", ("*.fchk", "*.fch"), "iodata"),
    FormatDefinition("fcidump", ("FCIDUMP", "*.fcidump"), "iodata"),
    FormatDefinition("gamess", ("*.gamess.out", "*.gamess.log", "*.gms"), "iodata", requires_explicit_hint=True),
    FormatDefinition("gaussianinput", ("*.gjf", "*.com"), "iodata"),
    FormatDefinition("gaussianlog", ("*.log", "*.gaussian.out"), "iodata", requires_explicit_hint=True),
    FormatDefinition("gromacs", ("*.gro",), "iodata", multi_record_capable=True),
    FormatDefinition("json_qcschema", ("*.qcschema.json",), "iodata", requires_explicit_hint=True),
    FormatDefinition("locpot", ("LOCPOT", "LOCPOT.*"), "iodata"),
    FormatDefinition("mol2", ("*.mol2",), "iodata"),
    FormatDefinition("molden", ("*.molden", "*.molden.input"), "iodata"),
    FormatDefinition("molekel", ("*.mkl",), "iodata"),
    FormatDefinition("mwfn", ("*.mwfn",), "iodata"),
    FormatDefinition("orcalog", ("*.orca.out", "*.orca.log"), "iodata", requires_explicit_hint=True),
    FormatDefinition("pdb", ("*.pdb",), "iodata", multi_record_capable=True),
    FormatDefinition("poscar", ("POSCAR", "CONTCAR", "POSCAR.*", "CONTCAR.*"), "iodata"),
    FormatDefinition("qchemlog", ("*.qchem.out", "*.qchem.log"), "iodata", requires_explicit_hint=True),
    FormatDefinition("sdf", ("*.sdf", "*.mol"), "iodata", multi_record_capable=True),
    FormatDefinition("wfn", ("*.wfn",), "iodata"),
    FormatDefinition("wfx", ("*.wfx",), "iodata"),
    FormatDefinition("xyz", ("*.xyz",), "iodata", multi_record_capable=True),
)


def iodata_format_ids() -> tuple[str, ...]:
    """Return the pinned IOData 1.0.1 readable-format identifiers."""

    return tuple(item.format_id for item in IODATA_READABLE_FORMATS)
