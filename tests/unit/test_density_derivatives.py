import math

import numpy as np
import pytest

from openwfn.analysis.density import evaluate_density
from openwfn.analysis.realspace import evaluate_density_fields
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


def _single_s_data(
    *,
    total: float = 1.0,
    spin: float | None = None,
    restricted_closed_shell: bool = False,
) -> CalculationData:
    records = (
        {"Number of alpha electrons": 1, "Number of beta electrons": 1}
        if restricted_closed_shell
        else {}
    )
    return CalculationData(
        molecule=_molecule(),
        basis=BasisSet((BasisShell(0, 0, (1.0,), (1.0,)),)),
        total_density=DensityMatrix(((total,),), "total"),
        spin_density=None if spin is None else DensityMatrix(((spin,),), "spin"),
        records=records,
    )


def _finite_difference_density(
    data: CalculationData,
    point: np.ndarray,
    *,
    step: float = 2.0e-4,
) -> tuple[np.ndarray, np.ndarray]:
    assert data.basis is not None
    assert data.total_density is not None

    def value(offset: np.ndarray) -> float:
        sample = (point + offset).reshape(1, 3)
        return float(
            evaluate_density(
                data.molecule,
                data.basis,
                data.total_density,
                sample,
            )[0]
        )

    origin = value(np.zeros(3))
    gradient = np.zeros(3)
    hessian = np.zeros((3, 3))
    for axis in range(3):
        offset = np.zeros(3)
        offset[axis] = step
        plus = value(offset)
        minus = value(-offset)
        gradient[axis] = (plus - minus) / (2.0 * step)
        hessian[axis, axis] = (plus - 2.0 * origin + minus) / step**2

    for left in range(3):
        for right in range(left):
            offset_left = np.zeros(3)
            offset_right = np.zeros(3)
            offset_left[left] = step
            offset_right[right] = step
            cross = (
                value(offset_left + offset_right)
                - value(offset_left - offset_right)
                - value(-offset_left + offset_right)
                + value(-offset_left - offset_right)
            ) / (4.0 * step**2)
            hessian[left, right] = cross
            hessian[right, left] = cross
    return gradient, hessian


def test_single_gaussian_density_has_closed_form_gradient_hessian_and_laplacian() -> None:
    data = _single_s_data()
    point = np.array(((0.2, -0.3, 0.4),), dtype=float)

    fields = evaluate_density_fields(data, point)

    xyz = point[0]
    alpha = 1.0
    normalization_squared = (2.0 * alpha / math.pi) ** 1.5
    rho = normalization_squared * math.exp(-2.0 * alpha * float(np.dot(xyz, xyz)))
    gradient = -4.0 * alpha * xyz * rho
    hessian = 16.0 * alpha**2 * np.outer(xyz, xyz) * rho
    hessian[np.diag_indices(3)] -= 4.0 * alpha * rho
    laplacian = float(np.trace(hessian))

    assert fields.rho.shape == (1,)
    assert fields.gradient.shape == (1, 3)
    assert fields.hessian.shape == (1, 3, 3)
    assert fields.laplacian.shape == (1,)
    assert fields.rho[0] == pytest.approx(rho, abs=1e-12)
    np.testing.assert_allclose(fields.gradient[0], gradient, atol=1e-12)
    np.testing.assert_allclose(fields.hessian[0], hessian, atol=1e-12)
    assert fields.laplacian[0] == pytest.approx(laplacian, abs=1e-12)
    np.testing.assert_allclose(fields.hessian, np.swapaxes(fields.hessian, 1, 2), atol=1e-13)


def test_density_derivatives_use_both_ao_factors_for_a_general_matrix() -> None:
    basis = BasisSet(
        (
            BasisShell(0, 0, (0.7,), (1.0,)),
            BasisShell(0, 0, (1.3,), (1.0,)),
        )
    )
    density = DensityMatrix(((1.1, 0.35), (-0.15, 0.6)), "total")
    data = CalculationData(molecule=_molecule(), basis=basis, total_density=density)
    point = np.array((0.31, -0.27, 0.42), dtype=float)

    fields = evaluate_density_fields(data, point.reshape(1, 3))
    expected_gradient, expected_hessian = _finite_difference_density(data, point)

    np.testing.assert_allclose(fields.gradient[0], expected_gradient, rtol=3e-6, atol=3e-7)
    np.testing.assert_allclose(fields.hessian[0], expected_hessian, rtol=3e-5, atol=3e-6)
    assert fields.laplacian[0] == pytest.approx(float(np.trace(expected_hessian)), rel=3e-5, abs=3e-6)


def test_restricted_closed_shell_alpha_beta_fields_are_half_total() -> None:
    data = _single_s_data(total=2.0, restricted_closed_shell=True)
    points = np.array(((0.2, 0.1, -0.3), (0.4, -0.2, 0.5)), dtype=float)

    total = evaluate_density_fields(data, points, kind="total")
    alpha = evaluate_density_fields(data, points, kind="alpha")
    beta = evaluate_density_fields(data, points, kind="beta")

    for component in ("rho", "gradient", "hessian", "laplacian"):
        total_value = getattr(total, component)
        np.testing.assert_allclose(getattr(alpha, component), 0.5 * total_value, atol=1e-12)
        np.testing.assert_allclose(getattr(beta, component), 0.5 * total_value, atol=1e-12)


def test_unrestricted_total_and_spin_channels_reconstruct_alpha_beta_fields() -> None:
    data = _single_s_data(total=1.4, spin=0.4)
    points = np.array(((0.17, -0.29, 0.33), (0.41, 0.12, -0.26)), dtype=float)

    total = evaluate_density_fields(data, points, kind="total")
    spin = evaluate_density_fields(data, points, kind="spin")
    alpha = evaluate_density_fields(data, points, kind="alpha")
    beta = evaluate_density_fields(data, points, kind="beta")

    for component in ("rho", "gradient", "hessian", "laplacian"):
        np.testing.assert_allclose(
            getattr(alpha, component) + getattr(beta, component),
            getattr(total, component),
            atol=1e-12,
        )
        np.testing.assert_allclose(
            getattr(alpha, component) - getattr(beta, component),
            getattr(spin, component),
            atol=1e-12,
        )


def test_density_field_chunking_is_numerically_identical_to_one_batch() -> None:
    data = _single_s_data(total=1.7)
    points = np.array(
        (
            (0.1, 0.2, 0.3),
            (0.2, -0.3, 0.4),
            (-0.4, 0.1, 0.2),
            (0.5, 0.2, -0.1),
            (-0.3, -0.2, 0.6),
        ),
        dtype=float,
    )

    one_batch = evaluate_density_fields(data, points)
    chunked = evaluate_density_fields(data, points, chunk_size=2)

    np.testing.assert_array_equal(chunked.rho, one_batch.rho)
    np.testing.assert_array_equal(chunked.gradient, one_batch.gradient)
    np.testing.assert_array_equal(chunked.hessian, one_batch.hessian)
    np.testing.assert_array_equal(chunked.laplacian, one_batch.laplacian)


def test_density_field_rejects_invalid_chunk_size_before_evaluation() -> None:
    data = _single_s_data()

    with pytest.raises(ValueError, match="chunk_size"):
        evaluate_density_fields(data, np.zeros((1, 3)), chunk_size=0)
