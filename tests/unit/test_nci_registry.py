import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

import openwfn.analysis.nci as nci_module
from openwfn.analysis.registry import available_analyses, run_analysis, run_analysis_safe
from openwfn.model import CalculationMetadata
from openwfn.parsers.gaussian.fchk import parse_fchk

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / "examples" / "water" / "water.fchk"
POINTS = np.array(((0.17, -0.23, 0.31), (0.42, 0.11, -0.28)), dtype=float)


def test_nci_is_registered() -> None:
    assert "nci" in available_analyses()


def test_nci_registry_payload_is_explicit_finite_and_reproducible() -> None:
    data = parse_fchk(WATER)

    result = run_analysis(data, "nci", points_bohr=POINTS, chunk_size=1)

    assert result.kind == "nci_rdg"
    assert result.validation_status == "Experimental"
    assert result.status == "success"
    assert result.data["points_bohr"] == POINTS.tolist()
    assert len(result.data["rho"]) == 2
    assert len(result.data["gradient_norm"]) == 2
    assert len(result.data["rdg"]) == 2
    assert len(result.data["hessian_eigenvalues"]) == 2
    assert len(result.data["lambda2"]) == 2
    assert len(result.data["signed_density"]) == 2
    assert result.data["rdg_valid_mask"] == [True, True]
    assert result.data["field_valid_mask"] == [True, True]
    assert result.data["thresholds"] == {
        "density_floor": pytest.approx(1.0e-12),
        "hessian_antisymmetry_tolerance": pytest.approx(1.0e-10),
        "lambda2_ambiguity_absolute_tolerance": pytest.approx(1.0e-12),
        "lambda2_ambiguity_relative_tolerance": pytest.approx(1.0e-10),
    }
    assert result.data["density_source"] == data.total_density.source
    assert result.data["conventions"]["coordinates"] == "Cartesian bohr"
    assert result.data["conventions"]["density_channel"] == "total"
    assert result.data["conventions"]["rdg_formula"] == (
        "|grad(rho)|/[2(3*pi^2)^(1/3)rho^(4/3)]"
    )
    assert result.data["conventions"]["hessian_eigenvalue_order"] == "ascending algebraic"
    assert result.data["conventions"]["signed_density_formula"] == "sign(lambda2)*rho"
    assert result.data["conventions"]["invalid_values"] == "null"
    assert result.units["points_bohr"] == "bohr"
    assert result.units["rho"] == "electron/bohr^3"
    assert result.units["gradient_norm"] == "electron/bohr^4"
    assert result.units["rdg"] == "dimensionless"
    assert result.units["hessian_eigenvalues"] == "electron/bohr^5"
    assert result.units["lambda2"] == "electron/bohr^5"
    assert result.units["signed_density"] == "electron/bohr^3"
    assert result.units["hessian_antisymmetry_residual"] == "electron/bohr^5"
    json.dumps(result.as_dict(), allow_nan=False)


def test_low_density_point_is_partial_null_and_strict_json_safe() -> None:
    data = parse_fchk(WATER)
    settings = nci_module.NCISettings(density_floor=1.0e6)

    result = run_analysis(
        data,
        "nci",
        points_bohr=np.array(((5.0, 0.0, 0.0),), dtype=float),
        settings=settings,
    )

    assert result.status == "partial"
    assert result.data["rdg"] == [None]
    assert result.data["rdg_valid_mask"] == [False]
    assert result.data["field_valid_mask"] == [False]
    assert result.data["diagnostics"]["invalid_density_count"] == 1
    assert result.warnings
    json.dumps(result.as_dict(), allow_nan=False)


def test_lambda2_ambiguity_is_nonfatal_interpretive_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    data = parse_fchk(WATER)
    batch = nci_module.compute_nci_components(
        np.array([0.5]),
        np.zeros((1, 3)),
        np.diag([-2.0, 0.0, 1.0])[None, :, :],
        settings=nci_module.NCISettings(),
    )

    monkeypatch.setattr(nci_module, "evaluate_nci", lambda *args, **kwargs: batch)
    result = nci_module.nci(data, points_bohr=np.zeros((1, 3)))

    assert result.status == "success"
    assert result.data["lambda2_sign_ambiguous_mask"] == [True]
    assert result.data["signed_density"] == [0.0]
    assert any("ambiguous" in warning.lower() for warning in result.warnings)


def test_post_hf_scf_density_source_is_explicitly_warned() -> None:
    data = parse_fchk(WATER)
    assert data.total_density is not None
    data = replace(
        data,
        molecule=replace(
            data.molecule,
            metadata=CalculationMetadata(
                source_program=data.molecule.metadata.source_program,
                route=data.molecule.metadata.route,
                method="MP2",
                basis=data.molecule.metadata.basis,
                energy_hartree=data.molecule.metadata.energy_hartree,
                terminated_normally=data.molecule.metadata.terminated_normally,
                source_program_version=data.molecule.metadata.source_program_version,
            ),
        ),
        total_density=replace(data.total_density, source="scf"),
    )

    result = run_analysis(data, "nci", points_bohr=POINTS)

    assert result.data["density_source"] == "scf"
    assert any("SCF density" in warning for warning in result.warnings)


def test_nci_registry_signature_rejects_unapproved_keywords() -> None:
    data = parse_fchk(WATER)

    with pytest.raises(TypeError, match="unexpected keyword argument"):
        run_analysis(data, "nci", points_bohr=POINTS, spacing_bohr=0.2)


def test_safe_registry_returns_structured_failure_for_missing_basis() -> None:
    data = parse_fchk(WATER)
    data = replace(data, basis=None)

    result = run_analysis_safe(data, "nci", points_bohr=POINTS)

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.category == "DataUnavailableError"
