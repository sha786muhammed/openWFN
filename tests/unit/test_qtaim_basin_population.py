from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
import pytest

from openwfn.analysis.atom_quadrature import AtomQuadratureChunk, AtomQuadratureSettings
from openwfn.analysis.qtaim import SearchDiagnostics
from openwfn.analysis.qtaim_basins import (
    BasinTrajectoryBatch,
    PreparedBasinAttractors,
    QTAIMBasinSettings,
)
from openwfn.constants import BOHR_TO_ANGSTROM
from openwfn.model import (
    Atom,
    BasisSet,
    BasisShell,
    CalculationData,
    CalculationMetadata,
    DensityMatrix,
    Molecule,
)


def _data(*, method: str = "RHF", density_source: str | None = "scf") -> CalculationData:
    atoms = (
        Atom(1, (-1.0 * BOHR_TO_ANGSTROM, 0.0, 0.0)),
        Atom(1, (1.0 * BOHR_TO_ANGSTROM, 0.0, 0.0)),
    )
    return CalculationData(
        molecule=Molecule(atoms, 0, 1, CalculationMetadata("fixture", method=method)),
        basis=BasisSet(
            (
                BasisShell(0, 0, (1.0,), (1.0,)),
                BasisShell(1, 0, (1.0,), (1.0,)),
            )
        ),
        total_density=DensityMatrix(((1.0, 0.0), (0.0, 1.0)), "total", source=density_source),
        records={"Number of electrons": 2.0},
    )


def _prepared() -> PreparedBasinAttractors:
    diagnostics = SearchDiagnostics(2, 2, 0, 2)
    positions = np.asarray(((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0)))
    return PreparedBasinAttractors(
        physical_nucleus_indices=(0, 1),
        nucleus_positions_bohr=positions.copy(),
        nuclear_charges=np.asarray((1.0, 1.0)),
        attractor_positions_bohr=positions.copy(),
        attractor_to_nucleus_distances_bohr=np.zeros(2),
        bounds=(np.full(3, -4.0), np.full(3, 4.0)),
        critical_points=(),
        search_diagnostics=diagnostics,
        search_complete=False,
        warnings=("bounded attractor search is not exhaustive",),
    )


def _chunk() -> AtomQuadratureChunk:
    return AtomQuadratureChunk(
        points_bohr=np.asarray(((-0.75, 0.0, 0.0), (0.75, 0.0, 0.0))),
        integration_weights=np.ones(2),
        # Deliberately opposite to QTAIM membership: owner must never define basin.
        owner_atom_indices=np.asarray((1, 0), dtype=np.int64),
        molecular_partition_weights=np.ones(2),
    )


def _flow(indices: tuple[int, int], statuses: tuple[str, str] = ("captured", "captured")) -> BasinTrajectoryBatch:
    return BasinTrajectoryBatch(
        basin_indices=np.asarray(indices, dtype=np.int64),
        attractor_indices=np.asarray(indices, dtype=np.int64),
        status=np.asarray(statuses, dtype=object),
        steps=np.asarray((2, 2), dtype=np.int64),
        final_points_bohr=np.asarray(((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0))),
        final_distances_bohr=np.zeros(2),
        path_lengths_bohr=np.asarray((0.25, 0.25)),
    )


def _install_synthetic(
    monkeypatch: pytest.MonkeyPatch,
    *,
    rho: tuple[float, float] = (1.0, 1.0),
    flow: BasinTrajectoryBatch | None = None,
) -> None:
    import openwfn.analysis.qtaim_basins as basins

    monkeypatch.setattr(basins, "prepare_qtaim_basin_attractors", lambda *args, **kwargs: _prepared())
    monkeypatch.setattr(basins, "iter_atom_centered_chunks", lambda *args, **kwargs: iter((_chunk(),)), raising=False)
    monkeypatch.setattr(
        basins,
        "evaluate_density",
        lambda *args, **kwargs: np.asarray(rho, dtype=float),
        raising=False,
    )
    monkeypatch.setattr(
        basins,
        "classify_basin_points",
        lambda *args, **kwargs: flow or _flow((0, 1)),
    )


def test_symmetric_two_attractor_density_integrates_half_population_per_basin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openwfn.analysis.qtaim_basins as basins

    _install_synthetic(monkeypatch)
    result = basins.qtaim_basins(_data())

    assert [atom["electron_population"] for atom in result.data["atoms"]] == [1.0, 1.0]
    assert [atom["net_charge"] for atom in result.data["atoms"]] == [0.0, 0.0]
    assert result.data["diagnostics"]["integrated_electrons"] == pytest.approx(2.0)
    assert result.data["diagnostics"]["resolved_population_sum"] == pytest.approx(2.0)
    assert result.status == "success"


def test_population_membership_comes_from_flow_not_quadrature_owner_atom(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openwfn.analysis.qtaim_basins as basins

    _install_synthetic(monkeypatch, rho=(1.5, 0.5), flow=_flow((0, 1)))
    result = basins.qtaim_basins(_data())

    assert [atom["electron_population"] for atom in result.data["atoms"]] == [1.5, 0.5]


def test_unresolved_electron_contribution_is_retained_without_renormalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openwfn.analysis.qtaim_basins as basins

    _install_synthetic(
        monkeypatch,
        flow=_flow((-1, 1), ("gradient_floor", "captured")),
    )
    result = basins.qtaim_basins(_data())
    diagnostics = result.data["diagnostics"]

    assert [atom["electron_population"] for atom in result.data["atoms"]] == [0.0, 1.0]
    assert diagnostics["unresolved_electrons"] == pytest.approx(1.0)
    assert diagnostics["resolved_population_sum"] == pytest.approx(1.0)
    assert diagnostics["integrated_electrons"] == pytest.approx(2.0)
    assert diagnostics["unresolved_point_count"] == 1
    assert result.status == "partial"


def test_finite_radial_tail_error_is_visible_in_molecular_electron_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openwfn.analysis.qtaim_basins as basins

    _install_synthetic(monkeypatch, rho=(0.99, 0.99))
    result = basins.qtaim_basins(_data())

    diagnostics = result.data["diagnostics"]
    assert diagnostics["integrated_electrons"] == pytest.approx(1.98)
    assert diagnostics["electron_count_residual"] == pytest.approx(0.02)
    assert diagnostics["unresolved_electrons"] == pytest.approx(0.0)
    assert result.status == "partial"


def test_population_reports_electron_charge_and_partition_closure_separately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openwfn.analysis.qtaim_basins as basins

    _install_synthetic(monkeypatch)
    diagnostics = basins.qtaim_basins(_data()).data["diagnostics"]

    assert diagnostics["electron_count_residual"] == pytest.approx(0.0)
    assert diagnostics["population_partition_residual"] == pytest.approx(0.0)
    assert diagnostics["charge_closure_residual"] == pytest.approx(0.0)
    assert diagnostics["expected_molecular_charge"] == pytest.approx(0.0)
    assert diagnostics["integrated_atomic_charge"] == pytest.approx(0.0)


def test_quality_gate_marks_material_unresolved_or_closure_error_partial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openwfn.analysis.qtaim_basins as basins

    _install_synthetic(monkeypatch, rho=(0.99, 0.99))
    strict = replace(QTAIMBasinSettings(), max_electron_count_residual=1.0e-3)
    result = basins.qtaim_basins(_data(), settings=strict)

    assert result.status == "partial"
    assert any("electron" in warning.lower() and "closure" in warning.lower() for warning in result.warnings)


def test_result_has_units_formulas_settings_density_source_and_experimental_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openwfn.analysis.qtaim_basins as basins

    _install_synthetic(monkeypatch)
    result = basins.qtaim_basins(_data())

    assert result.kind == "qtaim_basins"
    assert result.validation_status == "Experimental"
    assert result.data["density_source"] == "scf"
    assert result.data["formulas"]["population"].startswith("N_A")
    assert result.data["formulas"]["charge"].startswith("q_A")
    assert result.data["settings"]["flow_step_bohr"] == pytest.approx(0.05)
    assert result.data["settings"]["quadrature"]["radial_points"] == 48
    assert result.data["boundary_diagnostics"]["status"] == "not_requested"
    assert result.units["electron_population"] == "electron"
    assert result.units["net_charge"] == "elementary charge"


def test_post_hf_metadata_with_scf_density_reports_scf_density_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openwfn.analysis.qtaim_basins as basins

    _install_synthetic(monkeypatch)
    result = basins.qtaim_basins(_data(method="MP2", density_source="scf"))

    assert result.data["density_source"] == "scf"
    assert any("scf density" in warning.lower() for warning in result.warnings)


def test_result_json_contains_null_not_nan_or_infinity(monkeypatch: pytest.MonkeyPatch) -> None:
    import openwfn.analysis.qtaim_basins as basins

    _install_synthetic(monkeypatch)
    payload = basins.qtaim_basins(_data()).as_dict()

    json.dumps(payload, allow_nan=False)


def test_quadrature_point_limit_fails_before_density_or_flow_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openwfn.analysis.qtaim_basins as basins

    _install_synthetic(monkeypatch)
    called = False

    def fail_density(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("density must not run")

    monkeypatch.setattr(basins, "evaluate_density", fail_density, raising=False)
    monkeypatch.setattr(basins.limits, "MAX_ATOM_QUADRATURE_POINTS", 1)

    settings = replace(
        QTAIMBasinSettings(),
        quadrature=AtomQuadratureSettings(
            radial_points=2,
            theta_points=2,
            phi_points=4,
            radial_extent_bohr=1.0,
            chunk_size=16,
        ),
    )
    with pytest.raises(ValueError, match="quadrature point count|safety limit"):
        basins.qtaim_basins(_data(), settings=settings)

    assert called is False
