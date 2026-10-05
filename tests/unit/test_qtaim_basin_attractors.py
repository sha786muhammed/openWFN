from __future__ import annotations

import numpy as np
import pytest

from openwfn.analysis.qtaim import CriticalPoint, SearchDiagnostics
from openwfn.constants import BOHR_TO_ANGSTROM
from openwfn.errors import ValidationError
from openwfn.model import (
    Atom,
    BasisSet,
    BasisShell,
    CalculationData,
    CalculationMetadata,
    DensityMatrix,
    Molecule,
)


def _basin_module():
    import openwfn.analysis.qtaim_basins as basins

    return basins


def _data(
    atoms: tuple[Atom, ...],
    *,
    multiplicity: int = 1,
    ecp_metadata: tuple[tuple[str, str], ...] = (),
) -> CalculationData:
    size = len(atoms)
    shells = tuple(BasisShell(index, 0, (1.0,), (1.0,)) for index in range(size))
    density = tuple(
        tuple(1.0 if row == column else 0.0 for column in range(size))
        for row in range(size)
    )
    return CalculationData(
        molecule=Molecule(
            atoms,
            0,
            multiplicity,
            CalculationMetadata("fixture", method="UHF" if multiplicity > 1 else "RHF"),
        ),
        basis=BasisSet(shells, ecp_metadata=ecp_metadata),
        total_density=DensityMatrix(density, "total"),
        records={
            "Number of electrons": float(size),
            "Number of alpha electrons": float(size),
            "Number of beta electrons": 0.0,
        },
    )


def _atom_at_bohr(x: float, *, atomic_number: int = 1, nuclear_charge: float | None = None) -> Atom:
    return Atom(atomic_number, (x * BOHR_TO_ANGSTROM, 0.0, 0.0), nuclear_charge=nuclear_charge)


def _cp(x: float) -> CriticalPoint:
    return CriticalPoint(
        position_bohr=(x, 0.0, 0.0),
        rho=1.0,
        gradient_norm=0.0,
        laplacian=-3.0,
        hessian_eigenvalues=(-1.0, -1.0, -1.0),
        rank=3,
        signature=-3,
        label="(3,-3)",
        iterations=1,
    )


def _install_points(monkeypatch: pytest.MonkeyPatch, points: tuple[CriticalPoint, ...]) -> None:
    basins = _basin_module()
    diagnostics = SearchDiagnostics(
        seed_count=max(1, len(points)),
        converged_seed_count=len(points),
        failed_seed_count=0,
        merged_critical_point_count=len(points),
    )
    monkeypatch.setattr(
        basins,
        "_discover_basin_critical_points",
        lambda *args, **kwargs: (points, diagnostics),
        raising=False,
    )


def test_preflight_rejects_ghost_center() -> None:
    basins = _basin_module()
    data = _data((_atom_at_bohr(0.0, nuclear_charge=0.0),))

    with pytest.raises(ValidationError, match="ghost"):
        basins.prepare_qtaim_basin_attractors(data)


def test_preflight_rejects_ecp_or_non_all_electron_center() -> None:
    basins = _basin_module()
    ecp_charge = _data((_atom_at_bohr(0.0, atomic_number=14, nuclear_charge=4.0),))
    ecp_basis = _data((_atom_at_bohr(0.0),), ecp_metadata=(("ECP", "fixture"),))

    with pytest.raises(ValidationError, match="ECP|all-electron"):
        basins.prepare_qtaim_basin_attractors(ecp_charge)
    with pytest.raises(ValidationError, match="ECP|all-electron"):
        basins.prepare_qtaim_basin_attractors(ecp_basis)


def test_each_nucleus_requires_one_unique_nuclear_attractor(monkeypatch: pytest.MonkeyPatch) -> None:
    basins = _basin_module()
    data = _data((_atom_at_bohr(-1.0), _atom_at_bohr(1.0)))
    _install_points(monkeypatch, (_cp(-1.0), _cp(1.0)))

    prepared = basins.prepare_qtaim_basin_attractors(data)

    assert prepared.physical_nucleus_indices == (0, 1)
    np.testing.assert_allclose(prepared.attractor_positions_bohr, ((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0)))
    np.testing.assert_allclose(prepared.attractor_to_nucleus_distances_bohr, (0.0, 0.0))


def test_small_gaussian_attractor_displacement_within_035_bohr_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    basins = _basin_module()
    data = _data((_atom_at_bohr(0.0),))
    _install_points(monkeypatch, (_cp(0.20),))

    prepared = basins.prepare_qtaim_basin_attractors(data)

    np.testing.assert_allclose(prepared.attractor_positions_bohr, ((0.20, 0.0, 0.0),))
    np.testing.assert_allclose(prepared.attractor_to_nucleus_distances_bohr, (0.20,))


def test_missing_attractor_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    basins = _basin_module()
    data = _data((_atom_at_bohr(-1.0), _atom_at_bohr(1.0)))
    _install_points(monkeypatch, (_cp(-1.0),))

    with pytest.raises(ValidationError, match="missing|no unique"):
        basins.prepare_qtaim_basin_attractors(data)


def test_ambiguous_nucleus_attractor_matching_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    basins = _basin_module()
    data = _data((_atom_at_bohr(0.0),))
    _install_points(monkeypatch, (_cp(-0.10), _cp(0.10)))

    with pytest.raises(ValidationError, match="ambiguous|multiple"):
        basins.prepare_qtaim_basin_attractors(data)


def test_detected_non_nuclear_attractor_rejects_atomic_only_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    basins = _basin_module()
    data = _data((_atom_at_bohr(0.0),))
    _install_points(monkeypatch, (_cp(0.0), _cp(1.0)))

    with pytest.raises(ValidationError, match="non-nuclear"):
        basins.prepare_qtaim_basin_attractors(data)


def test_open_shell_total_density_is_allowed_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    basins = _basin_module()
    data = _data((_atom_at_bohr(0.0),), multiplicity=2)
    _install_points(monkeypatch, (_cp(0.0),))

    prepared = basins.prepare_qtaim_basin_attractors(data)

    assert prepared.physical_nucleus_indices == (0,)


def test_bounded_attractor_search_is_not_labeled_exhaustive(monkeypatch: pytest.MonkeyPatch) -> None:
    basins = _basin_module()
    data = _data((_atom_at_bohr(0.0),))
    _install_points(monkeypatch, (_cp(0.0),))

    prepared = basins.prepare_qtaim_basin_attractors(data)

    assert prepared.search_complete is False
    assert any("bounded" in warning.lower() and "not" in warning.lower() for warning in prepared.warnings)
