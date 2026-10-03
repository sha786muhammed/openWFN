from pathlib import Path

import pytest

from openwfn.excited_states import get_excited_state_collection
from openwfn.model import CalculationData
from openwfn.parsers.gaussian.output import parse_gaussian_output

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "gaussian" / "excited"


def _parse_collection(name: str):
    from openwfn.parsers.excited.gaussian import parse_gaussian_excited_states

    return parse_gaussian_excited_states((FIXTURES / name).read_text(encoding="utf-8"))


def test_gaussian_tddft_state_fidelity() -> None:
    collection = _parse_collection("tddft_states.log")

    assert collection is not None
    assert len(collection.jobs) == 1
    job = collection.jobs[0]
    assert job.index == 1
    assert job.source_program == "Gaussian"
    assert job.method_family == "tddft"
    assert "TD" in job.method_detail.upper()
    assert job.charge == 0
    assert job.multiplicity == 1
    assert job.reference_energy_hartree == pytest.approx(-76.4212345678)
    assert job.atomic_numbers == (8, 1, 1)
    assert job.coordinates_angstrom[0] == pytest.approx((0.0, 0.0, 0.11779))

    first, second = job.states
    assert first.source_state == "1"
    assert first.energy_ev == pytest.approx(4.0)
    assert first.wavelength_nm == pytest.approx(309.96049608300065)
    assert first.oscillator_strength == pytest.approx(0.1)
    assert first.multiplicity == 1
    assert first.symmetry == "A1"
    assert first.spin_expectation == pytest.approx(0.0)
    assert first.transition_dipole == pytest.approx((0.1, 0.2, 0.3))
    assert first.transition_dipole_unit == "au"
    assert [item.value for item in first.contributions] == pytest.approx([0.7, -0.1])
    assert [item.quantity for item in first.contributions] == ["coefficient", "coefficient"]
    assert second.oscillator_strength == 0.0
    assert second.multiplicity == 3
    assert second.symmetry == "B1"
    assert second.transition_dipole == pytest.approx((0.0, 0.0, 0.0))


def test_gaussian_cis_dark_state_preserves_zero_strength() -> None:
    collection = _parse_collection("cis_dark.log")

    assert collection is not None
    job = collection.jobs[0]
    assert job.method_family == "cis"
    assert len(job.states) == 1
    assert job.states[0].oscillator_strength == 0.0


def test_gaussian_link1_excited_job_does_not_inherit_later_metadata() -> None:
    collection = _parse_collection("link1_excited_then_sp.log")

    assert collection is not None
    assert len(collection.jobs) == 1
    job = collection.jobs[0]
    assert job.charge == 0
    assert job.multiplicity == 1
    assert job.reference_energy_hartree == pytest.approx(-76.4212345678)
    assert job.coordinates_angstrom[0] == pytest.approx((0.0, 0.0, 0.11779))
    assert "TD" in job.method_detail.upper()

    parsed = parse_gaussian_output(FIXTURES / "link1_excited_then_sp.log")
    assert isinstance(parsed, CalculationData)
    assert parsed.molecule.charge == 0
    assert parsed.molecule.multiplicity == 1
    assert parsed.molecule.atoms[0].coordinates == pytest.approx((0.0, 0.0, 0.11779))
    attached = get_excited_state_collection(parsed)
    assert attached.jobs[0].states[0].energy_ev == pytest.approx(4.1)


def test_gaussian_nonfinite_state_value_is_rejected() -> None:
    with pytest.raises(ValueError, match="finite"):
        _parse_collection("malformed_state.log")


def test_gaussian_without_excited_states_returns_none() -> None:
    from openwfn.parsers.excited.gaussian import parse_gaussian_excited_states

    assert parse_gaussian_excited_states(" Entering Gaussian System\n SCF Done: E(RHF) = -1.0\n") is None


def test_gaussian_parser_enforces_state_limit_before_record_construction() -> None:
    from openwfn.parsers.excited.gaussian import parse_gaussian_excited_states

    from openwfn.excited_states import MAX_EXCITED_STATES_PER_JOB

    header = (
        " Entering Gaussian System\n"
        " #P TD B3LYP/6-31G\n"
        " Charge = 0 Multiplicity = 1\n"
    )
    states = "".join(
        f" Excited State {index}: Singlet-A1 4.0 eV 309.9 nm f=0.1 <S**2>=0.0\n"
        for index in range(1, MAX_EXCITED_STATES_PER_JOB + 2)
    )

    with pytest.raises(ValueError, match="state limit"):
        parse_gaussian_excited_states(header + states)
