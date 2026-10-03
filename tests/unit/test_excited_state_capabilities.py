from dataclasses import replace
from pathlib import Path

from openwfn.data import wrap_calculation
from openwfn.parsers.gaussian.fchk import parse_fchk

ROOT = Path(__file__).resolve().parents[2]


def test_excited_state_capabilities_follow_typed_record_contents() -> None:
    from openwfn.capabilities import infer_capabilities
    from openwfn.excited_states import (
        AmplitudeBlock,
        ExcitedState,
        ExcitedStateCollection,
        ExcitedStateJob,
        TransitionContribution,
    )

    calculation = parse_fchk(ROOT / "examples" / "water" / "water.fchk")
    record = ExcitedStateCollection(
        jobs=(
            ExcitedStateJob(
                index=1,
                source_program="Gaussian",
                method_family="tddft",
                method_detail="TD-B3LYP",
                states=(
                    ExcitedState(
                        index=1,
                        energy_ev=4.0,
                        oscillator_strength=0.1,
                        transition_dipole=(0.1, 0.2, 0.3),
                        transition_dipole_unit="au",
                        contributions=(
                            TransitionContribution(
                                source_label="HOMO",
                                target_label="LUMO",
                                value=0.8,
                                quantity="coefficient",
                                convention="source-reported",
                            ),
                        ),
                        amplitudes=(
                            AmplitudeBlock(
                                convention="vendor-specific-coefficient",
                                values=(0.8,),
                                indices=((5, 6),),
                            ),
                        ),
                    ),
                ),
            ),
        )
    )
    calculation = replace(
        calculation,
        records={**calculation.records, "excited_states": record},
    )

    capabilities = infer_capabilities(wrap_calculation(calculation))

    assert capabilities["excited_states"].state == "available"
    assert capabilities["optical_oscillator_strengths"].state == "available"
    assert capabilities["transition_dipoles"].state == "available"
    assert capabilities["excitation_contributions"].state == "available"
    assert capabilities["excitation_amplitudes"].state == "available"
    assert capabilities["nto_ready_amplitudes"].state == "missing"


def test_dark_state_counts_as_reported_optical_strength() -> None:
    from openwfn.capabilities import infer_capabilities
    from openwfn.excited_states import ExcitedState, ExcitedStateCollection, ExcitedStateJob

    calculation = parse_fchk(ROOT / "examples" / "water" / "water.fchk")
    record = ExcitedStateCollection(
        jobs=(
            ExcitedStateJob(
                index=1,
                source_program="ORCA",
                method_family="cis",
                method_detail="CIS",
                states=(ExcitedState(index=1, energy_ev=5.0, oscillator_strength=0.0),),
            ),
        )
    )
    calculation = replace(
        calculation,
        records={**calculation.records, "excited_states": record},
    )

    capabilities = infer_capabilities(wrap_calculation(calculation))
    assert capabilities["optical_oscillator_strengths"].state == "available"
