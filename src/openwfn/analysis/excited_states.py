"""Source-faithful excited-state tables and UV-Vis post-processing."""

from __future__ import annotations

from math import isfinite

from ..constants import HC_EV_NM
from ..errors import DataUnavailableError
from ..excited_states import (
    ExcitedState,
    ExcitedStateCollection,
    ExcitedStateJob,
    get_excited_state_collection,
)
from ..model import CalculationData
from ..results import ResultRecord
from ..spectrum_math import gaussian_broaden

DEFAULT_UVVIS_FWHM_EV = 0.20


def _state_row(state: ExcitedState) -> dict[str, object]:
    return {
        "state": state.index,
        "source_state": state.source_state,
        "energy_ev": state.energy_ev,
        "wavelength_nm": state.wavelength_nm,
        "oscillator_strength": state.oscillator_strength,
        "transition_dipole": list(state.transition_dipole) if state.transition_dipole is not None else None,
        "transition_dipole_unit": state.transition_dipole_unit,
        "multiplicity": state.multiplicity,
        "symmetry": state.symmetry,
        "label": state.label,
        "spin_expectation": state.spin_expectation,
        "transition_kind": state.transition_kind,
        "contributions": [
            {
                "source_label": item.source_label,
                "target_label": item.target_label,
                "value": item.value,
                "quantity": item.quantity,
                "convention": item.convention,
                "spin": item.spin,
            }
            for item in state.contributions
        ],
        "amplitudes": [
            {
                "convention": block.convention,
                "count": len(block.values),
                "dimensions": list(block.dimensions),
                "spin_block": block.spin_block,
                "side": block.side,
                "nto_ready": block.nto_ready,
            }
            for block in state.amplitudes
        ],
        "diagnostics": {key: value for key, value in state.diagnostics},
    }


def _job_row(job: ExcitedStateJob) -> dict[str, object]:
    return {
        "job": job.index,
        "source_job_label": job.source_job_label,
        "source_program": job.source_program,
        "source_program_version": job.source_program_version,
        "method_family": job.method_family,
        "method_detail": job.method_detail,
        "reference_state": job.reference_state,
        "charge": job.charge,
        "multiplicity": job.multiplicity,
        "reference_energy_hartree": job.reference_energy_hartree,
        "state_count": len(job.states),
        "states": [_state_row(state) for state in job.states],
        "diagnostics": {key: value for key, value in job.diagnostics},
    }


def _collection(data: CalculationData) -> ExcitedStateCollection:
    return get_excited_state_collection(data)


def _select_job(collection: ExcitedStateCollection, job: int | None) -> ExcitedStateJob:
    if job is None:
        if len(collection.jobs) != 1:
            raise ValueError(
                "job must be supplied as a one-based index when multiple excited-state jobs are present"
            )
        return collection.jobs[0]
    if isinstance(job, bool) or not isinstance(job, int) or not 1 <= job <= len(collection.jobs):
        raise ValueError(
            f"job must be a one-based index between 1 and {len(collection.jobs)}"
        )
    return collection.jobs[job - 1]


def excited_states(data: CalculationData, *, job: int | None = None) -> ResultRecord:
    """Return source-reported excited states without spectrum simulation."""

    collection = _collection(data)
    jobs = collection.jobs if job is None else (_select_job(collection, job),)
    return ResultRecord(
        kind="excited_states",
        data={
            "job_count": len(collection.jobs),
            "selected_job": job,
            "jobs": [_job_row(item) for item in jobs],
        },
        units={
            "energy_ev": "eV",
            "wavelength_nm": "nm",
            "oscillator_strength": "dimensionless",
            "reference_energy_hartree": "hartree",
        },
        validation_status="Experimental",
    )


def excited_state(
    data: CalculationData,
    *,
    state: int,
    job: int | None = None,
) -> ResultRecord:
    """Return one one-based excited state from one explicit source job."""

    selected_job = _select_job(_collection(data), job)
    if (
        isinstance(state, bool)
        or not isinstance(state, int)
        or not 1 <= state <= len(selected_job.states)
    ):
        raise ValueError(
            f"state must be a one-based index between 1 and {len(selected_job.states)}"
        )
    row = _state_row(selected_job.states[state - 1])
    row.update(
        {
            "job": selected_job.index,
            "source_program": selected_job.source_program,
            "method_family": selected_job.method_family,
            "method_detail": selected_job.method_detail,
        }
    )
    return ResultRecord(
        kind="excited_state",
        data=row,
        units={
            "energy_ev": "eV",
            "wavelength_nm": "nm",
            "oscillator_strength": "dimensionless",
            "transition_dipole": selected_job.states[state - 1].transition_dipole_unit
            or "unavailable",
        },
        validation_status="Experimental",
    )


def transition_dipoles(
    data: CalculationData,
    *,
    job: int | None = None,
) -> ResultRecord:
    """Return only source-reported transition dipoles; never infer missing vectors."""

    selected_job = _select_job(_collection(data), job)
    rows = [
        {
            "state": state.index,
            "source_state": state.source_state,
            "energy_ev": state.energy_ev,
            "transition_dipole": list(state.transition_dipole),
            "unit": state.transition_dipole_unit,
        }
        for state in selected_job.states
        if state.transition_dipole is not None
    ]
    if not rows:
        raise DataUnavailableError("Transition dipoles are not available for this excited-state job.")
    return ResultRecord(
        kind="transition_dipoles",
        data={"job": selected_job.index, "dipoles": rows},
        units={"energy_ev": "eV", "transition_dipole": "source-reported unit"},
        validation_status="Experimental",
    )


def _line_eligibility(state: ExcitedState) -> tuple[bool, str | None]:
    if state.energy_ev <= 0.0:
        return False, "nonpositive excitation energy"
    if state.oscillator_strength is None:
        return False, "oscillator strength unavailable"
    if state.oscillator_strength < 0.0:
        return False, "negative oscillator strength"
    return True, None


def uvvis_spectrum(
    data: CalculationData,
    *,
    job: int | None = None,
    fwhm_ev: float = DEFAULT_UVVIS_FWHM_EV,
    energy_min_ev: float | None = None,
    energy_max_ev: float | None = None,
    points: int | None = None,
    include_wavelength: bool = True,
) -> ResultRecord:
    """Return source UV-Vis sticks and a peak-height Gaussian curve in energy space."""

    selected_job = _select_job(_collection(data), job)
    if not isfinite(fwhm_ev) or fwhm_ev <= 0.0:
        raise ValueError("FWHM must be a positive finite value")
    lines: list[dict[str, object]] = []
    centers: list[float] = []
    strengths: list[float] = []
    excluded_missing = 0
    excluded_negative = 0
    excluded_energy = 0

    for state in selected_job.states:
        eligible, reason = _line_eligibility(state)
        lines.append(
            {
                "state": state.index,
                "source_state": state.source_state,
                "energy_ev": state.energy_ev,
                "wavelength_nm": state.wavelength_nm,
                "oscillator_strength": state.oscillator_strength,
                "multiplicity": state.multiplicity,
                "symmetry": state.symmetry,
                "eligible": eligible,
                "exclusion_reason": reason,
            }
        )
        if eligible:
            assert state.oscillator_strength is not None
            centers.append(state.energy_ev)
            strengths.append(state.oscillator_strength)
        elif reason == "oscillator strength unavailable":
            excluded_missing += 1
        elif reason == "negative oscillator strength":
            excluded_negative += 1
        elif reason == "nonpositive excitation energy":
            excluded_energy += 1

    if not centers:
        raise DataUnavailableError(
            "No excited states with nonnegative source oscillator strength and positive excitation energy are available for a UV-Vis curve."
        )

    margin = max(0.5, 5.0 * float(fwhm_ev))
    grid, curve = gaussian_broaden(
        centers,
        strengths,
        fwhm=fwhm_ev,
        lower=energy_min_ev,
        upper=energy_max_ev,
        points=points,
        margin=margin,
        lower_floor=0.0,
        default_step=0.002,
    )

    result_data: dict[str, object] = {
        "spectrum_type": "uvvis",
        "quantity": "oscillator_strength_broadened",
        "job": selected_job.index,
        "lines": lines,
        "energy_ev": grid.tolist(),
        "intensity": curve.tolist(),
        "broadening": {"type": "gaussian", "fwhm_ev": float(fwhm_ev)},
        "energy_range_ev": [float(grid[0]), float(grid[-1])],
    }
    if include_wavelength:
        positive = grid > 0.0
        wavelength_grid = grid[positive]
        wavelength_curve = curve[positive]
        wavelength = HC_EV_NM / wavelength_grid[::-1]
        transformed = wavelength_curve[::-1] * HC_EV_NM / wavelength**2
        result_data["wavelength_nm"] = wavelength.tolist()
        result_data["wavelength_intensity"] = transformed.tolist()
        result_data["wavelength_range_nm"] = [float(wavelength[0]), float(wavelength[-1])]

    warnings: list[str] = []
    if excluded_missing:
        warnings.append(
            f"{excluded_missing} source state(s) with unavailable oscillator strength were retained in stick data but excluded from the simulated curve."
        )
    if excluded_negative:
        warnings.append(
            f"{excluded_negative} source state(s) with negative oscillator strength were retained without clamping and excluded from the simulated curve."
        )
    if excluded_energy:
        warnings.append(
            f"{excluded_energy} source state(s) with nonpositive excitation energy were retained in state data but excluded from the simulated curve."
        )

    return ResultRecord(
        kind="uvvis_spectrum",
        data=result_data,
        units={
            "lines": "energy: eV; wavelength: nm; oscillator strength: dimensionless",
            "energy_ev": "eV",
            "intensity": "relative oscillator-strength peak height",
            "energy_range_ev": "eV",
            "broadening": "FWHM: eV",
            "wavelength_nm": "nm",
            "wavelength_intensity": "Jacobian-transformed relative intensity per nm",
            "wavelength_range_nm": "nm",
        },
        validation_status="Experimental",
        warnings=tuple(warnings),
    )
