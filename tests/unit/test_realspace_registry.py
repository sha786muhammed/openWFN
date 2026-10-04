from pathlib import Path

import numpy as np
import pytest

from openwfn.analysis.registry import available_analyses, run_analysis
from openwfn.api import load
from openwfn.parsers.gaussian.fchk import parse_fchk

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / "examples" / "water" / "water.fchk"
POINTS = np.array(((0.17, -0.23, 0.31), (0.42, 0.11, -0.28)), dtype=float)


def test_realspace_analyses_are_registered() -> None:
    analyses = available_analyses()

    assert "density-derivatives" in analyses
    assert "kinetic-energy-density" in analyses


def test_density_derivatives_registry_payload_is_explicit_and_finite() -> None:
    data = parse_fchk(WATER)

    result = run_analysis(
        data,
        "density-derivatives",
        points_bohr=POINTS,
        kind="total",
        chunk_size=1,
    )

    assert result.kind == "density_derivatives"
    assert result.validation_status == "Experimental"
    assert result.data["channel"] == "total"
    assert result.data["points_bohr"] == POINTS.tolist()
    assert result.data["derivative_convention"] == "analytic_cartesian_ao_product_rule"
    assert result.data["finite_mask"] == [True, True]
    assert len(result.data["rho"]) == 2
    assert np.asarray(result.data["gradient"]).shape == (2, 3)
    assert np.asarray(result.data["hessian"]).shape == (2, 3, 3)
    assert len(result.data["laplacian"]) == 2
    assert result.units == {
        "points_bohr": "bohr",
        "rho": "electron/bohr^3",
        "gradient": "electron/bohr^4",
        "hessian": "electron/bohr^5",
        "laplacian": "electron/bohr^5",
    }


def test_ked_registry_payload_names_positive_definite_convention() -> None:
    data = parse_fchk(WATER)

    result = run_analysis(
        data,
        "kinetic-energy-density",
        points_bohr=POINTS,
        kind="total",
        chunk_size=1,
    )

    assert result.kind == "kinetic_energy_density"
    assert result.validation_status == "Experimental"
    assert result.data == {
        "points_bohr": POINTS.tolist(),
        "channel": "total",
        "tau": result.data["tau"],
        "convention": "positive_definite_half_gradient_square",
        "finite_mask": [True, True],
    }
    assert len(result.data["tau"]) == 2
    assert result.units == {
        "points_bohr": "bohr",
        "tau": "hartree/bohr^3",
    }


def test_ked_registry_rejects_spin_difference_channel() -> None:
    data = parse_fchk(WATER)

    with pytest.raises(ValueError, match="total, alpha, or beta"):
        run_analysis(
            data,
            "kinetic-energy-density",
            points_bohr=POINTS,
            kind="spin",
        )


def test_registry_signature_rejects_unapproved_realspace_keywords() -> None:
    data = parse_fchk(WATER)

    with pytest.raises(TypeError, match="unexpected keyword argument"):
        run_analysis(
            data,
            "density-derivatives",
            points_bohr=POINTS,
            spacing_bohr=0.2,
        )


def test_loaded_python_api_analyze_matches_direct_registry_payload() -> None:
    direct_data = parse_fchk(WATER)
    calculation = load(WATER)

    direct_density = run_analysis(
        direct_data,
        "density-derivatives",
        points_bohr=POINTS,
        kind="total",
        chunk_size=1,
    )
    api_density = calculation.analyze(
        "density-derivatives",
        points_bohr=POINTS,
        kind="total",
        chunk_size=1,
    )
    direct_ked = run_analysis(
        direct_data,
        "kinetic-energy-density",
        points_bohr=POINTS,
        kind="total",
        chunk_size=1,
    )
    api_ked = calculation.analyze(
        "kinetic-energy-density",
        points_bohr=POINTS,
        kind="total",
        chunk_size=1,
    )

    assert api_density.data == direct_density.data
    assert api_density.units == direct_density.units
    assert api_ked.data == direct_ked.data
    assert api_ked.units == direct_ked.units
