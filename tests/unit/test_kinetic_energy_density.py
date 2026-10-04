import math

import numpy as np
import pytest

from openwfn.analysis.basis import evaluate_ao_fields
from openwfn.analysis.realspace import evaluate_kinetic_energy_density
from openwfn.errors import DataUnavailableError
from openwfn.model import (
    Atom,
    BasisSet,
    BasisShell,
    CalculationData,
    CalculationMetadata,
    DensityMatrix,
    Molecule,
)


def _molecule() -> Molecule:
    return Molecule(
        (Atom(1, (0.0, 0.0, 0.0)),),
        0,
        1,
        CalculationMetadata("fixture"),
    )


def _matrix(values: np.ndarray, kind: str) -> DensityMatrix:
    return DensityMatrix(
        tuple(tuple(float(value) for value in row) for row in values),
        kind,
    )


def test_single_gaussian_positive_definite_ked_has_closed_form_value() -> None:
    alpha = 1.0
    basis = BasisSet((BasisShell(0, 0, (alpha,), (1.0,)),))
    point = np.array(((0.2, -0.3, 0.4),), dtype=float)
    data = CalculationData(
        molecule=_molecule(),
        basis=basis,
        total_density=DensityMatrix(((1.0,),), "total"),
    )

    result = evaluate_kinetic_energy_density(data, point)

    xyz = point[0]
    normalization_squared = (2.0 * alpha / math.pi) ** 1.5
    phi_squared = normalization_squared * math.exp(
        -2.0 * alpha * float(np.dot(xyz, xyz))
    )
    expected = 2.0 * alpha**2 * float(np.dot(xyz, xyz)) * phi_squared
    assert result.tau.shape == (1,)
    assert result.tau[0] == pytest.approx(expected, abs=1e-12)
    assert result.convention == "positive_definite_half_gradient_square"


def test_restricted_density_matrix_ked_matches_explicit_doubly_occupied_mo_gradient() -> None:
    basis = BasisSet(
        (
            BasisShell(0, 0, (0.7,), (1.0,)),
            BasisShell(0, 0, (1.3,), (1.0,)),
        )
    )
    coefficients = np.array((0.8, -0.35), dtype=float)
    total_density = 2.0 * np.outer(coefficients, coefficients)
    data = CalculationData(
        molecule=_molecule(),
        basis=basis,
        total_density=_matrix(total_density, "total"),
        records={"Number of alpha electrons": 1, "Number of beta electrons": 1},
    )
    points = np.array(
        ((0.15, -0.22, 0.31), (0.41, 0.13, -0.19), (-0.28, 0.36, 0.17)),
        dtype=float,
    )

    result = evaluate_kinetic_energy_density(data, points, kind="total")
    ao = evaluate_ao_fields(basis, data.molecule, points, derivatives=1)
    orbital_gradient = np.einsum("pia,i->pa", ao.gradients, coefficients)
    expected = np.sum(orbital_gradient * orbital_gradient, axis=1)

    np.testing.assert_allclose(result.tau, expected, atol=1e-12)


def test_unrestricted_ked_channels_match_explicit_alpha_beta_orbital_gradients() -> None:
    basis = BasisSet(
        (
            BasisShell(0, 0, (0.65,), (1.0,)),
            BasisShell(0, 0, (1.15,), (1.0,)),
        )
    )
    alpha_coefficients = np.array((0.72, -0.28), dtype=float)
    beta_coefficients = np.array((0.31, 0.64), dtype=float)
    alpha_density = np.outer(alpha_coefficients, alpha_coefficients)
    beta_density = np.outer(beta_coefficients, beta_coefficients)
    data = CalculationData(
        molecule=_molecule(),
        basis=basis,
        total_density=_matrix(alpha_density + beta_density, "total"),
        spin_density=_matrix(alpha_density - beta_density, "spin"),
    )
    points = np.array(
        ((0.18, -0.24, 0.37), (-0.33, 0.29, 0.11)),
        dtype=float,
    )

    ao = evaluate_ao_fields(basis, data.molecule, points, derivatives=1)
    grad_alpha = np.einsum("pia,i->pa", ao.gradients, alpha_coefficients)
    grad_beta = np.einsum("pia,i->pa", ao.gradients, beta_coefficients)
    expected_alpha = 0.5 * np.sum(grad_alpha * grad_alpha, axis=1)
    expected_beta = 0.5 * np.sum(grad_beta * grad_beta, axis=1)

    alpha = evaluate_kinetic_energy_density(data, points, kind="alpha")
    beta = evaluate_kinetic_energy_density(data, points, kind="beta")
    total = evaluate_kinetic_energy_density(data, points, kind="total")
    spin = evaluate_kinetic_energy_density(data, points, kind="spin")

    np.testing.assert_allclose(alpha.tau, expected_alpha, atol=1e-12)
    np.testing.assert_allclose(beta.tau, expected_beta, atol=1e-12)
    np.testing.assert_allclose(total.tau, expected_alpha + expected_beta, atol=1e-12)
    np.testing.assert_allclose(spin.tau, expected_alpha - expected_beta, atol=1e-12)


def test_restricted_closed_shell_alpha_beta_ked_are_half_total() -> None:
    basis = BasisSet((BasisShell(0, 0, (0.9,), (1.0,)),))
    data = CalculationData(
        molecule=_molecule(),
        basis=basis,
        total_density=DensityMatrix(((2.0,),), "total"),
        records={"Number of alpha electrons": 1, "Number of beta electrons": 1},
    )
    points = np.array(((0.2, 0.1, -0.3), (0.4, -0.2, 0.5)), dtype=float)

    total = evaluate_kinetic_energy_density(data, points, kind="total")
    alpha = evaluate_kinetic_energy_density(data, points, kind="alpha")
    beta = evaluate_kinetic_energy_density(data, points, kind="beta")

    np.testing.assert_allclose(alpha.tau, 0.5 * total.tau, atol=1e-12)
    np.testing.assert_allclose(beta.tau, 0.5 * total.tau, atol=1e-12)


def test_spin_ked_rejects_unavailable_spin_density_instead_of_inference() -> None:
    basis = BasisSet((BasisShell(0, 0, (1.0,), (1.0,)),))
    data = CalculationData(
        molecule=_molecule(),
        basis=basis,
        total_density=DensityMatrix(((1.0,),), "total"),
    )

    with pytest.raises(DataUnavailableError, match="Spin density matrix is not available"):
        evaluate_kinetic_energy_density(data, np.zeros((1, 3)), kind="spin")


def test_ked_chunking_is_numerically_equivalent_to_one_batch() -> None:
    basis = BasisSet((BasisShell(0, 0, (1.0,), (1.0,)),))
    data = CalculationData(
        molecule=_molecule(),
        basis=basis,
        total_density=DensityMatrix(((1.3,),), "total"),
    )
    points = np.array(
        ((0.1, 0.2, 0.3), (0.2, -0.3, 0.4), (-0.4, 0.1, 0.2), (0.5, 0.2, -0.1)),
        dtype=float,
    )

    one_batch = evaluate_kinetic_energy_density(data, points)
    chunked = evaluate_kinetic_energy_density(data, points, chunk_size=2)

    np.testing.assert_allclose(chunked.tau, one_batch.tau, rtol=5e-15, atol=5e-16)
    assert chunked.convention == one_batch.convention
