"""Versioned registry for analyses shared by every public interface."""

from dataclasses import dataclass, replace
from time import perf_counter
from typing import Callable

from ..model import MODEL_SCHEMA_VERSION, CalculationData
from ..results import ResultRecord
from ..services import molecular_summary, orbital_frontier, population_analysis

AnalysisRunner = Callable[[CalculationData], ResultRecord]


@dataclass(frozen=True, slots=True)
class AnalysisDefinition:
    name: str
    version: str
    result_kind: str
    runner: AnalysisRunner


_ANALYSES = {
    "beta-frontier": AnalysisDefinition(
        "beta-frontier",
        "1",
        "frontier_orbitals",
        lambda data: orbital_frontier(data, "beta"),
    ),
    "frontier": AnalysisDefinition("frontier", "1", "frontier_orbitals", orbital_frontier),
    "lowdin": AnalysisDefinition(
        "lowdin",
        "1",
        "lowdin_population",
        lambda data: population_analysis(data, "lowdin"),
    ),
    "mulliken": AnalysisDefinition(
        "mulliken",
        "1",
        "mulliken_population",
        lambda data: population_analysis(data, "mulliken"),
    ),
    "summary": AnalysisDefinition("summary", "1", "summary", molecular_summary),
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


def _input_provenance(data: CalculationData) -> dict[str, object]:
    molecule = data.molecule
    provenance = molecule.provenance
    return {
        "input_sha256": provenance.sha256 if provenance else None,
        "model_schema_version": MODEL_SCHEMA_VERSION,
        "parser": provenance.parser if provenance else None,
        "parser_version": provenance.parser_version if provenance else None,
        "source_format": provenance.source_format if provenance else None,
        "source_path": provenance.source_path if provenance else None,
        "source_program": molecule.metadata.source_program,
        "source_program_version": molecule.metadata.source_program_version,
        "transformations": list(provenance.transformations) if provenance else [],
    }


def _source_warnings(data: CalculationData) -> tuple[str, ...]:
    provenance = data.molecule.provenance
    return provenance.warnings if provenance else ()


def run_analysis(data: CalculationData, name: str) -> ResultRecord:
    """Run one registered analysis and attach reproducibility metadata."""

    definition = _resolve(name)
    started = perf_counter()
    result = definition.runner(data)
    elapsed = perf_counter() - started
    return replace(
        result,
        analysis_name=definition.name,
        analysis_version=definition.version,
        warnings=tuple(dict.fromkeys((*result.warnings, *_source_warnings(data)))),
        provenance=_input_provenance(data),
        elapsed_seconds=elapsed,
    )


def run_analysis_safe(data: CalculationData, name: str) -> ResultRecord:
    """Run one analysis and return expected scientific failures as data."""

    definition = _resolve(name)
    started = perf_counter()
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
