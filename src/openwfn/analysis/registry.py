"""Versioned registry for analyses shared by every public interface."""

from dataclasses import dataclass, replace
from time import perf_counter
from typing import Callable

from ..capabilities import CapabilityRequirement, evaluate_requirements
from ..data import INTEROP_SCHEMA_VERSION, OpenWFNData, wrap_calculation
from ..errors import DataUnavailableError
from ..model import MODEL_SCHEMA_VERSION, CalculationData
from ..results import ResultRecord
from ..services import molecular_summary, orbital_frontier, population_analysis

AnalysisRunner = Callable[[CalculationData], ResultRecord]
AnalysisInput = CalculationData | OpenWFNData


@dataclass(frozen=True, slots=True)
class AnalysisDefinition:
    name: str
    version: str
    result_kind: str
    runner: AnalysisRunner
    requirements: tuple[CapabilityRequirement, ...] = ()


_ISOLATED = CapabilityRequirement("isolated molecule", ("isolated_molecule",))
_ALPHA = CapabilityRequirement("alpha orbitals", ("alpha_orbitals",))
_BETA = CapabilityRequirement("beta orbitals", ("beta_orbitals",))
_ORBITALS = CapabilityRequirement("molecular orbitals", ("alpha_orbitals", "beta_orbitals"))
_BASIS = CapabilityRequirement("basis", ("basis",))
_TOTAL_DENSITY = CapabilityRequirement("total density", ("total_density",))
_AO_OVERLAP = CapabilityRequirement("AO overlap", ("ao_overlap",))


_ANALYSES = {
    "beta-frontier": AnalysisDefinition(
        "beta-frontier",
        "1",
        "frontier_orbitals",
        lambda data: orbital_frontier(data, "beta"),
        (_BETA,),
    ),
    "frontier": AnalysisDefinition(
        "frontier",
        "1",
        "frontier_orbitals",
        orbital_frontier,
        (_ALPHA,),
    ),
    "frontier-all": AnalysisDefinition(
        "frontier-all",
        "1",
        "frontier_orbitals",
        lambda data: orbital_frontier(data, "all"),
        (_ORBITALS,),
    ),
    "lowdin": AnalysisDefinition(
        "lowdin",
        "1",
        "lowdin_population",
        lambda data: population_analysis(data, "lowdin"),
        (_ISOLATED, _BASIS, _TOTAL_DENSITY, _AO_OVERLAP),
    ),
    "mulliken": AnalysisDefinition(
        "mulliken",
        "1",
        "mulliken_population",
        lambda data: population_analysis(data, "mulliken"),
        (_ISOLATED, _BASIS, _TOTAL_DENSITY, _AO_OVERLAP),
    ),
    "summary": AnalysisDefinition(
        "summary",
        "1",
        "summary",
        molecular_summary,
        (_ISOLATED,),
    ),
}


def available_analyses() -> tuple[str, ...]:
    """Return registered analysis names in deterministic order."""

    return tuple(sorted(_ANALYSES))


def _resolve(name: str) -> AnalysisDefinition:
    normalized = name.strip().lower()
    try:
        return _ANALYSES[normalized]
    except KeyError as exc:
        choices = ", ".join(available_analyses())
        raise ValueError(f"Unknown analysis '{name}'. Available analyses: {choices}") from exc


def _normalize(data: AnalysisInput) -> OpenWFNData:
    return data if isinstance(data, OpenWFNData) else wrap_calculation(data)


def _input_provenance(data: AnalysisInput) -> dict[str, object]:
    normalized = _normalize(data)
    provenance = normalized.provenance
    if isinstance(data, CalculationData):
        metadata = data.molecule.metadata
        return {
            "input_sha256": provenance.sha256 if provenance else None,
            "model_schema_version": MODEL_SCHEMA_VERSION,
            "parser": provenance.parser if provenance else None,
            "parser_version": provenance.parser_version if provenance else None,
            "source_format": provenance.source_format if provenance else None,
            "source_path": provenance.source_path if provenance else None,
            "source_program": metadata.source_program,
            "source_program_version": metadata.source_program_version,
            "transformations": list(provenance.transformations) if provenance else [],
        }
    return {
        "input_sha256": provenance.sha256 if provenance else None,
        "interop_schema_version": INTEROP_SCHEMA_VERSION,
        "model_schema_version": MODEL_SCHEMA_VERSION,
        "parser": provenance.parser if provenance else None,
        "parser_version": provenance.parser_version if provenance else None,
        "source_format": provenance.source_format if provenance else None,
        "source_path": provenance.source_path if provenance else None,
        "source_program": normalized.metadata.source_program,
        "source_program_version": normalized.metadata.source_program_version,
        "transformations": list(provenance.transformations) if provenance else [],
    }


def _source_warnings(data: AnalysisInput) -> tuple[str, ...]:
    provenance = _normalize(data).provenance
    return provenance.warnings if provenance else ()


def _require_analysis_capabilities(
    data: OpenWFNData,
    definition: AnalysisDefinition,
) -> None:
    availability = evaluate_requirements(data, definition.requirements)
    if availability.available:
        return
    missing = availability.missing_requirements
    if missing == ("beta orbitals",):
        raise DataUnavailableError("Beta orbitals are not available for this calculation.")
    if missing == ("alpha orbitals",):
        raise DataUnavailableError("Alpha orbitals are not available for this input.")
    if missing == ("isolated molecule",):
        raise DataUnavailableError(
            f"Analysis '{definition.name}' requires an isolated molecule."
        )
    raise DataUnavailableError(
        f"Analysis '{definition.name}' requires: {', '.join(missing)}."
    )


def run_analysis(data: AnalysisInput, name: str) -> ResultRecord:
    """Run one registered analysis and attach reproducibility metadata."""

    definition = _resolve(name)
    normalized = _normalize(data)
    _require_analysis_capabilities(normalized, definition)
    if normalized.calculation is None:
        raise DataUnavailableError(
            f"Analysis '{definition.name}' requires a molecular calculation."
        )
    started = perf_counter()
    result = definition.runner(normalized.calculation)
    elapsed = perf_counter() - started
    return replace(
        result,
        analysis_name=definition.name,
        analysis_version=definition.version,
        warnings=tuple(dict.fromkeys((*result.warnings, *_source_warnings(data)))),
        provenance=_input_provenance(data),
        elapsed_seconds=elapsed,
    )


def run_analysis_safe(data: AnalysisInput, name: str) -> ResultRecord:
    """Run one analysis and return expected scientific failures as data."""

    started = perf_counter()
    try:
        definition = _resolve(name)
    except ValueError as exc:
        return ResultRecord.failure(
            kind="analysis",
            analysis_name=name.strip().lower() or "unknown",
            analysis_version="unknown",
            exception=exc,
            elapsed_seconds=perf_counter() - started,
            warnings=_source_warnings(data),
            provenance=_input_provenance(data),
        )
    try:
        return run_analysis(data, definition.name)
    except Exception as exc:
        return ResultRecord.failure(
            kind=definition.result_kind,
            analysis_name=definition.name,
            analysis_version=definition.version,
            exception=exc,
            elapsed_seconds=perf_counter() - started,
            warnings=_source_warnings(data),
            provenance=_input_provenance(data),
        )
