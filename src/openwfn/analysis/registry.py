"""Versioned registry for analyses shared by every public interface."""

from dataclasses import dataclass, replace
from inspect import signature
from time import perf_counter
from typing import Callable

from ..capabilities import CapabilityRequirement, evaluate_requirements
from ..data import INTEROP_SCHEMA_VERSION, OpenWFNData, wrap_calculation
from ..errors import DataUnavailableError
from ..model import MODEL_SCHEMA_VERSION, CalculationData
from ..orbital_services import orbital_composition
from ..results import ResultRecord
from ..services import mayer_bond_orders, molecular_summary, orbital_frontier, population_analysis
from ..spectral_services import orbital_dos, orbital_pdos
from .excited_states import excited_state, excited_states, transition_dipoles, uvvis_spectrum
from .structure_summary import structure_summary
from .vibrations import ir_spectrum, normal_mode, raman_spectrum, vibrations

AnalysisRunner = Callable[..., ResultRecord]
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
_STRUCTURE = CapabilityRequirement("atomic structure", ("structure",))
_VIBRATIONS = CapabilityRequirement("vibrational modes", ("vibrations",))
_IR_INTENSITIES = CapabilityRequirement("IR intensities", ("ir_intensities",))
_RAMAN_ACTIVITIES = CapabilityRequirement("Raman activities", ("raman_activities",))
_NORMAL_MODE_VECTORS = CapabilityRequirement("normal mode vectors", ("normal_mode_vectors",))
_EXCITED_STATES = CapabilityRequirement("excited states", ("excited_states",))
_OSCILLATOR_STRENGTHS = CapabilityRequirement(
    "optical oscillator strengths", ("optical_oscillator_strengths",)
)
_TRANSITION_DIPOLES = CapabilityRequirement("transition dipoles", ("transition_dipoles",))


_ANALYSES = {
    "pdos": AnalysisDefinition("pdos", "1", "orbital_pdos", orbital_pdos, (_ISOLATED, _BASIS, _ORBITALS, _AO_OVERLAP)),
    "dos": AnalysisDefinition("dos", "1", "orbital_dos", orbital_dos, (_ISOLATED, _ORBITALS)),
    "mayer": AnalysisDefinition("mayer", "1", "mayer_bond_order", mayer_bond_orders, (_ISOLATED, _BASIS, _TOTAL_DENSITY, _AO_OVERLAP)),
    "orbital-composition": AnalysisDefinition("orbital-composition", "1", "orbital_composition", orbital_composition, (_ISOLATED, _BASIS, _ORBITALS, _AO_OVERLAP)),
    "beta-frontier": AnalysisDefinition(
        "beta-frontier",
        "1",
        "frontier_orbitals",
        lambda data: orbital_frontier(data, "beta"),
        (_BETA,),
    ),
    "excited-state": AnalysisDefinition(
        "excited-state",
        "1",
        "excited_state",
        excited_state,
        (_EXCITED_STATES,),
    ),
    "excited-states": AnalysisDefinition(
        "excited-states",
        "1",
        "excited_states",
        excited_states,
        (_EXCITED_STATES,),
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
    "ir-spectrum": AnalysisDefinition(
        "ir-spectrum",
        "1",
        "vibrational_spectrum",
        ir_spectrum,
        (_VIBRATIONS, _IR_INTENSITIES),
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
    "normal-mode": AnalysisDefinition(
        "normal-mode",
        "1",
        "normal_mode",
        normal_mode,
        (_VIBRATIONS, _NORMAL_MODE_VECTORS),
    ),
    "raman-spectrum": AnalysisDefinition(
        "raman-spectrum",
        "1",
        "vibrational_spectrum",
        raman_spectrum,
        (_VIBRATIONS, _RAMAN_ACTIVITIES),
    ),
    "summary": AnalysisDefinition(
        "summary",
        "2",
        "summary",
        molecular_summary,
        (_STRUCTURE,),
    ),
    "transition-dipoles": AnalysisDefinition(
        "transition-dipoles",
        "1",
        "transition_dipoles",
        transition_dipoles,
        (_EXCITED_STATES, _TRANSITION_DIPOLES),
    ),
    "uvvis-spectrum": AnalysisDefinition(
        "uvvis-spectrum",
        "1",
        "uvvis_spectrum",
        uvvis_spectrum,
        (_EXCITED_STATES, _OSCILLATOR_STRENGTHS),
    ),
    "vibrations": AnalysisDefinition(
        "vibrations",
        "1",
        "vibrational_modes",
        vibrations,
        (_VIBRATIONS,),
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


def run_analysis(data: AnalysisInput, name: str, **parameters) -> ResultRecord:
    """Run one registered analysis and attach reproducibility metadata."""

    definition = _resolve(name)
    normalized = _normalize(data)
    signature(definition.runner).bind(normalized.calculation, **parameters)
    _require_analysis_capabilities(normalized, definition)
    if normalized.calculation is None and definition.name != "summary":
        raise DataUnavailableError(
            f"Analysis '{definition.name}' requires a molecular calculation."
        )
    started = perf_counter()
    if definition.name == "summary" and (
        normalized.calculation is None
        or (
            normalized.calculation.basis is None
            and normalized.calculation.alpha_orbitals is None
            and normalized.calculation.total_density is None
        )
    ):
        result = structure_summary(normalized)
    else:
        assert normalized.calculation is not None
        result = definition.runner(normalized.calculation, **parameters)
    elapsed = perf_counter() - started
    return replace(
        result,
        analysis_name=definition.name,
        analysis_version=definition.version,
        warnings=tuple(dict.fromkeys((*result.warnings, *_source_warnings(data)))),
        provenance=_input_provenance(data),
        elapsed_seconds=elapsed,
    )


def run_analysis_safe(data: AnalysisInput, name: str, **parameters) -> ResultRecord:
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
        return run_analysis(data, definition.name, **parameters)
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
