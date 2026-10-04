"""Source-faithful vibrational mode and spectrum analyses."""

from typing import Callable

from ..errors import DataUnavailableError
from ..model import CalculationData
from ..results import ResultRecord
from ..vibrational import VibrationalMode, get_vibrational_record
from ..vibrational_services import DEFAULT_FWHM_CM1, broaden_lines


def _mode_row(mode: VibrationalMode) -> dict[str, object]:
    return {
        "mode": mode.index,
        "frequency_cm1": mode.frequency_cm1,
        "imaginary": mode.imaginary,
        "symmetry": mode.symmetry,
        "reduced_mass_amu": mode.reduced_mass_amu,
        "force_constant_mdyne_per_angstrom": mode.force_constant_mdyne_per_angstrom,
        "ir_intensity_km_mol": mode.ir_intensity_km_mol,
        "raman_activity_a4_amu": mode.raman_activity_a4_amu,
    }


def vibrations(data: CalculationData) -> ResultRecord:
    """Return source-reported mode metadata without broadening."""

    record = get_vibrational_record(data)
    return ResultRecord(
        kind="vibrational_modes",
        data={
            "mode_count": len(record.modes),
            "imaginary_mode_count": sum(mode.imaginary for mode in record.modes),
            "ir_available": record.ir_available,
            "raman_available": record.raman_available,
            "displacements_available": record.displacements_available,
            "modes": [_mode_row(mode) for mode in record.modes],
        },
        units={
            "modes": (
                "frequency: cm^-1; reduced_mass: amu; force_constant: mDyne/angstrom; "
                "IR intensity: km/mol; Raman activity: angstrom^4/amu"
            )
        },
        validation_status="Experimental",
    )


def _spectrum(
    data: CalculationData,
    *,
    spectrum_type: str,
    strength_getter: Callable[[VibrationalMode], float | None],
    strength_name: str,
    strength_unit: str,
    fwhm_cm1: float,
    frequency_min_cm1: float | None,
    frequency_max_cm1: float | None,
    points: int | None,
) -> ResultRecord:
    record = get_vibrational_record(data)
    strengths = [strength_getter(mode) for mode in record.modes]
    if any(value is None for value in strengths):
        label = "IR intensities" if spectrum_type == "ir" else "Raman activities"
        raise DataUnavailableError(f"{label} are not available for all vibrational modes.")

    lines = [
        {
            "mode": mode.index,
            "frequency_cm1": mode.frequency_cm1,
            strength_name: float(strengths[index]),
            "imaginary": mode.imaginary,
            "symmetry": mode.symmetry,
        }
        for index, mode in enumerate(record.modes)
    ]
    real_pairs = [
        (mode.frequency_cm1, float(strengths[index]))
        for index, mode in enumerate(record.modes)
        if not mode.imaginary and mode.frequency_cm1 >= 0.0
    ]
    if not real_pairs:
        raise DataUnavailableError(
            f"No non-imaginary modes are available for the {spectrum_type.upper()} curve."
        )
    real_frequencies = tuple(pair[0] for pair in real_pairs)
    real_strengths = tuple(pair[1] for pair in real_pairs)
    grid, curve = broaden_lines(
        real_frequencies,
        real_strengths,
        fwhm_cm1=fwhm_cm1,
        frequency_min_cm1=frequency_min_cm1,
        frequency_max_cm1=frequency_max_cm1,
        points=points,
    )
    excluded = [mode.index for mode in record.modes if mode.imaginary]
    warnings = ()
    if excluded:
        warnings = (
            "Imaginary modes are retained in source stick data but excluded from the "
            "broadened physical spectrum.",
        )

    return ResultRecord(
        kind="vibrational_spectrum",
        data={
            "spectrum_type": spectrum_type,
            "quantity": "ir_intensity" if spectrum_type == "ir" else "raman_activity",
            "lines": lines,
            "frequency_cm1": grid.tolist(),
            "intensity": curve.tolist(),
            "broadening": {"type": "gaussian", "fwhm_cm1": float(fwhm_cm1)},
            "frequency_range_cm1": [float(grid[0]), float(grid[-1])],
            "excluded_imaginary_modes": excluded,
        },
        units={
            "lines": f"frequency: cm^-1; {strength_name}: {strength_unit}",
            "frequency_cm1": "cm^-1",
            "intensity": strength_unit,
            "frequency_range_cm1": "cm^-1",
            "broadening": "FWHM: cm^-1",
        },
        validation_status="Experimental",
        warnings=warnings,
    )


def ir_spectrum(
    data: CalculationData,
    *,
    fwhm_cm1: float = DEFAULT_FWHM_CM1,
    frequency_min_cm1: float | None = None,
    frequency_max_cm1: float | None = None,
    points: int | None = None,
) -> ResultRecord:
    """Return source IR sticks and a peak-height-preserving Gaussian curve."""

    return _spectrum(
        data,
        spectrum_type="ir",
        strength_getter=lambda mode: mode.ir_intensity_km_mol,
        strength_name="intensity",
        strength_unit="km/mol",
        fwhm_cm1=fwhm_cm1,
        frequency_min_cm1=frequency_min_cm1,
        frequency_max_cm1=frequency_max_cm1,
        points=points,
    )


def raman_spectrum(
    data: CalculationData,
    *,
    fwhm_cm1: float = DEFAULT_FWHM_CM1,
    frequency_min_cm1: float | None = None,
    frequency_max_cm1: float | None = None,
    points: int | None = None,
) -> ResultRecord:
    """Return source Raman activities and a broadened activity curve."""

    return _spectrum(
        data,
        spectrum_type="raman",
        strength_getter=lambda mode: mode.raman_activity_a4_amu,
        strength_name="activity",
        strength_unit="angstrom^4/amu",
        fwhm_cm1=fwhm_cm1,
        frequency_min_cm1=frequency_min_cm1,
        frequency_max_cm1=frequency_max_cm1,
        points=points,
    )


def normal_mode(data: CalculationData, *, mode: int) -> ResultRecord:
    """Return one source normal-mode displacement vector without rescaling."""

    record = get_vibrational_record(data)
    if isinstance(mode, bool) or not isinstance(mode, int) or mode < 1 or mode > len(record.modes):
        raise ValueError(f"mode must be a one-based index between 1 and {len(record.modes)}")
    selected = record.modes[mode - 1]
    if selected.displacements is None:
        raise DataUnavailableError(f"Normal mode vectors are not available for mode {mode}.")
    return ResultRecord(
        kind="normal_mode",
        data={
            "mode": selected.index,
            "frequency_cm1": selected.frequency_cm1,
            "imaginary": selected.imaginary,
            "symmetry": selected.symmetry,
            "reduced_mass_amu": selected.reduced_mass_amu,
            "force_constant_mdyne_per_angstrom": selected.force_constant_mdyne_per_angstrom,
            "ir_intensity_km_mol": selected.ir_intensity_km_mol,
            "raman_activity_a4_amu": selected.raman_activity_a4_amu,
            "displacements": [list(vector) for vector in selected.displacements],
        },
        units={
            "frequency_cm1": "cm^-1",
            "reduced_mass_amu": "amu",
            "force_constant_mdyne_per_angstrom": "mDyne/angstrom",
            "ir_intensity_km_mol": "km/mol",
            "raman_activity_a4_amu": "angstrom^4/amu",
            "displacements": "source normal-mode Cartesian convention",
        },
        validation_status="Experimental",
    )
