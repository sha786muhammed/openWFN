"""Centralized input routing for native and optional interoperability parsers."""

from fnmatch import fnmatchcase
from hashlib import sha256
from importlib import import_module
from pathlib import Path
from typing import Any

from .data import OpenWFNData, SourceMetadata, wrap_calculation
from .errors import MissingOptionalDependencyError, ParseError
from .formats import IODATA_READABLE_FORMATS, FormatDefinition
from .model import CalculationData, CalculationMetadata, Provenance, VolumetricGrid
from .parsers.registry import DEFAULT_REGISTRY, looks_like_gaussian_output

_NATIVE_SUFFIXES = {".chk", ".cub", ".cube", ".fch", ".fchk", ".mol", ".pdb", ".sdf", ".xyz"}
_FORMATS_BY_ID = {definition.format_id: definition for definition in IODATA_READABLE_FORMATS}


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _generated_provenance(path: Path, *, parser: str, source_format: str) -> Provenance:
    return Provenance(
        source_path=str(path),
        sha256=_sha256(path),
        parser=parser,
        source_format=source_format,
        parser_version="1",
    )


def _normalize_native(parsed: Any, path: Path, *, source_format: str) -> OpenWFNData:
    if isinstance(parsed, CalculationData):
        return wrap_calculation(parsed)
    if isinstance(parsed, VolumetricGrid):
        return OpenWFNData(
            calculation=None,
            structure=None,
            periodic=None,
            grids=(parsed,),
            integrals=None,
            metadata=SourceMetadata(),
            provenance=_generated_provenance(
                path, parser="gaussian-cube", source_format=source_format
            ),
        )
    if isinstance(parsed, CalculationMetadata):
        return OpenWFNData(
            calculation=None,
            structure=None,
            periodic=None,
            grids=(),
            integrals=None,
            metadata=SourceMetadata(
                source_program=parsed.source_program,
                source_program_version=parsed.source_program_version,
                energy_hartree=parsed.energy_hartree,
            ),
            provenance=_generated_provenance(
                path, parser="gaussian-output", source_format=source_format
            ),
        )
    raise ParseError(f"Unsupported native parser result type: {type(parsed).__name__}.")


def _definition_for_pattern(path: Path) -> FormatDefinition | None:
    name = path.name.casefold()
    for definition in IODATA_READABLE_FORMATS:
        for pattern in definition.patterns:
            if fnmatchcase(name, pattern.casefold()):
                return definition
    return None


def _detect_text_output_format(path: Path) -> str | None:
    name = path.name.casefold()
    if name.endswith(".cp2k.out"):
        return "cp2klog"
    if looks_like_gaussian_output(path):
        return "gaussianlog"
    with path.open(encoding="utf-8", errors="replace") as stream:
        text = stream.read(131072)
    upper = text.upper()
    if "O   R   C   A" in upper or "FINAL SINGLE POINT ENERGY" in upper:
        return "orcalog"
    if "Q-CHEM" in upper:
        return "qchemlog"
    if "GAMESS" in upper:
        return "gamess"
    if "CP2K|" in upper or "CP2K VERSION" in upper:
        return "cp2klog"
    return None


def _has_multiple_xyz_records(path: Path) -> bool:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return False
    try:
        atom_count = int(lines[0].strip())
    except ValueError:
        return False
    next_record = atom_count + 2
    while next_record < len(lines) and not lines[next_record].strip():
        next_record += 1
    if next_record >= len(lines):
        return False
    try:
        second_count = int(lines[next_record].strip())
    except ValueError:
        return False
    return second_count > 0 and len(lines) >= next_record + second_count + 2


def _load_iodata(path: Path, *, format_id: str) -> OpenWFNData:
    try:
        import_module("iodata")
    except ModuleNotFoundError as exc:
        raise MissingOptionalDependencyError(
            f"Input format '{format_id}' requires the interoperability backend. "
            'Install it with: pip install "openwfn[interop]"'
        ) from exc

    try:
        adapter = import_module("openwfn.adapters.iodata")
    except ModuleNotFoundError as exc:
        raise ParseError("The openWFN IOData adapter is unavailable in this build.") from exc
    return adapter.load_iodata(path, format_id=format_id)


def _load_native(path: Path, *, source_format: str) -> OpenWFNData:
    if path.suffix.casefold() == ".xyz" and _has_multiple_xyz_records(path):
        raise ParseError(
            "XYZ contains multiple records; sequence/trajectory ingestion is not part of the "
            "0.9 load() API."
        )
    return _normalize_native(DEFAULT_REGISTRY.load(path), path, source_format=source_format)


def load_input(path: Path, *, format_hint: str | None = None) -> OpenWFNData:
    """Load one input record through the strongest registered ingestion path."""

    source = Path(path)
    if not source.is_file():
        raise ParseError(f"Input file does not exist: {source}")

    if format_hint is not None:
        normalized_hint = format_hint.strip().lower()
        definition = _FORMATS_BY_ID.get(normalized_hint)
        if definition is None:
            choices = ", ".join(sorted(_FORMATS_BY_ID))
            raise ParseError(
                f"Unknown input format hint '{format_hint}'. Available format IDs: {choices}"
            )
        if definition.backend == "native":
            return _load_native(source, source_format=definition.format_id)
        return _load_iodata(source, format_id=definition.format_id)

    suffix = source.suffix.casefold()
    if suffix in _NATIVE_SUFFIXES:
        native_format = {
            ".cub": "cube",
            ".cube": "cube",
            ".fch": "fchk",
            ".fchk": "fchk",
            ".chk": "fchk",
            ".mol": "mol",
            ".pdb": "pdb",
            ".sdf": "sdf",
            ".xyz": "xyz",
        }[suffix]
        return _load_native(source, source_format=native_format)

    if suffix in {".log", ".out"}:
        detected = _detect_text_output_format(source)
        if detected == "gaussianlog":
            return _normalize_native(
                DEFAULT_REGISTRY.load(source), source, source_format="gaussianlog"
            )
        if detected is not None:
            return _load_iodata(source, format_id=detected)

    definition = _definition_for_pattern(source)
    if definition is not None:
        if definition.backend == "native":
            return _load_native(source, source_format=definition.format_id)
        return _load_iodata(source, format_id=definition.format_id)

    with source.open(encoding="utf-8", errors="replace") as stream:
        header = stream.read(4096).lstrip("\ufeff \t\r\n").casefold()
    if header.startswith("[molden format]"):
        return _load_iodata(source, format_id="molden")
    raise ParseError(f"Unsupported input format '{source.suffix}' for {source.name}.")
