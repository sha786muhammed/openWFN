from pathlib import Path

import numpy as np
import pytest

from openwfn.analysis.registry import run_analysis_safe
from openwfn.capabilities import infer_capabilities
from openwfn.data import wrap_calculation
from openwfn.model import CalculationData
from openwfn.parsers.gaussian.output import parse_gaussian_output


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "gaussian" / "vibrations"


def _calculation(name: str) -> CalculationData:
    parsed = parse_gaussian_output(FIXTURES / name)
    assert isinstance(parsed, CalculationData)
    return parsed


def test_single_line_gaussian_preserves_peak_and_fwhm() -> None:
    from openwfn.vibrational_services import broaden_lines

    x, y = broaden_lines(
        (1000.0,),
        (10.0,),
        fwhm_cm1=20.0,
        frequency_min_cm1=960.0,
        frequency_max_cm1=1040.0,
        points=81,
    )

    center = int(np.where(np.isclose(x, 1000.0))[0][0])
    left_half = int(np.where(np.isclose(x, 990.0))[0][0])
    right_half = int(np.where(np.isclose(x, 1010.0))[0][0])
    assert y[center] == pytest.approx(10.0)
    assert y[left_half] == pytest.approx(5.0)
    assert y[right_half] == pytest.approx(5.0)
    assert y == pytest.approx(y[::-1])


def test_multiline_broadening_is_linear_superposition() -> None:
    from openwfn.vibrational_services import broaden_lines

    kwargs = {
        "fwhm_cm1": 20.0,
        "frequency_min_cm1": 900.0,
        "frequency_max_cm1": 1200.0,
        "points": 301,
    }
    x, combined = broaden_lines((1000.0, 1100.0), (8.0, 3.0), **kwargs)
    x1, first = broaden_lines((1000.0,), (8.0,), **kwargs)
    x2, second = broaden_lines((1100.0,), (3.0,), **kwargs)

    assert x == pytest.approx(x1)
    assert x == pytest.approx(x2)
    assert combined == pytest.approx(first + second)


def test_broadening_rejects_invalid_or_excessive_grid_requests() -> None:
    from openwfn.vibrational_services import MAX_SPECTRUM_POINTS, broaden_lines

    with pytest.raises(ValueError, match="FWHM"):
        broaden_lines((1000.0,), (1.0,), fwhm_cm1=0.0)
    with pytest.raises(ValueError, match="range"):
        broaden_lines(
            (1000.0,),
            (1.0,),
            fwhm_cm1=20.0,
            frequency_min_cm1=1100.0,
            frequency_max_cm1=900.0,
        )
    with pytest.raises(ValueError, match="points"):
        broaden_lines((1000.0,), (1.0,), fwhm_cm1=20.0, points=1)
    with pytest.raises(ValueError, match="points"):
        broaden_lines(
            (1000.0,),
            (1.0,),
            fwhm_cm1=20.0,
            points=MAX_SPECTRUM_POINTS + 1,
        )


def test_vibrational_capabilities_reflect_only_present_source_data() -> None:
    complete = infer_capabilities(wrap_calculation(_calculation("water_freq.log")))
    no_raman = infer_capabilities(wrap_calculation(_calculation("no_raman.log")))
    no_vectors = infer_capabilities(wrap_calculation(_calculation("no_vectors.log")))

    assert complete["vibrations"].state == "available"
    assert complete["ir_intensities"].state == "available"
    assert complete["raman_activities"].state == "available"
    assert complete["normal_mode_vectors"].state == "available"
    assert no_raman["raman_activities"].state == "missing"
    assert no_vectors["normal_mode_vectors"].state == "missing"


def test_vibrations_result_preserves_source_mode_table() -> None:
    result = run_analysis_safe(_calculation("water_freq.log"), "vibrations")

    assert result.status == "success"
    assert result.validation_status == "Experimental"
    assert result.data["mode_count"] == 3
    assert result.data["imaginary_mode_count"] == 0
    assert result.data["ir_available"] is True
    assert result.data["raman_available"] is True
    assert result.data["displacements_available"] is True
    assert result.data["modes"][0]["frequency_cm1"] == pytest.approx(1595.1234)
    assert result.data["modes"][0]["ir_intensity_km_mol"] == pytest.approx(100.0)
    assert "displacements" not in result.data["modes"][0]


def test_ir_and_raman_spectra_return_sticks_and_broadened_arrays() -> None:
    calculation = _calculation("water_freq.log")
    ir = run_analysis_safe(calculation, "ir-spectrum", fwhm_cm1=20.0, points=401)
    raman = run_analysis_safe(calculation, "raman-spectrum", fwhm_cm1=20.0, points=401)

    assert ir.status == "success"
    assert ir.validation_status == "Experimental"
    assert ir.data["spectrum_type"] == "ir"
    assert ir.data["lines"][0]["frequency_cm1"] == pytest.approx(1595.1234)
    assert ir.data["lines"][0]["intensity"] == pytest.approx(100.0)
    assert len(ir.data["frequency_cm1"]) == 401
    assert len(ir.data["intensity"]) == 401
    assert ir.data["broadening"] == {"type": "gaussian", "fwhm_cm1": 20.0}

    assert raman.status == "success"
    assert raman.data["spectrum_type"] == "raman"
    assert raman.data["quantity"] == "raman_activity"
    assert raman.data["lines"][0]["activity"] == pytest.approx(10.0)
    assert len(raman.data["frequency_cm1"]) == 401
    assert len(raman.data["intensity"]) == 401


def test_imaginary_mode_is_preserved_but_excluded_from_broadened_spectrum() -> None:
    result = run_analysis_safe(_calculation("imaginary_freq.log"), "ir-spectrum", points=301)

    assert result.status == "success"
    assert result.data["lines"][0]["frequency_cm1"] == pytest.approx(-512.25)
    assert result.data["lines"][0]["imaginary"] is True
    assert result.data["excluded_imaginary_modes"] == [1]
    assert min(result.data["frequency_cm1"]) >= 0.0
    assert any("imaginary" in warning.lower() for warning in result.warnings)


def test_missing_source_quantities_fail_explicitly() -> None:
    no_raman = run_analysis_safe(_calculation("no_raman.log"), "raman-spectrum")
    no_vectors = run_analysis_safe(_calculation("no_vectors.log"), "normal-mode", mode=1)
    invalid_mode = run_analysis_safe(_calculation("water_freq.log"), "normal-mode", mode=99)

    assert no_raman.status == "failed"
    assert no_raman.validation_status == "Unsupported"
    assert no_raman.error is not None
    assert "raman" in no_raman.error.message.lower()

    assert no_vectors.status == "failed"
    assert no_vectors.validation_status == "Unsupported"
    assert no_vectors.error is not None
    assert "normal mode vectors" in no_vectors.error.message.lower()

    assert invalid_mode.status == "failed"
    assert invalid_mode.error is not None
    assert "mode" in invalid_mode.error.message.lower()


def test_normal_mode_returns_source_vectors_without_rescaling() -> None:
    result = run_analysis_safe(_calculation("water_freq.log"), "normal-mode", mode=1)

    assert result.status == "success"
    assert result.data["mode"] == 1
    assert result.data["frequency_cm1"] == pytest.approx(1595.1234)
    assert result.data["displacements"][0] == pytest.approx([0.0, 0.0, 0.1])
    assert len(result.data["displacements"]) == 3
