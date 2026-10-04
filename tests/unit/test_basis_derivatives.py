import math

import numpy as np
import pytest

from openwfn.analysis.basis import _pure_transform, evaluate_ao_fields
from openwfn.model import Atom, BasisSet, BasisShell, CalculationMetadata, Molecule


def _atom() -> Molecule:
    return Molecule((Atom(1, (0.0, 0.0, 0.0)),), 0, 1, CalculationMetadata("fixture"))


def test_normalized_s_primitive_has_closed_form_value_gradient_and_hessian() -> None:
    alpha = 1.0
    basis = BasisSet((BasisShell(0, 0, (alpha,), (1.0,)),))
    point = np.array(((0.2, -0.3, 0.4),), dtype=float)

    fields = evaluate_ao_fields(basis, _atom(), point)

    xyz = point[0]
    norm = (2.0 * alpha / math.pi) ** 0.75
    value = norm * math.exp(-alpha * float(np.dot(xyz, xyz)))
    gradient = -2.0 * alpha * xyz * value
    hessian = 4.0 * alpha**2 * np.outer(xyz, xyz) * value
    hessian[np.diag_indices(3)] -= 2.0 * alpha * value

    assert fields.values.shape == (1, 1)
    assert fields.gradients.shape == (1, 1, 3)
    assert fields.hessians.shape == (1, 1, 3, 3)
    assert fields.values[0, 0] == pytest.approx(value, abs=1e-12)
    np.testing.assert_allclose(fields.gradients[0, 0], gradient, atol=1e-12)
    np.testing.assert_allclose(fields.hessians[0, 0], hessian, atol=1e-12)


def test_cartesian_p_x_derivatives_include_polynomial_and_gaussian_terms() -> None:
    alpha = 0.5
    basis = BasisSet((BasisShell(0, 1, (alpha,), (1.0,)),))
    point = np.array(((0.7, -0.2, 0.3),), dtype=float)

    fields = evaluate_ao_fields(basis, _atom(), point)

    x, y, z = point[0]
    norm = (2.0 * alpha / math.pi) ** 0.75 * math.sqrt(4.0 * alpha)
    radial = math.exp(-alpha * (x * x + y * y + z * z))
    value = norm * x * radial
    expected_gradient = norm * radial * np.array(
        (
            1.0 - 2.0 * alpha * x * x,
            -2.0 * alpha * x * y,
            -2.0 * alpha * x * z,
        )
    )
    expected_xx = norm * radial * (-6.0 * alpha * x + 4.0 * alpha**2 * x**3)
    expected_xy = norm * radial * (-2.0 * alpha * y + 4.0 * alpha**2 * x**2 * y)

    assert fields.values[0, 0] == pytest.approx(value, abs=1e-12)
    np.testing.assert_allclose(fields.gradients[0, 0], expected_gradient, atol=1e-12)
    assert fields.hessians[0, 0, 0, 0] == pytest.approx(expected_xx, abs=1e-12)
    assert fields.hessians[0, 0, 0, 1] == pytest.approx(expected_xy, abs=1e-12)
    assert fields.hessians[0, 0, 1, 0] == pytest.approx(expected_xy, abs=1e-12)


@pytest.mark.parametrize("momentum", (2, 3, 4, 5))
def test_pure_shell_derivatives_use_same_cartesian_to_pure_transform(momentum: int) -> None:
    point = np.array(((0.31, -0.27, 0.42),), dtype=float)
    cart_basis = BasisSet((BasisShell(0, momentum, (0.8,), (1.0,), pure=False),))
    pure_basis = BasisSet((BasisShell(0, momentum, (0.8,), (1.0,), pure=True),))

    cart = evaluate_ao_fields(cart_basis, _atom(), point)
    pure = evaluate_ao_fields(pure_basis, _atom(), point)
    transform = _pure_transform(momentum)

    np.testing.assert_allclose(pure.values, cart.values @ transform.T, atol=1e-12)
    np.testing.assert_allclose(
        pure.gradients,
        np.einsum("pac,qa->pqc", cart.gradients, transform),
        atol=1e-12,
    )
    np.testing.assert_allclose(
        pure.hessians,
        np.einsum("paij,qa->pqij", cart.hessians, transform),
        atol=1e-12,
    )


def test_combined_sp_shell_derivatives_keep_one_s_and_three_p_functions() -> None:
    basis = BasisSet((BasisShell(0, -1, (1.0,), (1.0,), p_coefficients=(0.5,)),))

    fields = evaluate_ao_fields(basis, _atom(), np.array(((0.2, 0.3, 0.4),)))

    assert fields.values.shape == (1, 4)
    assert fields.gradients.shape == (1, 4, 3)
    assert fields.hessians.shape == (1, 4, 3, 3)


@pytest.mark.parametrize(
    "points, derivatives, message",
    (
        (np.zeros((3,)), 2, "shape"),
        (np.array(((0.0, np.nan, 0.0),)), 2, "finite"),
        (np.zeros((1, 3)), 3, "derivatives"),
        (np.zeros((1, 3)), -1, "derivatives"),
    ),
)
def test_ao_field_validation_happens_before_evaluation(
    points: np.ndarray, derivatives: int, message: str
) -> None:
    basis = BasisSet((BasisShell(0, 0, (1.0,), (1.0,)),))

    with pytest.raises(ValueError, match=message):
        evaluate_ao_fields(basis, _atom(), points, derivatives=derivatives)


def test_derivative_order_one_returns_empty_hessian_component_axis() -> None:
    basis = BasisSet((BasisShell(0, 0, (1.0,), (1.0,)),))

    fields = evaluate_ao_fields(
        basis,
        _atom(),
        np.array(((0.2, 0.3, 0.4),)),
        derivatives=1,
    )

    assert fields.values.shape == (1, 1)
    assert fields.gradients.shape == (1, 1, 3)
    assert fields.hessians.shape == (1, 1, 0, 0)
