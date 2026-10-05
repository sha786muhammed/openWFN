from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

import openwfn.analysis.limits as limits
from openwfn.analysis.qtaim_basins import QTAIMBasinSettings


def _two_gaussian_field(points_bohr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    points = np.asarray(points_bohr, dtype=float)
    centers = np.asarray(((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0)))
    delta = points[:, None, :] - centers[None, :, :]
    values = np.exp(-np.sum(delta * delta, axis=2))
    rho = np.sum(values, axis=1)
    gradient = np.sum(-2.0 * delta * values[:, :, None], axis=1)
    return rho, gradient


def _settings() -> QTAIMBasinSettings:
    return replace(
        QTAIMBasinSettings(),
        flow_step_bohr=0.05,
        attractor_capture_radius_bohr=0.20,
        gradient_floor=1.0e-12,
        boundary_spacing_bohr=0.50,
        boundary_padding_bohr=0.10,
        boundary_bisection_tolerance_bohr=1.0e-4,
        boundary_local_radius_bohr=0.80,
        boundary_min_neighbors=4,
    )


def test_symmetry_plane_crossing_bisection_converges_to_known_boundary() -> None:
    from openwfn.analysis.qtaim_boundary import qtaim_zero_flux_diagnostics

    result = qtaim_zero_flux_diagnostics(
        _two_gaussian_field,
        np.asarray(((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0))),
        bounds=(np.asarray((-1.5, -1.0, -1.0)), np.asarray((1.5, 1.0, 1.0))),
        settings=_settings(),
    )

    assert result.crossing_sample_count > 0
    assert np.max(np.abs(result.crossing_points_bohr[:, 0])) <= 2.0e-3


def test_exact_synthetic_boundary_has_zero_normal_gradient_component() -> None:
    from openwfn.analysis.qtaim_boundary import qtaim_zero_flux_diagnostics

    result = qtaim_zero_flux_diagnostics(
        _two_gaussian_field,
        np.asarray(((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0))),
        bounds=(np.asarray((-1.5, -1.0, -1.0)), np.asarray((1.5, 1.0, 1.0))),
        settings=_settings(),
    )

    assert result.resolved_sample_count > 0
    assert result.median_residual is not None
    assert result.p95_residual is not None
    assert result.median_residual < 1.0e-6
    assert result.p95_residual < 1.0e-4


def test_plane_fit_uses_neighboring_crossings_and_returns_finite_normal() -> None:
    from openwfn.analysis.qtaim_boundary import _fit_boundary_normal

    points = np.asarray(
        ((0.0, -0.5, -0.5), (0.0, -0.5, 0.5), (0.0, 0.5, -0.5), (0.0, 0.5, 0.5))
    )
    normal = _fit_boundary_normal(points, condition_ratio=1.0e-3)

    assert normal is not None
    assert np.isfinite(normal).all()
    assert abs(abs(normal[0]) - 1.0) < 1.0e-12


def test_collinear_or_sparse_boundary_neighbors_are_unresolved_not_arbitrary() -> None:
    from openwfn.analysis.qtaim_boundary import _fit_boundary_normal

    sparse = np.asarray(((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 2.0, 0.0)))
    assert _fit_boundary_normal(sparse, condition_ratio=1.0e-3) is None


def test_boundary_grid_oversize_rejected_before_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    from openwfn.analysis.qtaim_boundary import qtaim_zero_flux_diagnostics

    monkeypatch.setattr(limits, "MAX_GRID_POINTS", 10)
    called = False

    def evaluator(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        nonlocal called
        called = True
        return _two_gaussian_field(points)

    with pytest.raises(ValueError, match=r"boundary.*grid|grid.*10"):
        qtaim_zero_flux_diagnostics(
            evaluator,
            np.asarray(((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0))),
            bounds=(np.asarray((-1.5, -1.0, -1.0)), np.asarray((1.5, 1.0, 1.0))),
            settings=_settings(),
        )
    assert called is False


def test_requested_zero_flux_p95_above_015_is_partial(monkeypatch: pytest.MonkeyPatch) -> None:
    import openwfn.analysis.qtaim_boundary as boundary

    monkeypatch.setattr(boundary, "_boundary_residual", lambda *args, **kwargs: 0.25)
    result = boundary.qtaim_zero_flux_diagnostics(
        _two_gaussian_field,
        np.asarray(((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0))),
        bounds=(np.asarray((-1.5, -1.0, -1.0)), np.asarray((1.5, 1.0, 1.0))),
        settings=_settings(),
    )

    assert result.p95_residual == pytest.approx(0.25)
    assert result.status == "partial"
