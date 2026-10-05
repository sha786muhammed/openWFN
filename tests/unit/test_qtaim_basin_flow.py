from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

import openwfn.analysis.limits as limits


def _basin_api():
    from openwfn.analysis.qtaim_basins import QTAIMBasinSettings, classify_basin_points

    return QTAIMBasinSettings, classify_basin_points


def _two_gaussian_field(points_bohr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    points = np.asarray(points_bohr, dtype=float)
    centers = np.asarray(((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0)), dtype=float)
    delta = points[:, None, :] - centers[None, :, :]
    values = np.exp(-np.sum(delta * delta, axis=2))
    rho = np.sum(values, axis=1)
    gradient = np.sum(-2.0 * delta * values[:, :, None], axis=1)
    return rho, gradient


def _single_parabola(points_bohr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    points = np.asarray(points_bohr, dtype=float)
    x = points[:, 0]
    rho = 2.0 - x * x - points[:, 1] ** 2 - points[:, 2] ** 2
    gradient = -2.0 * points
    return rho, gradient


def test_two_attractor_flow_assigns_points_on_each_side_of_symmetry_plane() -> None:
    Settings, classify = _basin_api()
    result = classify(
        _two_gaussian_field,
        np.asarray(((-0.25, 0.0, 0.0), (0.25, 0.0, 0.0))),
        np.asarray(((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0))),
        bounds=(np.full(3, -3.0), np.full(3, 3.0)),
        settings=replace(Settings(), attractor_capture_radius_bohr=0.20),
    )

    assert result.basin_indices.tolist() == [0, 1]
    assert result.attractor_indices.tolist() == [0, 1]
    assert result.status.tolist() == ["captured", "captured"]


def test_exact_symmetry_plane_is_not_assigned_by_nearest_attractor_fallback() -> None:
    Settings, classify = _basin_api()
    result = classify(
        _two_gaussian_field,
        np.asarray(((0.0, 0.0, 0.0),)),
        np.asarray(((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0))),
        bounds=(np.full(3, -3.0), np.full(3, 3.0)),
        settings=Settings(),
    )

    assert result.basin_indices.tolist() == [-1]
    assert result.status.tolist() == ["gradient_floor"]


def test_epsilon_offsets_from_boundary_are_deterministic() -> None:
    Settings, classify = _basin_api()
    points = np.asarray(((-1.0e-4, 0.0, 0.0), (1.0e-4, 0.0, 0.0)))
    kwargs = dict(
        bounds=(np.full(3, -3.0), np.full(3, 3.0)),
        settings=replace(Settings(), gradient_floor=1.0e-14),
    )

    first = classify(_two_gaussian_field, points, np.asarray(((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0))), **kwargs)
    second = classify(_two_gaussian_field, points, np.asarray(((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0))), **kwargs)

    assert first.basin_indices.tolist() == [0, 1]
    np.testing.assert_array_equal(first.basin_indices, second.basin_indices)
    np.testing.assert_array_equal(first.status, second.status)


def test_flow_requires_monotonic_density_ascent_and_backtracks() -> None:
    Settings, classify = _basin_api()
    result = classify(
        _single_parabola,
        np.asarray(((0.10, 0.0, 0.0),)),
        np.asarray(((0.0, 0.0, 0.0),)),
        bounds=(np.full(3, -2.0), np.full(3, 2.0)),
        settings=replace(
            Settings(),
            flow_step_bohr=0.50,
            attractor_capture_radius_bohr=0.03,
            max_backtracks=8,
        ),
    )

    assert result.status.tolist() == ["captured"]
    assert result.basin_indices.tolist() == [0]
    assert result.steps[0] >= 1
    assert result.path_lengths_bohr[0] < 0.50


def test_flow_reports_gradient_floor_out_of_bounds_nonfinite_step_limit_and_ambiguous_capture() -> None:
    Settings, classify = _basin_api()
    attractor = np.asarray(((0.0, 0.0, 0.0),))

    gradient_floor = classify(
        lambda points: (np.ones(len(points)), np.zeros((len(points), 3))),
        np.asarray(((0.5, 0.0, 0.0),)),
        attractor,
        bounds=(np.full(3, -2.0), np.full(3, 2.0)),
        settings=Settings(),
    )
    assert gradient_floor.status.tolist() == ["gradient_floor"]

    out_of_bounds = classify(
        lambda points: (points[:, 0], np.tile((1.0, 0.0, 0.0), (len(points), 1))),
        np.asarray(((0.95, 0.0, 0.0),)),
        np.asarray(((10.0, 0.0, 0.0),)),
        bounds=(np.asarray((-1.0, -1.0, -1.0)), np.asarray((1.0, 1.0, 1.0))),
        settings=replace(Settings(), flow_step_bohr=0.20, max_backtracks=1),
    )
    assert out_of_bounds.status.tolist() == ["out_of_bounds"]

    nonfinite = classify(
        lambda points: (np.full(len(points), np.nan), np.zeros((len(points), 3))),
        np.asarray(((0.5, 0.0, 0.0),)),
        attractor,
        bounds=(np.full(3, -2.0), np.full(3, 2.0)),
        settings=Settings(),
    )
    assert nonfinite.status.tolist() == ["nonfinite_field"]

    step_limit = classify(
        lambda points: (points[:, 0], np.tile((1.0, 0.0, 0.0), (len(points), 1))),
        np.asarray(((0.0, 0.0, 0.0),)),
        np.asarray(((10.0, 0.0, 0.0),)),
        bounds=(np.full(3, -20.0), np.full(3, 20.0)),
        settings=replace(Settings(), max_flow_steps=1, flow_step_bohr=0.05),
    )
    assert step_limit.status.tolist() == ["step_limit"]

    ambiguous = classify(
        _single_parabola,
        np.asarray(((0.0, 0.0, 0.0),)),
        np.asarray(((-0.10, 0.0, 0.0), (0.10, 0.0, 0.0))),
        bounds=(np.full(3, -2.0), np.full(3, 2.0)),
        settings=replace(Settings(), attractor_capture_radius_bohr=0.20),
    )
    assert ambiguous.status.tolist() == ["ambiguous_capture"]
    assert ambiguous.basin_indices.tolist() == [-1]


def test_chunked_and_unchunked_flow_agree_within_float_tolerance() -> None:
    Settings, classify = _basin_api()
    points = np.asarray(((-0.60, 0.1, 0.0), (-0.25, 0.0, 0.1), (0.25, 0.0, -0.1), (0.60, -0.1, 0.0)))
    attractors = np.asarray(((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0)))
    kwargs = dict(bounds=(np.full(3, -3.0), np.full(3, 3.0)), settings=Settings())

    full = classify(_two_gaussian_field, points, attractors, chunk_size=None, **kwargs)
    chunked = classify(_two_gaussian_field, points, attractors, chunk_size=1, **kwargs)

    np.testing.assert_array_equal(full.basin_indices, chunked.basin_indices)
    np.testing.assert_array_equal(full.status, chunked.status)
    np.testing.assert_allclose(full.final_points_bohr, chunked.final_points_bohr, rtol=0.0, atol=1.0e-14)
    np.testing.assert_allclose(full.path_lengths_bohr, chunked.path_lengths_bohr, rtol=0.0, atol=1.0e-14)


def test_flow_rejects_oversized_point_request_before_evaluation(monkeypatch: pytest.MonkeyPatch) -> None:
    Settings, classify = _basin_api()
    monkeypatch.setattr(limits, "MAX_POINT_ANALYSIS_POINTS", 2)
    called = False

    def evaluator(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        nonlocal called
        called = True
        return np.ones(len(points)), np.zeros((len(points), 3))

    with pytest.raises(ValueError, match=r"3.*2"):
        classify(
            evaluator,
            np.zeros((3, 3)),
            np.asarray(((0.0, 0.0, 0.0),)),
            bounds=(np.full(3, -1.0), np.full(3, 1.0)),
            settings=Settings(),
        )

    assert called is False


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"flow_step_bohr": 0.0}, "flow_step_bohr"),
        ({"attractor_capture_radius_bohr": float("inf")}, "attractor_capture_radius_bohr"),
        ({"gradient_floor": -1.0}, "gradient_floor"),
        ({"max_flow_steps": 0}, "max_flow_steps"),
        ({"max_backtracks": True}, "max_backtracks"),
        ({"bounds_padding_bohr": float("nan")}, "bounds_padding_bohr"),
        ({"attractor_match_tolerance_bohr": 0.0}, "attractor_match_tolerance_bohr"),
        ({"density_ascent_rel_tolerance": -1.0}, "density_ascent_rel_tolerance"),
    ),
)
def test_basin_settings_reject_nonfinite_nonpositive_and_invalid_integer_controls(
    changes: dict[str, object], message: str
) -> None:
    Settings, _ = _basin_api()
    with pytest.raises(ValueError, match=message):
        Settings(**changes)
