import importlib

import numpy as np
import pytest


def _nci_module():
    return importlib.import_module("openwfn.analysis.nci")


def test_uniform_positive_density_has_zero_rdg() -> None:
    nci = _nci_module()
    result = nci.compute_nci_components(
        np.array([0.25]),
        np.zeros((1, 3)),
        np.diag([-2.0, -1.0, 3.0])[None, :, :],
        settings=nci.NCISettings(),
    )

    assert result.rdg[0] == pytest.approx(0.0, abs=0.0)
    assert result.rdg_valid_mask.tolist() == [True]
    assert result.hessian_valid_mask.tolist() == [True]


def test_rdg_matches_hand_computed_scalar() -> None:
    nci = _nci_module()
    rho = np.array([0.2])
    gradient = np.array([[0.3, 0.4, 0.0]])
    expected = 0.5 / (2.0 * (3.0 * np.pi**2) ** (1.0 / 3.0) * 0.2 ** (4.0 / 3.0))

    result = nci.compute_nci_components(
        rho,
        gradient,
        np.diag([-3.0, -1.0, 2.0])[None, :, :],
        settings=nci.NCISettings(),
    )

    assert result.gradient_norm[0] == pytest.approx(0.5, rel=0.0, abs=1e-15)
    assert result.rdg[0] == pytest.approx(expected, rel=1e-14, abs=0.0)


def test_hessian_eigenvalues_are_sorted_and_lambda2_is_middle_value() -> None:
    nci = _nci_module()
    result = nci.compute_nci_components(
        np.array([0.3]),
        np.zeros((1, 3)),
        np.array([[[4.0, 0.0, 0.0], [0.0, -2.0, 0.0], [0.0, 0.0, 1.0]]]),
        settings=nci.NCISettings(),
    )

    np.testing.assert_allclose(result.hessian_eigenvalues[0], [-2.0, 1.0, 4.0])
    assert result.lambda2[0] == pytest.approx(1.0)
    assert result.hessian_valid_mask.tolist() == [True]


def test_lambda2_sign_and_signed_density_follow_raw_middle_eigenvalue() -> None:
    nci = _nci_module()
    rho = np.array([0.4, 0.6])
    hessian = np.array(
        [
            np.diag([-3.0, -1.0, 2.0]),
            np.diag([-1.0, 2.0, 4.0]),
        ]
    )
    result = nci.compute_nci_components(
        rho,
        np.zeros((2, 3)),
        hessian,
        settings=nci.NCISettings(),
    )

    np.testing.assert_allclose(result.lambda2, [-1.0, 2.0])
    np.testing.assert_allclose(result.signed_density, [-0.4, 0.6])


def test_near_zero_lambda2_is_ambiguous_without_invalidating_field() -> None:
    nci = _nci_module()
    rho = np.array([0.5, 0.5])
    hessian = np.array(
        [
            np.diag([-2.0, 5.0e-13, 1.0]),
            np.diag([-2.0, 0.0, 1.0]),
        ]
    )
    result = nci.compute_nci_components(
        rho,
        np.zeros((2, 3)),
        hessian,
        settings=nci.NCISettings(),
    )

    assert result.lambda2_sign_ambiguous_mask.tolist() == [True, True]
    assert result.hessian_valid_mask.tolist() == [True, True]
    assert result.field_valid_mask.tolist() == [True, True]
    assert result.signed_density[0] == pytest.approx(0.5)
    assert result.signed_density[1] == pytest.approx(0.0)


def test_density_floor_and_nonpositive_density_invalidate_rdg_without_fractional_power_failure() -> None:
    nci = _nci_module()
    rho = np.array([1.0e-14, 0.0, -0.2, 0.5])
    gradient = np.ones((4, 3))
    hessian = np.repeat(np.eye(3)[None, :, :], 4, axis=0)

    result = nci.compute_nci_components(
        rho,
        gradient,
        hessian,
        settings=nci.NCISettings(density_floor=1.0e-12),
    )

    assert result.rdg_valid_mask.tolist() == [False, False, False, True]
    assert result.hessian_valid_mask.tolist() == [True, True, True, True]
    assert np.isnan(result.rdg[:3]).all()
    assert np.isfinite(result.rdg[3])
    assert result.invalid_density_count == 3
    assert np.isrealobj(result.rdg)


def test_nonfinite_inputs_are_invalid_and_arrays_remain_real() -> None:
    nci = _nci_module()
    rho = np.array([0.5, np.nan, 0.5, 0.5])
    gradient = np.array(
        [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [np.inf, 0.0, 0.0],
            [0.0, 0.0, 0.0],
        ]
    )
    hessian = np.repeat(np.eye(3)[None, :, :], 4, axis=0)
    hessian[3, 0, 0] = np.nan

    result = nci.compute_nci_components(
        rho,
        gradient,
        hessian,
        settings=nci.NCISettings(),
    )

    assert result.rdg_valid_mask.tolist() == [True, False, False, True]
    assert result.hessian_valid_mask.tolist() == [True, True, True, False]
    assert result.field_valid_mask.tolist() == [True, False, False, False]
    assert np.isrealobj(result.hessian_eigenvalues)
    assert result.invalid_nonfinite_count == 3


def test_small_hessian_antisymmetry_is_symmetrized_but_material_antisymmetry_is_invalid() -> None:
    nci = _nci_module()
    hessian = np.array(
        [
            [[-2.0, 5.0e-12, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 3.0]],
            [[-2.0, 2.0e-8, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 3.0]],
        ]
    )
    result = nci.compute_nci_components(
        np.array([0.5, 0.5]),
        np.zeros((2, 3)),
        hessian,
        settings=nci.NCISettings(hessian_antisymmetry_tolerance=1.0e-10),
    )

    assert result.rdg_valid_mask.tolist() == [True, True]
    assert result.hessian_valid_mask.tolist() == [True, False]
    assert result.field_valid_mask.tolist() == [True, False]
    assert result.hessian_antisymmetry_residual[0] == pytest.approx(5.0e-12)
    assert result.hessian_antisymmetry_residual[1] == pytest.approx(2.0e-8)
    assert result.invalid_hessian_count == 1
    assert np.isfinite(result.lambda2[0])
    assert np.isnan(result.lambda2[1])


def test_empty_arrays_return_empty_valid_shapes() -> None:
    nci = _nci_module()
    result = nci.compute_nci_components(
        np.empty((0,)),
        np.empty((0, 3)),
        np.empty((0, 3, 3)),
        settings=nci.NCISettings(),
    )

    assert result.rho.shape == (0,)
    assert result.gradient_norm.shape == (0,)
    assert result.rdg.shape == (0,)
    assert result.hessian_eigenvalues.shape == (0, 3)
    assert result.lambda2.shape == (0,)
    assert result.signed_density.shape == (0,)
    assert result.rdg_valid_mask.shape == (0,)
    assert result.hessian_valid_mask.shape == (0,)
    assert result.field_valid_mask.shape == (0,)


def test_settings_reject_nonfinite_or_invalid_thresholds() -> None:
    nci = _nci_module()

    with pytest.raises(ValueError, match="density_floor"):
        nci.NCISettings(density_floor=0.0)
    with pytest.raises(ValueError, match="density_floor"):
        nci.NCISettings(density_floor=np.nan)
    with pytest.raises(ValueError, match="hessian_antisymmetry_tolerance"):
        nci.NCISettings(hessian_antisymmetry_tolerance=-1.0)
    with pytest.raises(ValueError, match="lambda2_ambiguity_absolute_tolerance"):
        nci.NCISettings(lambda2_ambiguity_absolute_tolerance=-1.0)
    with pytest.raises(ValueError, match="lambda2_ambiguity_relative_tolerance"):
        nci.NCISettings(lambda2_ambiguity_relative_tolerance=np.inf)
