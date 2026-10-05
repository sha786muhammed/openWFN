import numpy as np
import pytest

from openwfn.analysis.qtaim import QTAIMSettings, search_critical_points
from openwfn.analysis.realspace import DensityFieldBatch


def _quadratic_field(center: np.ndarray, hessian: np.ndarray):
    center = np.asarray(center, dtype=float)
    hessian = np.asarray(hessian, dtype=float)

    def evaluate(points_bohr: np.ndarray) -> DensityFieldBatch:
        points = np.asarray(points_bohr, dtype=float)
        delta = points - center[None, :]
        gradient = np.einsum("ij,pj->pi", hessian, delta)
        rho = 2.0 + 0.5 * np.einsum("pi,ij,pj->p", delta, hessian, delta)
        hessians = np.repeat(hessian[None, :, :], len(points), axis=0)
        return DensityFieldBatch(
            rho=rho,
            gradient=gradient,
            hessian=hessians,
            laplacian=np.full(len(points), np.trace(hessian), dtype=float),
        )

    return evaluate


def test_bounded_newton_search_converges_and_merges_duplicate_seeds() -> None:
    target = np.array((0.25, -0.30, 0.15), dtype=float)
    evaluator = _quadratic_field(target, np.diag((-3.0, -2.0, 1.0)))
    seeds = np.array(((1.0, 0.4, -0.5), (-0.8, -0.6, 0.7)), dtype=float)
    bounds = (np.array((-2.0, -2.0, -2.0)), np.array((2.0, 2.0, 2.0)))
    settings = QTAIMSettings(
        gradient_tolerance=1.0e-10,
        merge_tolerance_bohr=1.0e-6,
        trust_radius_bohr=0.4,
        max_iterations=32,
    )

    points, diagnostics = search_critical_points(evaluator, seeds, bounds=bounds, settings=settings)

    assert diagnostics.seed_count == 2
    assert diagnostics.converged_seed_count == 2
    assert len(points) == 1
    np.testing.assert_allclose(points[0].position_bohr, target, atol=1.0e-9)
    assert points[0].label == "(3,-1)"
    assert points[0].gradient_norm <= settings.gradient_tolerance


def test_search_obeys_trust_radius_and_iteration_limit() -> None:
    evaluator = _quadratic_field(np.zeros(3), np.eye(3))
    seeds = np.array(((1.0, 0.0, 0.0),), dtype=float)
    bounds = (np.array((-2.0, -2.0, -2.0)), np.array((2.0, 2.0, 2.0)))

    points, diagnostics = search_critical_points(
        evaluator,
        seeds,
        bounds=bounds,
        settings=QTAIMSettings(
            trust_radius_bohr=0.1,
            max_iterations=2,
            gradient_tolerance=1.0e-12,
        ),
    )

    assert points == ()
    assert diagnostics.converged_seed_count == 0
    assert diagnostics.failed_seed_count == 1


def test_search_terminates_non_improving_or_out_of_bounds_seeds() -> None:
    def constant_gradient(points_bohr: np.ndarray) -> DensityFieldBatch:
        points = np.asarray(points_bohr, dtype=float)
        n = len(points)
        return DensityFieldBatch(
            rho=np.ones(n),
            gradient=np.repeat(np.array(((1.0, 0.0, 0.0),)), n, axis=0),
            hessian=np.repeat(np.eye(3)[None, :, :], n, axis=0),
            laplacian=np.full(n, 3.0),
        )

    bounds = (np.array((-1.0, -1.0, -1.0)), np.array((1.0, 1.0, 1.0)))
    settings = QTAIMSettings(max_backtracks=3, max_iterations=8)

    points, diagnostics = search_critical_points(
        constant_gradient,
        np.array(((0.0, 0.0, 0.0), (2.0, 0.0, 0.0))),
        bounds=bounds,
        settings=settings,
    )

    assert points == ()
    assert diagnostics.seed_count == 2
    assert diagnostics.failed_seed_count == 2


def test_search_rejects_nonfinite_seed_arrays_and_seed_limit_overflow() -> None:
    evaluator = _quadratic_field(np.zeros(3), np.eye(3))
    bounds = (np.full(3, -2.0), np.full(3, 2.0))

    with pytest.raises(ValueError, match="shape"):
        search_critical_points(evaluator, np.zeros((3, 2)), bounds=bounds)
    with pytest.raises(ValueError, match="finite"):
        search_critical_points(
            evaluator,
            np.array(((0.0, np.nan, 0.0),)),
            bounds=bounds,
        )
    with pytest.raises(ValueError, match="max_seeds"):
        search_critical_points(
            evaluator,
            np.zeros((3, 3)),
            bounds=bounds,
            settings=QTAIMSettings(max_seeds=2),
        )
