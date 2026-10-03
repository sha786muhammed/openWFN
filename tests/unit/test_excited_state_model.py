"""RED contract for the universal excited-state model."""

from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from openwfn.data import wrap_calculation
from openwfn.errors import DataUnavailableError
from openwfn.parsers.gaussian.fchk import parse_fchk

ROOT = Path(__file__).resolve().parents[2]


def _types():
    from openwfn.excited_states import (
        MAX_AMPLITUDES_PER_STATE,
        MAX_EXCITED_STATES_PER_JOB,
        AmplitudeBlock,
        ExcitedState,
        ExcitedStateCollection,
        ExcitedStateJob,
        TransitionContribution,
        get_excited_state_collection,
    )

    return (
        MAX_AMPLITUDES_PER_STATE,
        MAX_EXCITED_STATES_PER_JOB,
        AmplitudeBlock,
        ExcitedState,
        ExcitedStateCollection,
        ExcitedStateJob,
        TransitionContribution,
        get_excited_state_collection,
    )


def test_state_preserves_source_values_and_derives_positive_wavelength() -> None:
    _, _, _, ExcitedState, _, _, _, _ = _types()

    state = ExcitedState(
        index=1,
        energy_ev=4.0,
        source_state="S1",
        oscillator_strength=0.0,
        transition_dipole=(0.1, -0.2, 0.3),
        transition_dipole_unit="au",
        multiplicity=1,
        symmetry="A1",
        label="bright-state-label",
    )

    assert state.index == 1
    assert state.source_state == "S1"
    assert state.oscillator_strength == 0.0
    assert state.transition_dipole == (0.1, -0.2, 0.3)
    assert state.wavelength_nm == pytest.approx(309.96049608300065)


def test_nonpositive_energy_remains_representable_without_wavelength() -> None:
    _, _, _, ExcitedState, _, _, _, _ = _types()

    zero = ExcitedState(index=1, energy_ev=0.0)
    negative = ExcitedState(index=2, energy_ev=-0.25)

    assert zero.wavelength_nm is None
    assert negative.wavelength_nm is None


def test_state_rejects_nonfinite_energy_and_non_one_based_index() -> None:
    _, _, _, ExcitedState, _, _, _, _ = _types()

    with pytest.raises(ValueError, match="one-based"):
        ExcitedState(index=0, energy_ev=1.0)
    with pytest.raises(ValueError, match="finite"):
        ExcitedState(index=1, energy_ev=float("nan"))


def test_contribution_keeps_quantity_distinct_from_amplitude() -> None:
    _, _, _, _, _, _, TransitionContribution, _ = _types()

    contribution = TransitionContribution(
        source_label="HOMO",
        target_label="LUMO",
        value=72.0,
        quantity="percent",
        convention="source-reported configuration weight",
    )

    assert contribution.quantity == "percent"
    assert contribution.value == 72.0
    assert not hasattr(contribution, "nto_ready")


def test_unknown_amplitude_convention_is_representable_but_not_nto_ready() -> None:
    _, _, AmplitudeBlock, _, _, _, _, _ = _types()

    block = AmplitudeBlock(
        convention="vendor-specific-coefficient",
        values=(0.7, -0.2),
        indices=((5, 8), (6, 9)),
        spin_block="alpha",
        side="right",
    )

    assert block.convention == "vendor-specific-coefficient"
    assert block.nto_ready is False


def test_multiple_jobs_keep_repeated_source_state_numbers_separate() -> None:
    _, _, _, ExcitedState, ExcitedStateCollection, ExcitedStateJob, _, _ = _types()

    collection = ExcitedStateCollection(
        jobs=(
            ExcitedStateJob(
                index=1,
                source_program="Gaussian",
                method_family="tddft",
                method_detail="TD-B3LYP",
                states=(ExcitedState(index=1, energy_ev=3.1, source_state="1"),),
            ),
            ExcitedStateJob(
                index=2,
                source_program="Gaussian",
                method_family="cis",
                method_detail="CIS",
                states=(ExcitedState(index=1, energy_ev=5.2, source_state="1"),),
            ),
        )
    )

    assert collection.jobs[0].states[0].source_state == "1"
    assert collection.jobs[1].states[0].source_state == "1"
    assert collection.jobs[0].method_detail == "TD-B3LYP"
    assert collection.jobs[1].method_detail == "CIS"


def test_collection_requires_job_metadata_and_contiguous_one_based_indices() -> None:
    _, _, _, ExcitedState, ExcitedStateCollection, ExcitedStateJob, _, _ = _types()

    with pytest.raises(ValueError, match="source_program"):
        ExcitedStateJob(
            index=1,
            source_program="",
            method_family="other",
            method_detail="unknown",
            states=(ExcitedState(index=1, energy_ev=2.0),),
        )
    with pytest.raises(ValueError, match="contiguous"):
        ExcitedStateCollection(
            jobs=(
                ExcitedStateJob(
                    index=2,
                    source_program="ORCA",
                    method_family="other",
                    method_detail="Unknown method",
                    states=(ExcitedState(index=1, energy_ev=2.0),),
                ),
            )
        )


def test_records_are_frozen_and_tuple_backed() -> None:
    _, _, _, ExcitedState, _, ExcitedStateJob, _, _ = _types()

    state = ExcitedState(index=1, energy_ev=2.5)
    job = ExcitedStateJob(
        index=1,
        source_program="Q-Chem",
        method_family="tddft",
        method_detail="TDDFT",
        states=(state,),
    )

    assert isinstance(job.states, tuple)
    with pytest.raises(FrozenInstanceError):
        state.energy_ev = 3.0  # type: ignore[misc]


def test_amplitude_and_state_resource_limits_are_hard_bounds() -> None:
    (
        max_amplitudes,
        max_states,
        AmplitudeBlock,
        ExcitedState,
        _,
        ExcitedStateJob,
        _,
        _,
    ) = _types()

    with pytest.raises(ValueError, match="amplitude"):
        AmplitudeBlock(
            convention="test",
            values=(0.0,) * (max_amplitudes + 1),
        )

    state = ExcitedState(index=1, energy_ev=1.0)
    with pytest.raises(ValueError, match="state limit"):
        ExcitedStateJob(
            index=1,
            source_program="Gaussian",
            method_family="other",
            method_detail="test",
            states=(state,) * (max_states + 1),
        )


def test_get_collection_reads_typed_record_and_rejects_missing_record() -> None:
    _, _, _, ExcitedState, ExcitedStateCollection, ExcitedStateJob, _, getter = _types()

    calculation = parse_fchk(ROOT / "examples" / "water" / "water.fchk")
    collection = ExcitedStateCollection(
        jobs=(
            ExcitedStateJob(
                index=1,
                source_program="Gaussian",
                method_family="tddft",
                method_detail="TD-B3LYP",
                states=(ExcitedState(index=1, energy_ev=4.0, oscillator_strength=0.1),),
            ),
        )
    )
    with_record = replace(
        calculation,
        records={**calculation.records, "excited_states": collection},
    )

    assert getter(with_record) is collection
    assert getter(wrap_calculation(with_record)) is collection
    with pytest.raises(DataUnavailableError, match="excited-state"):
        getter(calculation)
