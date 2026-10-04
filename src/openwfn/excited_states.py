"""Typed, source-faithful excited-state records shared by all program adapters."""

from dataclasses import dataclass
from math import isfinite
from typing import Literal

from .constants import HC_EV_NM
from .data import OpenWFNData
from .errors import DataUnavailableError
from .model import CalculationData

MAX_EXCITED_STATES_PER_JOB = 10_000
MAX_AMPLITUDES_PER_STATE = 1_000_000


def _require_nonblank(label: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{label} must not be blank")


def _require_finite(label: str, value: float | None) -> None:
    if value is not None and not isfinite(value):
        raise ValueError(f"{label} must be finite when present")


@dataclass(frozen=True, slots=True)
class TransitionContribution:
    """One source-reported transition/configuration contribution."""

    source_label: str
    target_label: str
    value: float
    quantity: str
    convention: str
    spin: str | None = None

    def __post_init__(self) -> None:
        _require_nonblank("source_label", self.source_label)
        _require_nonblank("target_label", self.target_label)
        _require_nonblank("quantity", self.quantity)
        _require_nonblank("convention", self.convention)
        if self.spin is not None:
            _require_nonblank("spin", self.spin)
        if not isfinite(self.value):
            raise ValueError("transition contribution value must be finite")


@dataclass(frozen=True, slots=True)
class AmplitudeBlock:
    """Convention-labelled numeric amplitudes from one source state."""

    convention: str
    values: tuple[float, ...]
    indices: tuple[tuple[int, ...], ...] = ()
    spin_block: str | None = None
    side: Literal["left", "right"] | None = None
    dimensions: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        _require_nonblank("amplitude convention", self.convention)
        if len(self.values) > MAX_AMPLITUDES_PER_STATE:
            raise ValueError(
                f"amplitude count exceeds hard limit of {MAX_AMPLITUDES_PER_STATE}"
            )
        if any(not isfinite(value) for value in self.values):
            raise ValueError("amplitude values must be finite")
        if self.indices and len(self.indices) != len(self.values):
            raise ValueError("amplitude indices must match amplitude values")
        if any(not index_tuple for index_tuple in self.indices):
            raise ValueError("amplitude index tuples must not be empty")
        if any(index < 0 for index_tuple in self.indices for index in index_tuple):
            raise ValueError("amplitude indices must be non-negative")
        if self.spin_block is not None:
            _require_nonblank("spin_block", self.spin_block)
        if any(size < 1 for size in self.dimensions):
            raise ValueError("amplitude dimensions must be positive")

    @property
    def nto_ready(self) -> bool:
        """Return whether this convention is approved for NTO construction."""

        from .parsers.excited.conventions import amplitude_semantics

        semantics = amplitude_semantics(self.convention)
        if not semantics.nto_ready:
            return False
        if self.dimensions and len(self.dimensions) != 2:
            return False
        if self.dimensions:
            expected = self.dimensions[0] * self.dimensions[1]
            if len(self.values) != expected:
                return False
        return bool(self.values)


@dataclass(frozen=True, slots=True)
class ExcitedState:
    """One source-reported excited state inside a specific source job."""

    index: int
    energy_ev: float
    source_state: str | int | None = None
    oscillator_strength: float | None = None
    transition_dipole: tuple[float, float, float] | None = None
    transition_dipole_unit: str | None = None
    multiplicity: int | None = None
    symmetry: str | None = None
    label: str | None = None
    spin_expectation: float | None = None
    transition_kind: str | None = None
    contributions: tuple[TransitionContribution, ...] = ()
    amplitudes: tuple[AmplitudeBlock, ...] = ()
    diagnostics: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if self.index < 1:
            raise ValueError("excited-state index must be one-based")
        if not isfinite(self.energy_ev):
            raise ValueError("excitation energy must be finite")
        _require_finite("oscillator strength", self.oscillator_strength)
        if self.transition_dipole is not None:
            if len(self.transition_dipole) != 3 or any(
                not isfinite(value) for value in self.transition_dipole
            ):
                raise ValueError("transition dipole must contain three finite values")
            if self.transition_dipole_unit is None:
                raise ValueError("transition_dipole_unit is required with a transition dipole")
        if self.transition_dipole_unit is not None:
            _require_nonblank("transition_dipole_unit", self.transition_dipole_unit)
        if self.multiplicity is not None and self.multiplicity < 1:
            raise ValueError("multiplicity must be at least one when present")
        _require_finite("spin expectation", self.spin_expectation)
        for label, value in (
            ("symmetry", self.symmetry),
            ("label", self.label),
            ("transition_kind", self.transition_kind),
        ):
            if value is not None:
                _require_nonblank(label, value)
        if sum(len(block.values) for block in self.amplitudes) > MAX_AMPLITUDES_PER_STATE:
            raise ValueError(
                f"amplitude count exceeds hard limit of {MAX_AMPLITUDES_PER_STATE}"
            )
        if any(not key.strip() for key, _ in self.diagnostics):
            raise ValueError("diagnostic names must not be blank")

    @property
    def wavelength_nm(self) -> float | None:
        """Return hc/E for positive excitation energy; otherwise unavailable."""

        return HC_EV_NM / self.energy_ev if self.energy_ev > 0.0 else None


@dataclass(frozen=True, slots=True)
class ExcitedStateJob:
    """Excited states belonging to one source job/block and reference state."""

    index: int
    source_program: str
    method_family: str
    method_detail: str
    states: tuple[ExcitedState, ...]
    source_program_version: str | None = None
    reference_state: str | None = None
    source_job_label: str | None = None
    charge: int | None = None
    multiplicity: int | None = None
    reference_energy_hartree: float | None = None
    atomic_numbers: tuple[int, ...] = ()
    coordinates_angstrom: tuple[tuple[float, float, float], ...] = ()
    terminated_normally: bool | None = None
    diagnostics: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if self.index < 1:
            raise ValueError("excited-state job index must be one-based")
        _require_nonblank("source_program", self.source_program)
        _require_nonblank("method_family", self.method_family)
        _require_nonblank("method_detail", self.method_detail)
        for label, value in (
            ("source_program_version", self.source_program_version),
            ("reference_state", self.reference_state),
            ("source_job_label", self.source_job_label),
        ):
            if value is not None:
                _require_nonblank(label, value)
        if self.multiplicity is not None and self.multiplicity < 1:
            raise ValueError("job multiplicity must be at least one when present")
        _require_finite("reference energy", self.reference_energy_hartree)
        if bool(self.atomic_numbers) != bool(self.coordinates_angstrom):
            raise ValueError("job atomic numbers and coordinates must be supplied together")
        if self.atomic_numbers:
            if len(self.atomic_numbers) != len(self.coordinates_angstrom):
                raise ValueError("job atomic numbers and coordinates must have matching lengths")
            if any(number < 1 for number in self.atomic_numbers):
                raise ValueError("job atomic numbers must be positive")
            if any(
                len(vector) != 3 or any(not isfinite(value) for value in vector)
                for vector in self.coordinates_angstrom
            ):
                raise ValueError("job coordinates must contain finite three-component vectors")
        if not self.states:
            raise ValueError("excited-state job must contain at least one state")
        if len(self.states) > MAX_EXCITED_STATES_PER_JOB:
            raise ValueError(
                f"state limit exceeded: at most {MAX_EXCITED_STATES_PER_JOB} states per job"
            )
        expected = tuple(range(1, len(self.states) + 1))
        actual = tuple(state.index for state in self.states)
        if actual != expected:
            raise ValueError("excited-state indices must be contiguous and one-based within each job")
        if any(not key.strip() for key, _ in self.diagnostics):
            raise ValueError("diagnostic names must not be blank")


@dataclass(frozen=True, slots=True)
class ExcitedStateCollection:
    """Program-independent excited-state jobs retained from one source file."""

    jobs: tuple[ExcitedStateJob, ...]
    parser_provenance: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.jobs:
            raise ValueError("excited-state collection must contain at least one job")
        expected = tuple(range(1, len(self.jobs) + 1))
        actual = tuple(job.index for job in self.jobs)
        if actual != expected:
            raise ValueError("excited-state job indices must be contiguous and one-based")
        if any(not key.strip() for key, _ in self.parser_provenance):
            raise ValueError("parser provenance names must not be blank")


def get_excited_state_collection(
    data: CalculationData | OpenWFNData,
) -> ExcitedStateCollection:
    """Return the typed excited-state record or fail explicitly when unavailable."""

    calculation = data.calculation if isinstance(data, OpenWFNData) else data
    if calculation is None:
        raise DataUnavailableError("Excited-state data are not available for this input.")
    record = calculation.records.get("excited_states")
    if not isinstance(record, ExcitedStateCollection):
        raise DataUnavailableError("Excited-state data are not available for this calculation.")
    return record
