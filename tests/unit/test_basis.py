import math

import numpy as np
import pytest

from openwfn.analysis.basis import ao_atom_indices, evaluate_ao, overlap_matrix
from openwfn.constants import BOHR_TO_ANGSTROM
from openwfn.errors import DataUnavailableError
from openwfn.model import Atom, BasisSet, BasisShell, CalculationMetadata, Molecule


def _atom() -> Molecule:
    return Molecule((Atom(1, (0.0, 0.0, 0.0)),), 0, 1, CalculationMetadata("fixture"))


def test_normalized_s_primitive_has_analytic_value_at_origin() -> None:
    basis = BasisSet((BasisShell(0, 0, (1.0,), (1.0,)),))

    values = evaluate_ao(basis, _atom(), np.array(((0.0, 0.0, 0.0),)))

    expected = (2.0 / math.pi) ** 0.75
    assert values.shape == (1, 1)
    assert values[0, 0] == pytest.approx(expected, abs=1e-12)


def test_p_shell_uses_gaussian_x_y_z_function_order() -> None:
    basis = BasisSet((BasisShell(0, 1, (0.5,), (1.0,)),))

    values = evaluate_ao(basis, _atom(), np.array(((1.0, 0.0, 0.0),)))

    assert values.shape == (1, 3)
    assert values[0, 0] > 0.0
    assert values[0, 1:] == pytest.approx((0.0, 0.0), abs=1e-15)


def test_combined_sp_shell_produces_one_s_and_three_p_functions() -> None:
    basis = BasisSet((BasisShell(0, -1, (1.0,), (1.0,), p_coefficients=(0.5,)),))

    values = evaluate_ao(basis, _atom(), np.array(((0.2, 0.3, 0.4),)))

    assert values.shape == (1, 4)


def test_pure_d_shell_uses_gaussian_5d_order_and_normalization() -> None:
    basis = BasisSet((BasisShell(0, 2, (1.0,), (1.0,), pure=True),))
    points = np.array(
        (
            (0.0, 0.0, 1.0),
            (1.0, 0.0, 0.0),
            (1.0, 1.0, 0.0),
        )
    )

    values = evaluate_ao(basis, _atom(), points)
    matrix = overlap_matrix(basis, _atom())

    assert values.shape == (3, 5)
    # Gaussian FCHK pure-d order is c0, c1, s1, c2, s2.
    assert values[0, 0] > 0.0
    assert values[0, 1:] == pytest.approx((0.0, 0.0, 0.0, 0.0), abs=1e-15)
    assert values[1, 0] < 0.0
    assert values[1, 3] > 0.0
    assert values[1, (1, 2, 4)] == pytest.approx((0.0, 0.0, 0.0), abs=1e-15)
    assert values[2, 4] > 0.0
    np.testing.assert_allclose(matrix, np.eye(5), atol=1e-12)
    assert ao_atom_indices(basis) == (0, 0, 0, 0, 0)


@pytest.mark.parametrize(("momentum", "count"), ((3, 7), (4, 9), (5, 11)))
def test_pure_high_angular_momentum_shell_has_expected_function_count(
    momentum: int, count: int
) -> None:
    basis = BasisSet((BasisShell(0, momentum, (1.0,), (1.0,), pure=True),))
    points = np.array(((0.2, 0.3, 0.4),))

    values = evaluate_ao(basis, _atom(), points)

    assert values.shape == (1, count)
    assert ao_atom_indices(basis) == (0,) * count


@pytest.mark.parametrize(("momentum", "count"), ((3, 7), (4, 9), (5, 11)))
def test_pure_high_angular_momentum_overlap_is_orthonormal(momentum: int, count: int) -> None:
    basis = BasisSet((BasisShell(0, momentum, (1.0,), (1.0,), pure=True),))

    matrix = overlap_matrix(basis, _atom())

    np.testing.assert_allclose(matrix, np.eye(count), atol=1e-11)


def test_overlap_matrix_for_normalized_separated_s_functions() -> None:
    molecule = Molecule(
        (
            Atom(1, (0.0, 0.0, 0.0)),
            Atom(1, (BOHR_TO_ANGSTROM, 0.0, 0.0)),
        ),
        0,
        1,
        CalculationMetadata("fixture"),
    )
    basis = BasisSet(
        (
            BasisShell(0, 0, (1.0,), (1.0,)),
            BasisShell(1, 0, (1.0,), (1.0,)),
        )
    )

    matrix = overlap_matrix(basis, molecule)

    np.testing.assert_allclose(np.diag(matrix), (1.0, 1.0), atol=1e-12)
    assert matrix[0, 1] == pytest.approx(math.exp(-0.5), abs=1e-12)
    assert matrix[1, 0] == pytest.approx(matrix[0, 1], abs=1e-12)
    assert ao_atom_indices(basis) == (0, 1)


def test_combined_sp_shell_maps_all_four_functions_to_its_atom() -> None:
    basis = BasisSet(
        (BasisShell(2, -1, (1.0,), (1.0,), p_coefficients=(1.0,)),)
    )

    assert ao_atom_indices(basis) == (2, 2, 2, 2)


def test_unsupported_higher_angular_momentum_is_explicit() -> None:
    basis = BasisSet((BasisShell(0, 6, (1.0,), (1.0,), pure=True),))

    with pytest.raises(DataUnavailableError, match="[Pp]ure angular momentum 6"):
        evaluate_ao(basis, _atom(), np.zeros((1, 3)))
