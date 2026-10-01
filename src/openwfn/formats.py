"""Pinned interoperability format inventory for openWFN 0.9."""

from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Literal


@dataclass(frozen=True, slots=True)
class FormatDefinition:
    """One readable IOData format and the rules used to identify candidates."""

    format_id: str
    patterns: tuple[str, ...]
    backend: Literal["native", "iodata"]
    requires_explicit_hint: bool = False
    multi_record_capable: bool = False


IODATA_READABLE_FORMATS: tuple[FormatDefinition, ...] = (
    FormatDefinition("charmm", ("*.crd", "*.psf"), "iodata", multi_record_capable=True),
    FormatDefinition("chgcar", ("CHGCAR", "CHGCAR-*", "*.chgcar"), "iodata"),
    FormatDefinition("cp2klog", (), "iodata", requires_explicit_hint=True),
    FormatDefinition("cube", ("*.cube", "*.cub"), "native"),
    FormatDefinition("extxyz", ("*.extxyz",), "iodata", multi_record_capable=True),
    FormatDefinition("fchk", ("*.fchk", "*.fch"), "native"),
    FormatDefinition("fcidump", ("FCIDUMP", "*.fcidump"), "iodata"),
    FormatDefinition("gamess", (), "iodata", requires_explicit_hint=True),
    FormatDefinition("gaussianinput", ("*.gjf", "*.com"), "iodata"),
    FormatDefinition("gaussianlog", ("*.log",), "iodata"),
    FormatDefinition("gromacs", ("*.gro",), "iodata", multi_record_capable=True),
    FormatDefinition("json_qcschema", ("*.qcschema.json",), "iodata"),
    FormatDefinition("locpot", ("LOCPOT", "LOCPOT-*", "*.locpot"), "iodata"),
    FormatDefinition("mol2", ("*.mol2",), "iodata"),
    FormatDefinition("molden", ("*.molden", "*.molden.input"), "iodata"),
    FormatDefinition("molekel", ("*.mkl",), "iodata"),
    FormatDefinition("mwfn", ("*.mwfn",), "iodata"),
    FormatDefinition("orcalog", (), "iodata", requires_explicit_hint=True),
    FormatDefinition("pdb", ("*.pdb",), "native", multi_record_capable=True),
    FormatDefinition("poscar", ("POSCAR", "POSCAR-*", "*.poscar", "*.vasp"), "iodata"),
    FormatDefinition("qchemlog", (), "iodata", requires_explicit_hint=True),
    FormatDefinition("sdf", ("*.sdf", "*.mol"), "native", multi_record_capable=True),
    FormatDefinition("wfn", ("*.wfn",), "iodata"),
    FormatDefinition("wfx", ("*.wfx",), "iodata"),
    FormatDefinition("xyz", ("*.xyz",), "native", multi_record_capable=True),
)


def iodata_format_ids() -> tuple[str, ...]:
    """Return the pinned IOData 1.0.1 readable-format IDs."""

    return tuple(item.format_id for item in IODATA_READABLE_FORMATS)


def path_matches_declared_format(path: str | Path) -> bool:
    """Return whether a filename matches any explicit 0.9 format pattern.

    This function only decides whether a file is a plausible batch input. It
    never decides scientific capabilities or the parser actually used.
    """

    name = Path(path).name.casefold()
    return any(
        fnmatchcase(name, pattern.casefold())
        for definition in IODATA_READABLE_FORMATS
        for pattern in definition.patterns
    )
