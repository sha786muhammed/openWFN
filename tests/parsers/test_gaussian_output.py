from pathlib import Path

import pytest

from openwfn.model import CalculationData
from openwfn.parsers.gaussian.output import parse_gaussian_output


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "gaussian" / "vibrations"


def test_gaussian_output_extracts_route_energy_and_status(tmp_path: Path) -> None:
    source = tmp_path / "water.log"
    source.write_text(
        " Entering Gaussian System\n"
        " #P B3LYP/6-31G(d) Opt\n"
        " ----------------------\n"
        " SCF Done:  E(RB3LYP) =  -76.4212345678 A.U. after 10 cycles\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    metadata = parse_gaussian_output(source)

    assert metadata.route == "#P B3LYP/6-31G(d) Opt"
    assert metadata.method == "B3LYP"
    assert metadata.basis == "6-31G(d)"
    assert metadata.energy_hartree == pytest.approx(-76.4212345678)
    assert metadata.terminated_normally is True


def test_vibrational_types_reject_invalid_mode_values() -> None:
    from openwfn.vibrational import VibrationalMode

    with pytest.raises(ValueError, match="mode index"):
        VibrationalMode(index=0, frequency_cm1=1000.0)
    with pytest.raises(ValueError, match="finite"):
        VibrationalMode(index=1, frequency_cm1=float("nan"))
    with pytest.raises(ValueError, match="three-component"):
        VibrationalMode(index=1, frequency_cm1=1000.0, displacements=((0.1, 0.2),))


def test_gaussian_frequency_output_uses_final_geometry_and_exact_source_values() -> None:
    from openwfn.vibrational import get_vibrational_record

    parsed = parse_gaussian_output(FIXTURES / "water_freq.log")

    assert isinstance(parsed, CalculationData)
    assert parsed.molecule.charge == 0
    assert parsed.molecule.multiplicity == 1
    assert parsed.molecule.atoms[0].coordinates == pytest.approx((0.0, 0.0, 0.11779))
    record = get_vibrational_record(parsed)
    assert [mode.index for mode in record.modes] == [1, 2, 3]
    assert [mode.frequency_cm1 for mode in record.modes] == pytest.approx(
        [1595.1234, 3657.4567, 3755.6789]
    )
    assert record.modes[0].reduced_mass_amu == pytest.approx(1.0823)
    assert record.modes[0].force_constant_mdyne_per_angstrom == pytest.approx(1.2345)
    assert record.modes[0].ir_intensity_km_mol == pytest.approx(100.0)
    assert record.modes[0].raman_activity_a4_amu == pytest.approx(10.0)
    assert record.modes[0].symmetry == "A1"
    assert record.modes[0].displacements[0] == pytest.approx((0.0, 0.0, 0.1))
    assert record.ir_available is True
    assert record.raman_available is True
    assert record.displacements_available is True


def test_gaussian_linear_frequency_output_preserves_four_modes() -> None:
    from openwfn.vibrational import get_vibrational_record

    parsed = parse_gaussian_output(FIXTURES / "co2_freq.log")
    assert isinstance(parsed, CalculationData)
    record = get_vibrational_record(parsed)

    assert len(parsed.molecule.atoms) == 3
    assert len(record.modes) == 4
    assert [mode.frequency_cm1 for mode in record.modes] == pytest.approx(
        [667.0, 667.0, 1333.0, 2349.0]
    )


def test_gaussian_imaginary_frequency_preserves_sign_and_flag() -> None:
    from openwfn.vibrational import get_vibrational_record

    parsed = parse_gaussian_output(FIXTURES / "imaginary_freq.log")
    assert isinstance(parsed, CalculationData)
    mode = get_vibrational_record(parsed).modes[0]

    assert mode.frequency_cm1 == pytest.approx(-512.25)
    assert mode.imaginary is True


def test_gaussian_missing_raman_is_unavailable_not_zero() -> None:
    from openwfn.vibrational import get_vibrational_record

    parsed = parse_gaussian_output(FIXTURES / "no_raman.log")
    assert isinstance(parsed, CalculationData)
    record = get_vibrational_record(parsed)

    assert record.ir_available is True
    assert record.raman_available is False
    assert all(mode.raman_activity_a4_amu is None for mode in record.modes)


def test_gaussian_missing_vectors_are_unavailable_not_empty() -> None:
    from openwfn.vibrational import get_vibrational_record

    parsed = parse_gaussian_output(FIXTURES / "no_vectors.log")
    assert isinstance(parsed, CalculationData)
    record = get_vibrational_record(parsed)

    assert record.displacements_available is False
    assert all(mode.displacements is None for mode in record.modes)


def test_gaussian_malformed_displacement_atom_count_is_rejected() -> None:
    with pytest.raises(ValueError, match="displacement"):
        parse_gaussian_output(FIXTURES / "malformed_vectors.log")
