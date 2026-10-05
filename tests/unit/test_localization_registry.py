from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from openwfn.analysis.registry import available_analyses, run_analysis, run_analysis_safe
from openwfn.api import load
from openwfn.parsers.gaussian.fchk import parse_fchk

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / "examples" / "water" / "water.fchk"
POINTS = np.array(((0.17, -0.23, 0.31), (0.42, 0.11, -0.28)), dtype=float)


def _assert_common_localization_contract(result, *, kind: str) -> None:
    assert result.kind == kind
    assert result.validation_status == "Experimental"
    assert result.status == "success"
    assert result.data["channel"] == "total"
    assert result.data["points_bohr"] == POINTS.tolist()
    assert result.data["valid_mask"] == [True, True]
    assert len(result.data["values"]) == 2
    assert len(result.data["rho"]) == 2
    assert len(result.data["tau"]) == 2
    assert len(result.data["reference_ked"]) == 2
    assert result.data["density_floor"] == pytest.approx(1.0e-12)
    assert result.data["conventions"]["coordinates"] == "Cartesian bohr"
    assert (
        result.data["conventions"]["kinetic_energy_density"]
        == "positive_definite_half_gradient_square"
    )
    assert result.data["conventions"]["invalid_values"] == "null"
    assert result.data["conventions"]["homogeneous_electron_gas_reference"] == 0.5
    assert result.units["points_bohr"] == "bohr"
    assert result.units["values"] == "dimensionless"
    assert result.units["rho"] == "electron/bohr^3"
    assert result.units["tau"] == "hartree/bohr^3"
    assert result.units["reference_ked"] == "hartree/bohr^3"
    assert result.data["diagnostics"]["invalid_density_count"] == 0
    assert result.data["diagnostics"]["invalid_nonfinite_count"] == 0


def test_elf_and_lol_are_registered() -> None:
    analyses = available_analyses()

    assert "elf" in analyses
    assert "lol" in analyses


def test_elf_registry_payload_is_explicit_finite_and_reproducible() -> None:
    data = parse_fchk(WATER)

    result = run_analysis(data, "elf", points_bohr=POINTS, channel="total", chunk_size=1)

    _assert_common_localization_contract(
        result, kind="electron_localization_function"
    )
    assert result.data["conventions"]["descriptor"] == "Becke-Edgecombe ELF"
    assert result.data["conventions"]["spin_reference"] == "restricted_closed_shell_total"
    assert len(result.data["von_weizsaecker"]) == 2
    assert len(result.data["pauli_excess"]) == 2
    assert result.units["von_weizsaecker"] == "hartree/bohr^3"
    assert result.units["pauli_excess"] == "hartree/bohr^3"
    assert result.data["diagnostics"]["invalid_pauli_count"] == 0
    assert all(value is not None for value in result.data["values"])


def test_lol_registry_payload_is_explicit_finite_and_reproducible() -> None:
    data = parse_fchk(WATER)

    result = run_analysis(data, "lol", points_bohr=POINTS, channel="total", chunk_size=1)

    _assert_common_localization_contract(result, kind="localized_orbital_locator")
    assert result.data["conventions"]["descriptor"] == "Schmider-Becke LOL"
    assert result.data["conventions"]["spin_reference"] == "restricted_closed_shell_total"
    assert result.data["diagnostics"]["invalid_ked_count"] == 0
    assert all(value is not None for value in result.data["values"])


def test_invalid_tail_points_are_null_partial_and_never_nan() -> None:
    data = parse_fchk(WATER)
    points = np.array(((5.0, 0.0, 0.0),), dtype=float)

    for name in ("elf", "lol"):
        result = run_analysis(
            data,
            name,
            points_bohr=points,
            channel="total",
            density_floor=1.0e6,
        )
        payload = result.as_dict()

        assert result.status == "partial"
        assert result.data["values"] == [None]
        assert result.data["valid_mask"] == [False]
        assert result.data["diagnostics"]["invalid_density_count"] == 1
        assert result.warnings
        assert "nan" not in repr(payload).lower()


def test_open_shell_total_failure_remains_structured_through_safe_registry() -> None:
    data = parse_fchk(WATER)
    data = replace(
        data,
        records={
            **data.records,
            "Number of alpha electrons": 5,
            "Number of beta electrons": 4,
        },
    )

    result = run_analysis_safe(data, "elf", points_bohr=POINTS, channel="total")

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.category == "ValueError"
    assert "restricted closed-shell" in result.error.message


def test_registry_signature_rejects_unapproved_localization_keywords() -> None:
    data = parse_fchk(WATER)

    with pytest.raises(TypeError, match="unexpected keyword argument"):
        run_analysis(data, "elf", points_bohr=POINTS, spacing_bohr=0.2)


def test_loaded_python_api_matches_direct_registry_payload() -> None:
    direct_data = parse_fchk(WATER)
    calculation = load(WATER)

    for name in ("elf", "lol"):
        direct = run_analysis(
            direct_data, name, points_bohr=POINTS, channel="total", chunk_size=1
        )
        api = calculation.analyze(
            name, points_bohr=POINTS, channel="total", chunk_size=1
        )
        assert api.data == direct.data
        assert api.units == direct.units
        assert api.validation_status == "Experimental"
