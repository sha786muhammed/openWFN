from __future__ import annotations

import importlib
import importlib.util

import numpy as np
import pytest


def _api():
    spec = importlib.util.find_spec("openwfn.analysis.nto")
    assert spec is not None, "openwfn.analysis.nto must provide the NTO SVD engine"
    module = importlib.import_module("openwfn.analysis.nto")
    return module.compute_nto_svd, module.MAX_NTO_MATRIX_ELEMENTS


def test_nto_svd_diagonal_matrix_has_exact_pairs_and_weights() -> None:
    compute_nto_svd, _ = _api()
    matrix = np.diag([3.0, 2.0, 1.0])

    result = compute_nto_svd(matrix)

    np.testing.assert_allclose(result.singular_values, [3.0, 2.0, 1.0], atol=1e-14)
    np.testing.assert_allclose(result.pair_strengths, [9.0, 4.0, 1.0], atol=1e-14)
    np.testing.assert_allclose(result.weights, np.array([9.0, 4.0, 1.0]) / 14.0, atol=1e-14)
    np.testing.assert_allclose(result.cumulative_weights, [9 / 14, 13 / 14, 1.0], atol=1e-14)
    assert result.transition_norm == pytest.approx(14.0)


def test_nto_svd_reconstructs_rotated_matrix_and_vectors_are_orthonormal() -> None:
    compute_nto_svd, _ = _api()
    theta = 0.37
    phi = -0.51
    left = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    right = np.array([[np.cos(phi), -np.sin(phi)], [np.sin(phi), np.cos(phi)]])
    matrix = left @ np.diag([2.5, 0.75]) @ right.T

    result = compute_nto_svd(matrix)
    reconstructed = result.hole_vectors @ np.diag(result.singular_values) @ result.electron_vectors.T

    np.testing.assert_allclose(reconstructed, matrix, atol=1e-13)
    np.testing.assert_allclose(result.hole_vectors.T @ result.hole_vectors, np.eye(2), atol=1e-13)
    np.testing.assert_allclose(result.electron_vectors.T @ result.electron_vectors, np.eye(2), atol=1e-13)


def test_nto_svd_phase_is_deterministic_and_preserves_each_pair_outer_product() -> None:
    compute_nto_svd, _ = _api()
    matrix = np.array([[-1.2, 0.25], [-0.4, 0.8], [0.15, -0.3]])

    first = compute_nto_svd(matrix)
    second = compute_nto_svd(matrix.copy())

    np.testing.assert_array_equal(first.hole_vectors, second.hole_vectors)
    np.testing.assert_array_equal(first.electron_vectors, second.electron_vectors)
    for pair in range(first.singular_values.size):
        hole = first.hole_vectors[:, pair]
        electron = first.electron_vectors[:, pair]
        pivot = int(np.flatnonzero(np.abs(hole) == np.max(np.abs(hole)))[0])
        assert hole[pivot] >= 0.0
        np.testing.assert_allclose(
            first.singular_values[pair] * np.outer(hole, electron),
            second.singular_values[pair] * np.outer(
                second.hole_vectors[:, pair], second.electron_vectors[:, pair]
            ),
            atol=0.0,
            rtol=0.0,
        )


def test_nto_svd_weights_are_normalized_monotonic_and_end_at_one() -> None:
    compute_nto_svd, _ = _api()
    result = compute_nto_svd(np.array([[2.0, 0.0, 0.0], [0.0, 1.0, 0.5]]))

    assert np.all(result.weights >= 0.0)
    assert np.sum(result.weights) == pytest.approx(1.0)
    assert np.all(np.diff(result.cumulative_weights) >= 0.0)
    assert result.cumulative_weights[-1] == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("matrix", "message"),
    [
        (np.zeros((2, 2)), "zero-norm"),
        (np.array([[1.0, np.nan]]), "finite"),
        (np.array([1.0, 2.0]), "two-dimensional"),
        (np.empty((0, 2)), "non-empty"),
    ],
)
def test_nto_svd_rejects_invalid_transition_matrices(matrix: np.ndarray, message: str) -> None:
    compute_nto_svd, _ = _api()
    with pytest.raises(ValueError, match=message):
        compute_nto_svd(matrix)


def test_nto_svd_rejects_matrix_over_resource_ceiling_before_svd(monkeypatch) -> None:
    compute_nto_svd, max_elements = _api()
    matrix = np.zeros((1001, 1000), dtype=float)
    assert matrix.size > max_elements

    def forbidden_svd(*args, **kwargs):
        raise AssertionError("SVD must not run for an oversized transition matrix")

    monkeypatch.setattr(np.linalg, "svd", forbidden_svd)
    requested = f"{matrix.size:,}"
    ceiling = f"{max_elements:,}"
    with pytest.raises(ValueError, match=rf"{requested}.*{ceiling}"):
        compute_nto_svd(matrix)
