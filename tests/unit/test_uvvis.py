from dataclasses import replace

import numpy as np
import pytest

from openwfn.constants import HC_EV_NM
from openwfn.data import wrap_calculation
from openwfn.excited_states import ExcitedState, ExcitedStateCollection, ExcitedStateJob
from openwfn.parsers.gaussian.fchk import parse_fchk


def _data(states: tuple[ExcitedState, ...]):
    calculation = parse_fchk("examples/water/water.fchk")
    record = ExcitedStateCollection(
        (
            ExcitedStateJob(
                index=1,
                source_program="Gaussian",
                method_family="tddft",
                method_detail="TD(B3LYP)",
                states=states,
            ),
        )
    )
    calculation = replace(
        calculation,
        records={**calculation.records, "excited_states": record},
    )
    return wrap_calculation(calculation)


def test_uvvis_default_gaussian_has_expected_center_and_half_height() -> None:
    from openwfn.analysis.excited_states import uvvis_spectrum

    data = _data((ExcitedState(index=1, energy_ev=4.0, oscillator_strength=1.0),))
    result = uvvis_spectrum(
        data.calculation,
        energy_min_ev=3.8,
        energy_max_ev=4.2,
        points=401,
        include_wavelength=False,
    )
    energy = np.asarray(result.data["energy_ev"])
    intensity = np.asarray(result.data["intensity"])
    assert result.data["broadening"] == {"type": "gaussian", "fwhm_ev": 0.2}
    assert intensity[np.argmin(np.abs(energy - 4.0))] == pytest.approx(1.0)
    assert intensity[np.argmin(np.abs(energy - 3.9))] == pytest.approx(0.5, abs=1e-12)
    assert intensity[np.argmin(np.abs(energy - 4.1))] == pytest.approx(0.5, abs=1e-12)


def test_uvvis_preserves_all_source_lines_and_excludes_ineligible_curve_lines() -> None:
    from openwfn.analysis.excited_states import uvvis_spectrum

    states = (
        ExcitedState(index=1, energy_ev=4.0, oscillator_strength=0.2),
        ExcitedState(index=2, energy_ev=5.0, oscillator_strength=0.0),
        ExcitedState(index=3, energy_ev=6.0, oscillator_strength=None),
        ExcitedState(index=4, energy_ev=7.0, oscillator_strength=-0.1),
        ExcitedState(index=5, energy_ev=0.0, oscillator_strength=0.3),
    )
    result = uvvis_spectrum(_data(states).calculation, points=101)
    assert len(result.data["lines"]) == 5
    assert result.data["lines"][1]["eligible"] is True
    assert result.data["lines"][1]["oscillator_strength"] == 0.0
    assert result.data["lines"][2]["exclusion_reason"] == "oscillator strength unavailable"
    assert result.data["lines"][3]["exclusion_reason"] == "negative oscillator strength"
    assert result.data["lines"][4]["exclusion_reason"] == "nonpositive excitation energy"
    warning_text = " ".join(result.warnings).lower()
    assert "negative" in warning_text
    assert "missing" in warning_text or "unavailable" in warning_text


def test_uvvis_wavelength_curve_uses_jacobian_and_ascending_wavelength() -> None:
    from openwfn.analysis.excited_states import uvvis_spectrum

    result = uvvis_spectrum(
        _data((ExcitedState(index=1, energy_ev=4.0, oscillator_strength=1.0),)).calculation,
        energy_min_ev=3.8,
        energy_max_ev=4.2,
        points=5,
        include_wavelength=True,
    )
    energy = np.asarray(result.data["energy_ev"])
    intensity = np.asarray(result.data["intensity"])
    wavelength = np.asarray(result.data["wavelength_nm"])
    wavelength_intensity = np.asarray(result.data["wavelength_intensity"])
    assert np.all(np.diff(wavelength) > 0)
    expected_lambda = HC_EV_NM / energy[::-1]
    expected_intensity = intensity[::-1] * HC_EV_NM / expected_lambda**2
    assert wavelength == pytest.approx(expected_lambda)
    assert wavelength_intensity == pytest.approx(expected_intensity)


def test_uvvis_rejects_invalid_width_and_resource_heavy_grid() -> None:
    from openwfn.analysis.excited_states import uvvis_spectrum

    data = _data((ExcitedState(index=1, energy_ev=4.0, oscillator_strength=1.0),))
    with pytest.raises(ValueError, match="FWHM"):
        uvvis_spectrum(data.calculation, fwhm_ev=0.0)
    with pytest.raises(ValueError, match="100000"):
        uvvis_spectrum(data.calculation, points=100001)
