from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "qchem" / "excited"


def _parse(name: str):
    from openwfn.parsers.excited.qchem import parse_qchem_excited_states

    return parse_qchem_excited_states((FIXTURES / name).read_text(encoding="utf-8"))


def test_qchem_tddft_fidelity() -> None:
    collection = _parse("tddft.out")
    assert collection is not None
    job = collection.jobs[0]
    assert job.source_program == "Q-Chem"
    assert job.method_family == "tddft"
    assert "B3LYP" in job.method_detail
    assert job.charge == 0
    assert job.multiplicity == 1
    assert job.atomic_numbers == (8, 1, 1)
    assert job.reference_energy_hartree == pytest.approx(-76.31)
    first, second = job.states
    assert first.energy_ev == pytest.approx(4.12)
    assert first.oscillator_strength == pytest.approx(0.12)
    assert first.transition_dipole == pytest.approx((0.1, 0.2, 0.3))
    assert first.multiplicity == 1
    assert second.oscillator_strength == 0.0
    assert second.multiplicity == 3


def test_qchem_eom_preserves_missing_optical_data() -> None:
    collection = _parse("eom.out")
    assert collection is not None
    job = collection.jobs[0]
    assert job.method_family == "eom"
    assert [state.energy_ev for state in job.states] == pytest.approx([5.442277, 6.258618])
    assert [state.oscillator_strength for state in job.states] == [None, None]


def test_qchem_adc_transition_properties() -> None:
    collection = _parse("adc.out")
    assert collection is not None
    job = collection.jobs[0]
    assert job.method_family == "adc"
    state = job.states[0]
    assert state.energy_ev == pytest.approx(4.75)
    assert state.oscillator_strength == pytest.approx(0.045)
    assert state.transition_dipole == pytest.approx((0.15, 0.05, 0.0))


def test_qchem_unknown_method_falls_back_without_invention() -> None:
    collection = _parse("unknown.out")
    assert collection is not None
    job = collection.jobs[0]
    assert job.method_family == "other"
    assert "MYSTERY-EXCITED" in job.method_detail
    assert job.states[0].oscillator_strength is None


def test_qchem_multi_job_roots_remain_separate() -> None:
    collection = _parse("multi_job.out")
    assert collection is not None
    assert len(collection.jobs) == 2
    assert collection.jobs[0].states[0].source_state == "1"
    assert collection.jobs[1].states[0].source_state == "1"
    assert collection.jobs[0].method_family == "tddft"
    assert collection.jobs[1].method_family == "eom"
    assert collection.jobs[0].charge == 0
    assert collection.jobs[1].charge == 1


def test_qchem_parser_enforces_state_limit_before_record_construction() -> None:
    from openwfn.excited_states import MAX_EXCITED_STATES_PER_JOB
    from openwfn.parsers.excited.qchem import parse_qchem_excited_states

    text = "Q-Chem 6.3\n$rem\nMETHOD EOM-CCSD\n$end\n" + "".join(
        f"Excited state {index}: excitation energy (eV) = 5.0\n"
        for index in range(1, MAX_EXCITED_STATES_PER_JOB + 2)
    )
    with pytest.raises(ValueError, match="state limit"):
        parse_qchem_excited_states(text)
