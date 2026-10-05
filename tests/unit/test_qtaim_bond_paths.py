import numpy as np

from openwfn.analysis.qtaim import QTAIMSettings, trace_bond_path_for_field
from openwfn.analysis.realspace import DensityFieldBatch


def _two_attractor_field(points_bohr: np.ndarray) -> DensityFieldBatch:
    points = np.asarray(points_bohr, dtype=float)
    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2]
    rho = 5.0 - (x * x - 1.0) ** 2 - y * y - z * z
    gradient = np.column_stack(
        (
            -4.0 * x * (x * x - 1.0),
            -2.0 * y,
            -2.0 * z,
        )
    )
    hessian = np.zeros((len(points), 3, 3), dtype=float)
    hessian[:, 0, 0] = 4.0 - 12.0 * x * x
    hessian[:, 1, 1] = -2.0
    hessian[:, 2, 2] = -2.0
    return DensityFieldBatch(
        rho=rho,
        gradient=gradient,
        hessian=hessian,
        laplacian=np.trace(hessian, axis1=1, axis2=2),
    )


def test_bond_path_traces_positive_curvature_direction_to_distinct_attractors() -> None:
    atoms = np.array(((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0)), dtype=float)
    bounds = (np.full(3, -2.0), np.full(3, 2.0))
    settings = QTAIMSettings(
        path_step_bohr=0.04,
        path_initial_displacement_bohr=0.02,
        path_capture_radius_bohr=0.08,
        max_path_steps=200,
        max_stored_path_points=128,
    )

    path = trace_bond_path_for_field(
        _two_attractor_field,
        bcp_position_bohr=np.zeros(3),
        atom_positions_bohr=atoms,
        bounds=bounds,
        settings=settings,
    )

    assert path.resolved is True
    assert set(path.endpoint_atom_indices) == {0, 1}
    assert path.termination_reasons == ("captured_atom", "captured_atom")
    assert 0.0 < path.length_bohr < 3.0
    assert len(path.points_bohr) <= settings.max_stored_path_points
    assert np.all(np.isfinite(np.asarray(path.points_bohr)))
    np.testing.assert_allclose(path.points_bohr[len(path.points_bohr) // 2], np.zeros(3), atol=0.1)


def test_bond_path_keeps_unresolved_same_endpoint_or_step_limit_explicit() -> None:
    bounds = (np.full(3, -2.0), np.full(3, 2.0))
    settings = QTAIMSettings(
        path_step_bohr=0.04,
        path_initial_displacement_bohr=0.02,
        path_capture_radius_bohr=0.25,
        max_path_steps=2,
        max_stored_path_points=16,
    )

    path = trace_bond_path_for_field(
        _two_attractor_field,
        bcp_position_bohr=np.zeros(3),
        atom_positions_bohr=np.array(((1.0, 0.0, 0.0),), dtype=float),
        bounds=bounds,
        settings=settings,
    )

    assert path.resolved is False
    assert path.unresolved_reason is not None
    assert len(path.points_bohr) <= settings.max_stored_path_points
