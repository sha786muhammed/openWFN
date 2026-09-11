"""Vectorized normalized Cartesian Gaussian basis evaluation."""

import math

import numpy as np

from ..constants import BOHR_TO_ANGSTROM
from ..errors import DataUnavailableError
from ..model import BasisSet, Molecule

_CARTESIAN_POWERS: dict[int, tuple[tuple[int, int, int], ...]] = {
    0: ((0, 0, 0),),
    1: ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    2: ((2, 0, 0), (0, 2, 0), (0, 0, 2), (1, 1, 0), (1, 0, 1), (0, 1, 1)),
    3: (
        (3, 0, 0), (0, 3, 0), (0, 0, 3), (1, 2, 0), (2, 1, 0),
        (2, 0, 1), (1, 0, 2), (0, 1, 2), (0, 2, 1), (1, 1, 1),
    ),
}


def _double_factorial(value: int) -> int:
    return 1 if value <= 0 else math.prod(range(value, 0, -2))


def _primitive_normalization(alpha: float, powers: tuple[int, int, int]) -> float:
    lx, ly, lz = powers
    denominator = math.sqrt(
        _double_factorial(2 * lx - 1)
        * _double_factorial(2 * ly - 1)
        * _double_factorial(2 * lz - 1)
    )
    return (2.0 * alpha / math.pi) ** 0.75 * (4.0 * alpha) ** ((lx + ly + lz) / 2.0) / denominator


def _primitive_overlap(alpha: float, beta: float, powers: tuple[int, int, int]) -> float:
    exponent = alpha + beta
    integral = 1.0
    for power in powers:
        integral *= (
            _double_factorial(2 * power - 1)
            * math.sqrt(math.pi)
            / (2.0**power * exponent ** (power + 0.5))
        )
    return _primitive_normalization(alpha, powers) * _primitive_normalization(beta, powers) * integral


def _evaluate_contraction(
    displacements: np.ndarray,
    exponents: tuple[float, ...],
    coefficients: tuple[float, ...],
    powers: tuple[int, int, int],
) -> np.ndarray:
    coefficient_array = np.asarray(coefficients, dtype=float)
    exponent_array = np.asarray(exponents, dtype=float)
    overlap = np.array(
        [[_primitive_overlap(alpha, beta, powers) for beta in exponent_array] for alpha in exponent_array]
    )
    norm_squared = float(coefficient_array @ overlap @ coefficient_array)
    if norm_squared <= 0.0:
        raise ValueError("contracted Gaussian normalization is not positive")
    contraction_scale = 1.0 / math.sqrt(norm_squared)
    radial_squared = np.sum(displacements * displacements, axis=1)
    radial = np.exp(-np.outer(radial_squared, exponent_array))
    primitive_norms = np.asarray([_primitive_normalization(alpha, powers) for alpha in exponent_array])
    polynomial = (
        displacements[:, 0] ** powers[0]
        * displacements[:, 1] ** powers[1]
        * displacements[:, 2] ** powers[2]
    )
    return polynomial * (radial @ (coefficient_array * primitive_norms)) * contraction_scale


def evaluate_ao(basis: BasisSet, molecule: Molecule, points_bohr: np.ndarray) -> np.ndarray:
    """Evaluate ordered atomic-orbital basis functions at Bohr-coordinate points."""

    points = np.asarray(points_bohr, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points_bohr must have shape (n_points, 3)")
    columns: list[np.ndarray] = []
    for shell in basis.shells:
        if shell.atom_index >= len(molecule.atoms):
            raise ValueError("basis shell atom index exceeds molecule atom count")
        center_bohr = np.asarray(molecule.atoms[shell.atom_index].coordinates) / BOHR_TO_ANGSTROM
        displacement = points - center_bohr
        if shell.angular_momentum == -1:
            if shell.p_coefficients is None:
                raise ValueError("combined sp shell requires p coefficients")
            columns.append(_evaluate_contraction(displacement, shell.exponents, shell.coefficients, (0, 0, 0)))
            for powers in _CARTESIAN_POWERS[1]:
                columns.append(_evaluate_contraction(displacement, shell.exponents, shell.p_coefficients, powers))
            continue
        if shell.angular_momentum not in _CARTESIAN_POWERS:
            raise DataUnavailableError(
                f"Gaussian angular momentum {shell.angular_momentum} is not supported by this evaluator."
            )
        if shell.pure and shell.angular_momentum >= 2:
            raise DataUnavailableError(
                f"Pure angular momentum {shell.angular_momentum} requires a spherical transformation."
            )
        for powers in _CARTESIAN_POWERS[shell.angular_momentum]:
            columns.append(_evaluate_contraction(displacement, shell.exponents, shell.coefficients, powers))
    return np.column_stack(columns) if columns else np.empty((len(points), 0), dtype=float)


def _function_specs(
    basis: BasisSet,
) -> list[tuple[int, tuple[float, ...], tuple[float, ...], tuple[int, int, int]]]:
    specs: list[tuple[int, tuple[float, ...], tuple[float, ...], tuple[int, int, int]]] = []
    for shell in basis.shells:
        if shell.angular_momentum == -1:
            if shell.p_coefficients is None:
                raise ValueError("combined sp shell requires p coefficients")
            specs.append((shell.atom_index, shell.exponents, shell.coefficients, (0, 0, 0)))
            specs.extend(
                (shell.atom_index, shell.exponents, shell.p_coefficients, powers)
                for powers in _CARTESIAN_POWERS[1]
            )
            continue
        if shell.angular_momentum not in _CARTESIAN_POWERS:
            raise DataUnavailableError(
                f"Gaussian angular momentum {shell.angular_momentum} is not supported by this evaluator."
            )
        if shell.pure and shell.angular_momentum >= 2:
            raise DataUnavailableError(
                f"Pure angular momentum {shell.angular_momentum} requires a spherical transformation."
            )
        specs.extend(
            (shell.atom_index, shell.exponents, shell.coefficients, powers)
            for powers in _CARTESIAN_POWERS[shell.angular_momentum]
        )
    return specs


def ao_atom_indices(basis: BasisSet) -> tuple[int, ...]:
    """Return the zero-based center atom for each AO in Gaussian function order."""

    return tuple(spec[0] for spec in _function_specs(basis))


def _contraction_scale(
    exponents: tuple[float, ...],
    coefficients: tuple[float, ...],
    powers: tuple[int, int, int],
) -> float:
    coefficient_array = np.asarray(coefficients, dtype=float)
    exponent_array = np.asarray(exponents, dtype=float)
    primitive_overlap = np.array(
        [[_primitive_overlap(alpha, beta, powers) for beta in exponent_array] for alpha in exponent_array]
    )
    norm_squared = float(coefficient_array @ primitive_overlap @ coefficient_array)
    if norm_squared <= 0.0:
        raise ValueError("contracted Gaussian normalization is not positive")
    return 1.0 / math.sqrt(norm_squared)


def _overlap_1d(
    alpha: float,
    beta: float,
    center_a: float,
    center_b: float,
    power_a: int,
    power_b: int,
) -> float:
    exponent = alpha + beta
    product_center = (alpha * center_a + beta * center_b) / exponent
    prefactor = math.exp(-alpha * beta / exponent * (center_a - center_b) ** 2)
    total = 0.0
    for i in range(power_a + 1):
        for j in range(power_b + 1):
            power = i + j
            if power % 2:
                continue
            moment = (
                _double_factorial(power - 1)
                * math.sqrt(math.pi)
                / (2.0 ** (power / 2) * exponent ** (power / 2 + 0.5))
            )
            total += (
                math.comb(power_a, i)
                * math.comb(power_b, j)
                * (product_center - center_a) ** (power_a - i)
                * (product_center - center_b) ** (power_b - j)
                * moment
            )
    return prefactor * total


def overlap_matrix(basis: BasisSet, molecule: Molecule) -> np.ndarray:
    """Evaluate the normalized Cartesian AO overlap matrix analytically."""

    specs = _function_specs(basis)
    centers = [np.asarray(molecule.atoms[atom].coordinates) / BOHR_TO_ANGSTROM for atom, *_ in specs]
    matrix = np.empty((len(specs), len(specs)), dtype=float)
    for left, (_, exponents_a, coefficients_a, powers_a) in enumerate(specs):
        scale_a = _contraction_scale(exponents_a, coefficients_a, powers_a)
        for right in range(left + 1):
            _, exponents_b, coefficients_b, powers_b = specs[right]
            scale_b = _contraction_scale(exponents_b, coefficients_b, powers_b)
            value = 0.0
            for alpha, coefficient_a in zip(exponents_a, coefficients_a, strict=True):
                for beta, coefficient_b in zip(exponents_b, coefficients_b, strict=True):
                    integral = math.prod(
                        _overlap_1d(
                            alpha,
                            beta,
                            float(centers[left][axis]),
                            float(centers[right][axis]),
                            powers_a[axis],
                            powers_b[axis],
                        )
                        for axis in range(3)
                    )
                    value += (
                        coefficient_a
                        * coefficient_b
                        * _primitive_normalization(alpha, powers_a)
                        * _primitive_normalization(beta, powers_b)
                        * integral
                    )
            matrix[left, right] = matrix[right, left] = value * scale_a * scale_b
    return matrix
