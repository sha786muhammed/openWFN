import importlib

import numpy as np
import pytest


def _localization_module():
    return importlib.import_module("openwfn.analysis.localization")


def test_homogeneous_electron_gas_is_half_for_elf_and_lol() -> None:
    localization = _localization_module()
    settings = localization.LocalizationSettings()
    rho = np.array([0.25])
    gradient = np.zeros((1, 3))
    d0 = (3.0 / 10.0) * (3.0 * np.pi**2) ** (2.0 / 3.0) * rho ** (5.0 / 3.0)
    tau = d0.copy()

    elf = localization.compute_elf_components(
        rho, gradient, tau, spin_resolved=False, settings=settings
    )
    lol = localization.compute_lol_components(
        rho, tau, spin_resolved=False, settings=settings
    )

    assert elf.values[0] == pytest.approx(0.5, abs=1e-14)
    assert lol.values[0] == pytest.approx(0.5, abs=1e-14)
    assert elf.valid_mask.tolist() == [True]
    assert lol.valid_mask.tolist() == [True]


def test_spin_resolved_homogeneous_gas_uses_spin_heg_constant() -> None:
    localization = _localization_module()
    settings = localization.LocalizationSettings()
    rho = np.array([0.125])
    gradient = np.zeros((1, 3))
    d0 = (3.0 / 10.0) * (6.0 * np.pi**2) ** (2.0 / 3.0) * rho ** (5.0 / 3.0)

    elf = localization.compute_elf_components(
        rho, gradient, d0, spin_resolved=True, settings=settings
    )
    lol = localization.compute_lol_components(
        rho, d0, spin_resolved=True, settings=settings
    )

    assert elf.values[0] == pytest.approx(0.5, abs=1e-14)
    assert lol.values[0] == pytest.approx(0.5, abs=1e-14)


def test_elf_single_orbital_limit_is_one() -> None:
    localization = _localization_module()
    settings = localization.LocalizationSettings()
    rho = np.array([0.4])
    gradient = np.array([[0.3, -0.2, 0.1]])
    tau_w = np.sum(gradient * gradient, axis=1) / (8.0 * rho)

    result = localization.compute_elf_components(
        rho, gradient, tau_w, spin_resolved=False, settings=settings
    )

    assert result.values[0] == pytest.approx(1.0, abs=1e-14)
    assert result.pauli_excess[0] == pytest.approx(0.0, abs=1e-14)
    assert result.valid_mask.tolist() == [True]


def test_density_tail_is_invalid_not_artificially_localized() -> None:
    localization = _localization_module()
    settings = localization.LocalizationSettings(density_floor=1.0e-12)
    rho = np.array([1.0e-14])
    gradient = np.zeros((1, 3))
    tau = np.zeros(1)

    elf = localization.compute_elf_components(
        rho, gradient, tau, spin_resolved=False, settings=settings
    )
    lol = localization.compute_lol_components(
        rho, tau, spin_resolved=False, settings=settings
    )

    assert elf.valid_mask.tolist() == [False]
    assert lol.valid_mask.tolist() == [False]
    assert np.isnan(elf.values[0])
    assert np.isnan(lol.values[0])
    assert elf.invalid_density_count == 1
    assert lol.invalid_density_count == 1


def test_materially_negative_pauli_excess_is_invalid_and_not_squared() -> None:
    localization = _localization_module()
    settings = localization.LocalizationSettings()
    rho = np.array([0.5])
    gradient = np.array([[1.0, 0.0, 0.0]])
    tau_w = np.sum(gradient * gradient, axis=1) / (8.0 * rho)
    tau = tau_w - 1.0e-4

    result = localization.compute_elf_components(
        rho, gradient, tau, spin_resolved=False, settings=settings
    )

    assert result.valid_mask.tolist() == [False]
    assert np.isnan(result.values[0])
    assert result.pauli_excess[0] < 0.0
    assert result.invalid_pauli_count == 1


def test_tiny_negative_pauli_excess_is_clamped_with_diagnostic_count() -> None:
    localization = _localization_module()
    settings = localization.LocalizationSettings()
    rho = np.array([0.5])
    gradient = np.array([[0.2, 0.0, 0.0]])
    tau_w = np.sum(gradient * gradient, axis=1) / (8.0 * rho)
    tau = tau_w - 5.0e-13

    result = localization.compute_elf_components(
        rho, gradient, tau, spin_resolved=False, settings=settings
    )

    assert result.valid_mask.tolist() == [True]
    assert result.values[0] == pytest.approx(1.0, abs=1e-12)
    assert result.clamped_pauli_count == 1
    assert result.pauli_excess[0] == pytest.approx(0.0, abs=0.0)


def test_materially_negative_ked_is_invalid_for_lol() -> None:
    localization = _localization_module()
    settings = localization.LocalizationSettings()

    result = localization.compute_lol_components(
        np.array([0.5]), np.array([-1.0e-4]), spin_resolved=False, settings=settings
    )

    assert result.valid_mask.tolist() == [False]
    assert np.isnan(result.values[0])
    assert result.invalid_ked_count == 1


def test_tiny_negative_ked_is_clamped_for_lol() -> None:
    localization = _localization_module()
    settings = localization.LocalizationSettings()

    result = localization.compute_lol_components(
        np.array([0.5]), np.array([-5.0e-13]), spin_resolved=False, settings=settings
    )

    assert result.valid_mask.tolist() == [True]
    assert result.values[0] == pytest.approx(1.0, abs=1e-14)
    assert result.clamped_ked_count == 1
    assert result.tau[0] == pytest.approx(0.0, abs=0.0)


def test_nonfinite_inputs_are_invalid() -> None:
    localization = _localization_module()
    settings = localization.LocalizationSettings()
    rho = np.array([0.5, np.nan])
    gradient = np.array([[0.0, 0.0, 0.0], [0.0, np.inf, 0.0]])
    tau = np.array([0.2, 0.1])

    elf = localization.compute_elf_components(
        rho, gradient, tau, spin_resolved=False, settings=settings
    )
    lol = localization.compute_lol_components(
        rho, tau, spin_resolved=False, settings=settings
    )

    assert elf.valid_mask.tolist() == [True, False]
    assert lol.valid_mask.tolist() == [True, False]
    assert np.isnan(elf.values[1])
    assert np.isnan(lol.values[1])


def test_kernel_shape_validation_is_explicit() -> None:
    localization = _localization_module()
    settings = localization.LocalizationSettings()

    with pytest.raises(ValueError, match="gradient"):
        localization.compute_elf_components(
            np.ones(2), np.ones((2, 2)), np.ones(2), spin_resolved=False, settings=settings
        )
    with pytest.raises(ValueError, match="same length"):
        localization.compute_lol_components(
            np.ones(2), np.ones(3), spin_resolved=False, settings=settings
        )


def test_settings_reject_nonpositive_density_floor() -> None:
    localization = _localization_module()

    with pytest.raises(ValueError, match="density_floor"):
        localization.LocalizationSettings(density_floor=0.0)
