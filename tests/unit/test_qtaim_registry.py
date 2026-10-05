from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from openwfn.analysis.qtaim import QTAIMSettings
from openwfn.analysis.registry import available_analyses, run_analysis
from openwfn.errors import DataUnavailableError
from openwfn.parsers.gaussian.fchk import parse_fchk

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / "examples" / "water" / "water.fchk"


def test_qtaim_analysis_is_registered() -> None:
    assert "qtaim" in available_analyses()


def test_qtaim_registry_payload_is_explicit_bounded_and_experimental() -> None:
    data = parse_fchk(WATER)
    settings = QTAIMSettings(
        max_iterations=12,
        max_seeds=16,
        max_pair_seeds=8,
        max_path_steps=64,
        max_stored_path_points=32,
    )

    result = run_analysis(data, "qtaim", settings=settings, include_bond_paths=False)

    assert result.kind == "qtaim_topology"
    assert result.validation_status == "Experimental"
    assert result.status == "partial"
    assert result.data["search_complete"] is False
    assert result.data["seed_count"] <= settings.max_seeds
    assert set(result.data["counts"]) == {"(3,-3)", "(3,-1)", "(3,+1)", "(3,+3)", "unclassified"}
    assert isinstance(result.data["topology_relation"], int)
    assert isinstance(result.data["topology_relation_satisfied"], bool)
    assert result.data["bond_paths"] == []
    assert result.data["settings"]["max_iterations"] == 12
    assert result.data["conventions"] == {
        "coordinates": "Cartesian bohr",
        "atom_indices": "zero-based",
        "critical_point_labels": "QTAIM rank/signature (3,signature)",
        "topology_relation": "N_NCP - N_BCP + N_RCP - N_CCP",
    }
    assert any("not exhaustive" in warning.lower() for warning in result.warnings)
    assert result.units["position_bohr"] == "bohr"
    assert result.units["rho"] == "electron/bohr^3"
    assert result.units["gradient_norm"] == "electron/bohr^4"
    assert result.units["hessian_eigenvalues"] == "electron/bohr^5"
    assert result.units["bond_path_length_bohr"] == "bohr"

    for point in result.data["critical_points"]:
        assert np.all(np.isfinite(np.asarray(point["position_bohr"], dtype=float)))
        assert np.isfinite(point["rho"])
        assert np.isfinite(point["gradient_norm"])
        assert np.all(np.isfinite(np.asarray(point["hessian_eigenvalues"], dtype=float)))


def test_qtaim_registry_rejects_missing_total_density_before_running() -> None:
    data = parse_fchk(WATER)
    without_density = replace(data, total_density=None)

    with pytest.raises(DataUnavailableError, match="total density"):
        run_analysis(without_density, "qtaim")


def test_qtaim_rejects_malformed_explicit_seed_array() -> None:
    data = parse_fchk(WATER)

    with pytest.raises(ValueError, match="shape"):
        run_analysis(data, "qtaim", seeds_bohr=np.zeros((2, 2)))
