"""Typed source-reported vibrational data for spectroscopy workflows."""

from dataclasses import dataclass, field
from math import isfinite
from typing import Any

import numpy as np

from .errors import DataUnavailableError
from .model import CalculationData, Provenance

Vector3 = tuple[float, float, float]


def _finite_optional(label: str, value: float | None) -> None:
    if value is not None and not isfinite(value):
        raise ValueError(f"{label} must be finite when available")


@dataclass(frozen=True, slots=True)
class VibrationalMode:
    """One source-reported normal mode in source atom ordering."""

    index: int
    frequency_cm1: float
    reduced_mass_amu: float | None = None
    force_constant_mdyne_per_angstrom: float | None = None
    ir_intensity_km_mol: float | None = None
    raman_activity_a4_amu: float | None = None
    symmetry: str | None = None
    displacements: tuple[Vector3, ...] | None = None
    imaginary: bool = field(init=False)

    def __post_init__(self) -> None:
        if self.index < 1:
            raise ValueError("mode index must be one-based and positive")
        if not isfinite(self.frequency_cm1):
            raise ValueError("frequency must be finite")
        for label, value in (
            ("reduced mass", self.reduced_mass_amu),
            ("force constant", self.force_constant_mdyne_per_angstrom),
            ("IR intensity", self.ir_intensity_km_mol),
            ("Raman activity", self.raman_activity_a4_amu),
        ):
            _finite_optional(label, value)
        if self.symmetry is not None and not self.symmetry.strip():
            raise ValueError("symmetry label must not be blank")
        if self.displacements is not None:
            if not self.displacements:
                raise ValueError("displacements must not be empty when available")
            if any(len(vector) != 3 for vector in self.displacements):
                raise ValueError("displacements must contain three-component vectors")
            if any(not isfinite(value) for vector in self.displacements for value in vector):
                raise ValueError("displacements must contain only finite values")
        object.__setattr__(self, "imaginary", self.frequency_cm1 < 0.0)


@dataclass(frozen=True, slots=True)
class VibrationalRecord:
    """Source-reported harmonic vibrational record attached to a calculation."""

    modes: tuple[VibrationalMode, ...]
    source_program: str
    source_program_version: str | None = None
    source_method: str | None = None
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        if not self.modes:
            raise ValueError("vibrational record must contain at least one mode")
        if not self.source_program.strip():
            raise ValueError("source program must not be blank")
        expected = tuple(range(1, len(self.modes) + 1))
        indices = tuple(mode.index for mode in self.modes)
        if indices != expected:
            raise ValueError("vibrational mode indices must be contiguous and one-based")
        vector_counts = {
            len(mode.displacements)
            for mode in self.modes
            if mode.displacements is not None
        }
        if len(vector_counts) > 1:
            raise ValueError("vibrational displacement atom counts are inconsistent")

    @property
    def ir_available(self) -> bool:
        return all(mode.ir_intensity_km_mol is not None for mode in self.modes)

    @property
    def raman_available(self) -> bool:
        return all(mode.raman_activity_a4_amu is not None for mode in self.modes)

    @property
    def displacements_available(self) -> bool:
        return all(mode.displacements is not None for mode in self.modes)


def _optional_mode_array(parsed: Any, name: str, mode_count: int) -> np.ndarray | None:
    values = getattr(parsed, name, None)
    if values is None:
        return None
    array = np.asarray(values)
    if array.ndim != 1 or len(array) != mode_count:
        raise ValueError(f"cclib {name} length is inconsistent with vibfreqs")
    return array


def vibrational_record_from_cclib(
    parsed: Any,
    *,
    provenance: Provenance | None = None,
) -> VibrationalRecord | None:
    """Promote cclib vibration attributes into the shared typed record.

    cclib reports frequencies in cm^-1, IR intensities in km/mol, reduced
    masses in amu/Da, force constants in mDyne/angstrom, Raman activities in
    angstrom^4/amu, and Cartesian displacement vectors in source atom order.
    Missing optional quantities remain ``None`` rather than being inferred.
    """

    frequency_values = getattr(parsed, "vibfreqs", None)
    if frequency_values is None:
        return None
    frequencies = np.asarray(frequency_values, dtype=float)
    if frequencies.ndim != 1 or len(frequencies) == 0:
        raise ValueError("cclib vibfreqs must be a non-empty one-dimensional array")
    mode_count = len(frequencies)

    masses = _optional_mode_array(parsed, "vibrmasses", mode_count)
    force_constants = _optional_mode_array(parsed, "vibfconsts", mode_count)
    ir_intensities = _optional_mode_array(parsed, "vibirs", mode_count)
    raman_activities = _optional_mode_array(parsed, "vibramans", mode_count)
    symmetries = _optional_mode_array(parsed, "vibsyms", mode_count)

    displacement_values = getattr(parsed, "vibdisps", None)
    displacements: np.ndarray | None = None
    if displacement_values is not None:
        displacements = np.asarray(displacement_values, dtype=float)
        if displacements.ndim != 3 or displacements.shape[0] != mode_count or displacements.shape[2] != 3:
            raise ValueError("cclib vibdisps must have shape (n_modes, n_atoms, 3)")

    metadata = getattr(parsed, "metadata", {}) or {}
    source_program = str(metadata.get("package") or "cclib")
    source_program_version = metadata.get("package_version")
    methods = metadata.get("methods") or ()
    source_method = str(methods[-1]) if methods else None

    modes: list[VibrationalMode] = []
    for index, frequency in enumerate(frequencies):
        mode_displacements = None
        if displacements is not None:
            mode_displacements = tuple(
                tuple(float(value) for value in vector)  # type: ignore[misc]
                for vector in displacements[index]
            )
        symmetry = None
        if symmetries is not None:
            symmetry = str(symmetries[index])
        modes.append(
            VibrationalMode(
                index=index + 1,
                frequency_cm1=float(frequency),
                reduced_mass_amu=float(masses[index]) if masses is not None else None,
                force_constant_mdyne_per_angstrom=(
                    float(force_constants[index]) if force_constants is not None else None
                ),
                ir_intensity_km_mol=(
                    float(ir_intensities[index]) if ir_intensities is not None else None
                ),
                raman_activity_a4_amu=(
                    float(raman_activities[index]) if raman_activities is not None else None
                ),
                symmetry=symmetry,
                displacements=mode_displacements,
            )
        )
    return VibrationalRecord(
        modes=tuple(modes),
        source_program=source_program,
        source_program_version=(
            str(source_program_version) if source_program_version is not None else None
        ),
        source_method=source_method,
        provenance=provenance,
    )


def get_vibrational_record(data: CalculationData) -> VibrationalRecord:
    """Return the typed vibrational record or fail explicitly when unavailable."""

    record = data.records.get("vibrations")
    if not isinstance(record, VibrationalRecord):
        raise DataUnavailableError("Vibrational data are not available for this calculation.")
    return record
