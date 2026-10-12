from dataclasses import replace
from pathlib import Path

import pytest

from openwfn.data import wrap_calculation
from openwfn.excited_states import get_excited_state_collection
from openwfn.parsers.gaussian.fchk import parse_fchk

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "orca" / "excited"


def _parse(name: str):
    from openwfn.parsers.excited.orca import parse_orca_excited_states

    return parse_orca_excited_states((FIXTURES / name).read_text(encoding="utf-8"))


def test_orca_tddft_absorption_table_fidelity() -> None:
    collection = _parse("tddft_absorption.out")

    assert collection is not None
    job = collection.jobs[0]
    assert job.source_program == "ORCA"
    assert job.method_family == "tddft"
    assert "B3LYP" in job.method_detail
    assert job.charge == 0
    assert job.multiplicity == 1
    assert job.reference_energy_hartree == pytest.approx(-76.3)
    assert job.atomic_numbers == (8, 1, 1)
    assert job.coordinates_angstrom[0] == pytest.approx((0.0, 0.0, 0.11779))

    first, second = job.states
    assert first.source_state == "1-1A"
    assert first.energy_ev == pytest.approx(4.294795)
    assert first.oscillator_strength == pytest.approx(0.003830922)
    assert first.transition_dipole == pytest.approx((0.19012, 0.0, 0.0))
    assert first.transition_dipole_unit == "au"
    assert second.oscillator_strength == 0.0


def test_orca_standard_dotted_metadata_retains_charge_and_multiplicity():
    from openwfn.parsers.excited.orca import parse_orca_excited_states
    text = (FIXTURES / 'tddft_absorption.out').read_text()
    text = text.replace('Total Charge : 0', ' Total Charge           Charge          ....    0')
    text = text.replace('Multiplicity : 1', ' Multiplicity           Mult            ....    1')
    job = parse_orca_excited_states(text).jobs[0]
    assert job.charge == 0
    assert job.multiplicity == 1


def test_orca_numeric_absorption_uses_electric_table_and_preserves_forbidden_state():
    from openwfn.parsers.excited.orca import parse_orca_excited_states
    text = '''O   R   C   A
TD-DFT/TDA EXCITATION SPECTRA
Total Charge : 0
Multiplicity : 1
ABSORPTION SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS
State Energy Wavelength fosc T2 TX TY TZ
      (cm-1) (nm) (au**2) (au) (au) (au)
 1 40000.0 250.0 .02 .14 .1 .2 .3
 2 20000.0 500.0 spin forbidden (mult=3)

ABSORPTION SPECTRUM VIA TRANSITION VELOCITY DIPOLE MOMENTS
State Energy Wavelength fosc P2 PX PY PZ
      (cm-1) (nm) (au**2) (au) (au) (au)
 1 40000.0 250.0 1.99 .14 .1 .2 .3
'''
    states = parse_orca_excited_states(text).jobs[0].states
    assert len(states) == 2
    assert states[0].energy_ev == pytest.approx(4.95936793732801)
    assert states[0].oscillator_strength == .02
    assert states[0].transition_dipole == (.1, .2, .3)
    assert states[1].oscillator_strength is None
    assert states[1].multiplicity == 3


def test_orca_modern_absorption_does_not_duplicate_velocity_gauge_states():
    from openwfn.parsers.excited.orca import parse_orca_excited_states
    text = (FIXTURES / 'tddft_absorption.out').read_text()
    text += '''
ABSORPTION SPECTRUM VIA TRANSITION VELOCITY DIPOLE MOMENTS
0-1A -> 1-1A 4.294795 34639.9 288.7 9.0 .03615 .19012 0.0 0.0
'''
    states = parse_orca_excited_states(text).jobs[0].states
    assert len(states) == 2
    assert states[0].oscillator_strength == pytest.approx(.003830922)


def test_orca_malformed_first_numeric_state_cannot_be_silently_dropped():
    from openwfn.parsers.excited.orca import parse_orca_excited_states
    text = '''O   R   C   A
TD-DFT/TDA EXCITATION SPECTRA
ABSORPTION SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS
State Energy Wavelength fosc T2 TX TY TZ
      (cm-1) (nm) (au**2) (au) (au) (au)
 1 40000.0 250.0 BROKEN .14 .1 .2 .3
 2 20000.0 500.0 .01 .14 .1 .2 .3
'''
    with pytest.raises(ValueError, match='Malformed ORCA'):
        parse_orca_excited_states(text)


def test_orca_eom_states_remain_nonoptical_when_strength_not_reported() -> None:
    collection = _parse("eom_states.out")

    assert collection is not None
    job = collection.jobs[0]
    assert job.method_family == "eom"
    assert "EOM-CCSD" in job.method_detail
    assert [state.energy_ev for state in job.states] == pytest.approx([5.442277, 6.258618])
    assert [state.oscillator_strength for state in job.states] == [None, None]


def test_orca_casscf_transition_table_preserves_spin_and_symmetry() -> None:
    collection = _parse("casscf_states.out")

    assert collection is not None
    job = collection.jobs[0]
    assert job.method_family == "casscf"
    first, second = job.states
    assert first.source_state == "1"
    assert first.energy_ev == pytest.approx(4.456)
    assert first.multiplicity == 3
    assert first.symmetry == "B3u"
    assert second.multiplicity == 1
    assert second.symmetry == "Ag"


def test_orca_unknown_method_falls_back_without_inventing_optical_data() -> None:
    collection = _parse("unknown_states.out")

    assert collection is not None
    job = collection.jobs[0]
    assert job.method_family == "other"
    assert "MYSTERY-EXCITED" in job.method_detail
    assert job.states[0].energy_ev == pytest.approx(4.081708)
    assert job.states[0].oscillator_strength is None
    assert not job.states[0].amplitudes


def test_orca_repeated_root_numbers_are_separate_across_jobs() -> None:
    collection = _parse("multi_job.out")

    assert collection is not None
    assert len(collection.jobs) == 2
    assert collection.jobs[0].index == 1
    assert collection.jobs[1].index == 2
    assert collection.jobs[0].states[0].source_state == "1"
    assert collection.jobs[1].states[0].source_state == "1"
    assert collection.jobs[0].charge == 0
    assert collection.jobs[1].charge == 1
    assert collection.jobs[0].method_family == "tddft"
    assert collection.jobs[1].method_family == "eom"


def test_orca_attach_preserves_existing_wavefunction_and_records() -> None:
    from openwfn.parsers.excited.attach import attach_excited_states

    calculation = parse_fchk(ROOT / "examples" / "water" / "water.fchk")
    existing = replace(calculation, records={**calculation.records, "sentinel": "keep"})
    data = wrap_calculation(existing)
    collection = _parse("tddft_absorption.out")
    assert collection is not None

    attached = attach_excited_states(data, collection)

    assert attached.calculation is not None
    assert attached.calculation.basis is existing.basis
    assert attached.calculation.alpha_orbitals is existing.alpha_orbitals
    assert attached.calculation.records["sentinel"] == "keep"
    assert get_excited_state_collection(attached) is collection


def test_orca_parser_enforces_state_limit_before_record_construction() -> None:
    from openwfn.excited_states import MAX_EXCITED_STATES_PER_JOB
    from openwfn.parsers.excited.orca import parse_orca_excited_states

    text = "O   R   C   A\n! EOM-CCSD def2-SVP\n" + "".join(
        f"STATE {index}: E= 0.2 au 5.44 eV 43898 cm**-1\n"
        for index in range(1, MAX_EXCITED_STATES_PER_JOB + 2)
    )

    with pytest.raises(ValueError, match="state limit"):
        parse_orca_excited_states(text)
