from dataclasses import replace
from pathlib import Path

import pytest

from openwfn.data import wrap_calculation
from openwfn.excited_states import ExcitedState, ExcitedStateCollection, ExcitedStateJob
from openwfn.parsers.gaussian.fchk import parse_fchk


def _data(*, multi: bool = False):
    calculation = parse_fchk(Path("examples/water/water.fchk"))
    first = ExcitedStateJob(
        index=1,
        source_program="Gaussian",
        method_family="tddft",
        method_detail="TD(B3LYP)",
        states=(
            ExcitedState(index=1, source_state="1", energy_ev=4.0, oscillator_strength=0.2, transition_dipole=(0.1, 0.2, 0.3), transition_dipole_unit="au", multiplicity=1, symmetry="A1"),
            ExcitedState(index=2, source_state="2", energy_ev=5.0, oscillator_strength=0.0, multiplicity=3),
        ),
    )
    jobs = [first]
    if multi:
        jobs.append(
            ExcitedStateJob(
                index=2,
                source_program="Q-Chem",
                method_family="eom",
                method_detail="EOM-CCSD",
                states=(ExcitedState(index=1, source_state="1", energy_ev=6.0),),
            )
        )
    calculation = replace(
        calculation,
        records={**calculation.records, "excited_states": ExcitedStateCollection(tuple(jobs))},
    )
    return wrap_calculation(calculation)


def test_excited_states_lists_jobs_and_source_order() -> None:
    from openwfn.analysis.excited_states import excited_states

    result = excited_states(_data().calculation)
    assert result.kind == "excited_states"
    assert result.validation_status == "Experimental"
    assert result.data["job_count"] == 1
    assert [state["state"] for state in result.data["jobs"][0]["states"]] == [1, 2]
    assert result.data["jobs"][0]["states"][0]["oscillator_strength"] == pytest.approx(0.2)
    assert result.data["jobs"][0]["states"][1]["oscillator_strength"] == 0.0


def test_excited_state_selection_is_one_based_and_multi_job_is_explicit() -> None:
    from openwfn.analysis.excited_states import excited_state

    calculation = _data(multi=True).calculation
    with pytest.raises(ValueError, match="job"):
        excited_state(calculation, state=1)
    selected = excited_state(calculation, state=1, job=2)
    assert selected.data["job"] == 2
    assert selected.data["state"] == 1
    assert selected.data["energy_ev"] == pytest.approx(6.0)
    with pytest.raises(ValueError, match="one-based"):
        excited_state(calculation, state=0, job=1)


def test_transition_dipoles_returns_only_source_reported_vectors() -> None:
    from openwfn.analysis.excited_states import transition_dipoles

    result = transition_dipoles(_data().calculation)
    assert result.data["dipoles"] == [
        {"state": 1, "source_state": "1", "energy_ev": 4.0, "transition_dipole": [0.1, 0.2, 0.3], "unit": "au"}
    ]
