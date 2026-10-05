"""Vectorized normalized Gaussian basis evaluation with spherical D/F/G/H support."""

import math
from dataclasses import dataclass
from functools import cache, lru_cache

import numpy as np

from ..constants import BOHR_TO_ANGSTROM
from ..errors import DataUnavailableError
from ..model import BasisSet, Molecule


@dataclass(frozen=True, slots=True)
class AOFieldBatch:
    """Atomic-orbital values and requested analytic derivatives at points."""

    values: np.ndarray
    gradients: np.ndarray
    hessians: np.ndarray


# Gaussian FCHK uses special Cartesian ordering through F, then the reverse of
# the usual alphabetical Cartesian order for G and higher shells.
_GAUSSIAN_CARTESIAN_POWERS: dict[int, tuple[tuple[int, int, int], ...]] = {
    0: ((0, 0, 0),),
    1: ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    2: ((2, 0, 0), (0, 2, 0), (0, 0, 2), (1, 1, 0), (1, 0, 1), (0, 1, 1)),
    3: (
        (3, 0, 0),
        (0, 3, 0),
        (0, 0, 3),
        (1, 2, 0),
        (2, 1, 0),
        (2, 0, 1),
        (1, 0, 2),
        (0, 1, 2),
        (0, 2, 1),
        (1, 1, 1),
    ),
}


def _double_factorial(value: int) -> int:
    return 1 if value <= 0 else math.prod(range(value, 0, -2))


def _cartesian_powers(angular_momentum: int) -> tuple[tuple[int, int, int], ...]:
    """Return Gaussian FCHK Cartesian function ordering through H shells."""

    if angular_momentum in _GAUSSIAN_CARTESIAN_POWERS:
        return _GAUSSIAN_CARTESIAN_POWERS[angular_momentum]
    if 4 <= angular_momentum <= 5:
        alphabetical: list[tuple[int, int, int]] = []
        for nx in range(angular_momentum, -1, -1):
            for ny in range(angular_momentum - nx, -1, -1):
                nz = angular_momentum - nx - ny
                alphabetical.append((nx, ny, nz))
        return tuple(reversed(alphabetical))
    raise DataUnavailableError(
        f"Gaussian angular momentum {angular_momentum} is not supported by this evaluator."
    )


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


def _power(values: np.ndarray, exponent: int) -> np.ndarray:
    if exponent < 0:
        return np.zeros_like(values)
    if exponent == 0:
        return np.ones_like(values)
    return values**exponent


def _evaluate_contraction_fields(
    displacements: np.ndarray,
    exponents: tuple[float, ...],
    coefficients: tuple[float, ...],
    powers: tuple[int, int, int],
    *,
    derivatives: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n_points = len(displacements)
    value = np.zeros(n_points, dtype=float)
    gradient = np.zeros((n_points, 3), dtype=float) if derivatives >= 1 else np.empty((n_points, 0), dtype=float)
    hessian = (
        np.zeros((n_points, 3, 3), dtype=float)
        if derivatives >= 2
        else np.empty((n_points, 0, 0), dtype=float)
    )
    contraction_scale = _contraction_scale(exponents, coefficients, powers)
    radial_squared = np.sum(displacements * displacements, axis=1)

    for alpha, coefficient in zip(exponents, coefficients, strict=True):
        primitive_scale = coefficient * _primitive_normalization(alpha, powers) * contraction_scale
        radial = np.exp(-alpha * radial_squared)
        base = [_power(displacements[:, axis], powers[axis]) for axis in range(3)]
        primitive_value = primitive_scale * radial * base[0] * base[1] * base[2]
        value += primitive_value

        if derivatives >= 1:
            first = [
                powers[axis] * _power(displacements[:, axis], powers[axis] - 1)
                - 2.0 * alpha * _power(displacements[:, axis], powers[axis] + 1)
                for axis in range(3)
            ]
            for axis in range(3):
                others = [item for item in range(3) if item != axis]
                gradient[:, axis] += (
                    primitive_scale
                    * radial
                    * first[axis]
                    * base[others[0]]
                    * base[others[1]]
                )

        if derivatives >= 2:
            second = [
                powers[axis]
                * (powers[axis] - 1)
                * _power(displacements[:, axis], powers[axis] - 2)
                - 2.0
                * alpha
                * (2 * powers[axis] + 1)
                * _power(displacements[:, axis], powers[axis])
                + 4.0 * alpha**2 * _power(displacements[:, axis], powers[axis] + 2)
                for axis in range(3)
            ]
            for axis in range(3):
                others = [item for item in range(3) if item != axis]
                hessian[:, axis, axis] += (
                    primitive_scale
                    * radial
                    * second[axis]
                    * base[others[0]]
                    * base[others[1]]
                )
            for left in range(3):
                for right in range(left):
                    other = 3 - left - right
                    cross = primitive_scale * radial * first[left] * first[right] * base[other]
                    hessian[:, left, right] += cross
                    hessian[:, right, left] += cross

    return value, gradient, hessian


def _evaluate_contraction(
    displacements: np.ndarray,
    exponents: tuple[float, ...],
    coefficients: tuple[float, ...],
    powers: tuple[int, int, int],
) -> np.ndarray:
    return _evaluate_contraction_fields(
        displacements,
        exponents,
        coefficients,
        powers,
        derivatives=0,
    )[0]


Polynomial = dict[tuple[int, int, int], float]


def _poly_add_scaled(target: Polynomial, source: Polynomial, factor: float) -> None:
    for powers, coefficient in source.items():
        value = target.get(powers, 0.0) + factor * coefficient
        if abs(value) < 1e-15:
            target.pop(powers, None)
        else:
            target[powers] = value


def _poly_mul_axis(polynomial: Polynomial, axis: int) -> Polynomial:
    result: Polynomial = {}
    for powers, coefficient in polynomial.items():
        updated = list(powers)
        updated[axis] += 1
        key = tuple(updated)
        result[key] = result.get(key, 0.0) + coefficient
    return result


def _poly_mul_r2(polynomial: Polynomial) -> Polynomial:
    result: Polynomial = {}
    for axis in range(3):
        squared = _poly_mul_axis(_poly_mul_axis(polynomial, axis), axis)
        _poly_add_scaled(result, squared, 1.0)
    return result


def _scaled_polynomial(polynomial: Polynomial, factor: float) -> Polynomial:
    return {powers: factor * coefficient for powers, coefficient in polynomial.items()}


@cache
def _real_solid_harmonics(angular_momentum: int) -> tuple[Polynomial, ...]:
    """Generate C(l,m)/S(l,m) homogeneous polynomials in Gaussian pure order."""

    if not 2 <= angular_momentum <= 5:
        raise DataUnavailableError(
            f"Pure angular momentum {angular_momentum} is not supported; validated range is 2 through 5."
        )

    cosine: dict[tuple[int, int], Polynomial] = {
        (0, 0): {(0, 0, 0): 1.0},
        (1, 0): {(0, 0, 1): 1.0},
        (1, 1): {(1, 0, 0): 1.0},
    }
    sine: dict[tuple[int, int], Polynomial] = {
        (1, 1): {(0, 1, 0): 1.0},
    }

    for degree in range(2, angular_momentum + 1):
        edge_scale = math.sqrt((2 * degree - 1) / (2 * degree))

        c_edge: Polynomial = {}
        _poly_add_scaled(c_edge, _poly_mul_axis(cosine[(degree - 1, degree - 1)], 0), edge_scale)
        _poly_add_scaled(c_edge, _poly_mul_axis(sine[(degree - 1, degree - 1)], 1), -edge_scale)
        cosine[(degree, degree)] = c_edge

        s_edge: Polynomial = {}
        _poly_add_scaled(s_edge, _poly_mul_axis(sine[(degree - 1, degree - 1)], 0), edge_scale)
        _poly_add_scaled(s_edge, _poly_mul_axis(cosine[(degree - 1, degree - 1)], 1), edge_scale)
        sine[(degree, degree)] = s_edge

        near_edge_scale = math.sqrt(2 * degree - 1)
        cosine[(degree, degree - 1)] = _scaled_polynomial(
            _poly_mul_axis(cosine[(degree - 1, degree - 1)], 2), near_edge_scale
        )
        sine[(degree, degree - 1)] = _scaled_polynomial(
            _poly_mul_axis(sine[(degree - 1, degree - 1)], 2), near_edge_scale
        )

        for magnetic in range(0, degree - 1):
            z_scale = (2 * degree - 1) / math.sqrt(
                (degree + magnetic) * (degree - magnetic)
            )
            r2_scale = math.sqrt(
                ((degree - magnetic - 1) * (degree + magnetic - 1))
                / ((degree + magnetic) * (degree - magnetic))
            )

            c_poly: Polynomial = {}
            _poly_add_scaled(
                c_poly,
                _poly_mul_axis(cosine[(degree - 1, magnetic)], 2),
                z_scale,
            )
            _poly_add_scaled(
                c_poly,
                _poly_mul_r2(cosine[(degree - 2, magnetic)]),
                -r2_scale,
            )
            cosine[(degree, magnetic)] = c_poly

            if magnetic > 0:
                s_poly: Polynomial = {}
                _poly_add_scaled(
                    s_poly,
                    _poly_mul_axis(sine[(degree - 1, magnetic)], 2),
                    z_scale,
                )
                _poly_add_scaled(
                    s_poly,
                    _poly_mul_r2(sine[(degree - 2, magnetic)]),
                    -r2_scale,
                )
                sine[(degree, magnetic)] = s_poly

    ordered: list[Polynomial] = [cosine[(angular_momentum, 0)]]
    for magnetic in range(1, angular_momentum + 1):
        ordered.append(cosine[(angular_momentum, magnetic)])
        ordered.append(sine[(angular_momentum, magnetic)])
    return tuple(ordered)


@cache
def _pure_transform(angular_momentum: int) -> np.ndarray:
    """Return normalized Cartesian-to-real-spherical transform in Gaussian order."""

    if not 2 <= angular_momentum <= 5:
        raise DataUnavailableError(
            f"Pure angular momentum {angular_momentum} is not supported; validated range is 2 through 5."
        )

    cartesian = _cartesian_powers(angular_momentum)
    pure_denominator = _double_factorial(2 * angular_momentum - 1)
    rows: list[list[float]] = []
    for polynomial in _real_solid_harmonics(angular_momentum):
        row: list[float] = []
        for powers in cartesian:
            cartesian_denominator = math.prod(
                _double_factorial(2 * power - 1) for power in powers
            )
            normalization_ratio = math.sqrt(cartesian_denominator / pure_denominator)
            row.append(polynomial.get(powers, 0.0) * normalization_ratio)
        rows.append(row)

    transform = np.asarray(rows, dtype=float)
    transform.setflags(write=False)
    return transform


def _validate_field_request(points_bohr: np.ndarray, derivatives: int) -> np.ndarray:
    points = np.asarray(points_bohr, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points_bohr must have shape (n_points, 3)")
    if not np.all(np.isfinite(points)):
        raise ValueError("points_bohr coordinates must be finite")
    if isinstance(derivatives, bool) or not isinstance(derivatives, int) or derivatives not in (0, 1, 2):
        raise ValueError("derivatives must be one of 0, 1, or 2")
    return points


def evaluate_ao_fields(
    basis: BasisSet,
    molecule: Molecule,
    points_bohr: np.ndarray,
    *,
    derivatives: int = 2,
) -> AOFieldBatch:
    """Evaluate ordered AOs and analytic Cartesian derivatives at Bohr points."""

    points = _validate_field_request(points_bohr, derivatives)
    value_columns: list[np.ndarray] = []
    gradient_columns: list[np.ndarray] = []
    hessian_columns: list[np.ndarray] = []

    def append_fields(fields: tuple[np.ndarray, np.ndarray, np.ndarray]) -> None:
        value_columns.append(fields[0])
        gradient_columns.append(fields[1])
        hessian_columns.append(fields[2])

    for shell in basis.shells:
        if shell.atom_index >= len(molecule.atoms):
            raise ValueError("basis shell atom index exceeds molecule atom count")
        center_bohr = np.asarray(molecule.atoms[shell.atom_index].coordinates) / BOHR_TO_ANGSTROM
        displacement = points - center_bohr
        if shell.angular_momentum == -1:
            if shell.p_coefficients is None:
                raise ValueError("combined sp shell requires p coefficients")
            append_fields(
                _evaluate_contraction_fields(
                    displacement,
                    shell.exponents,
                    shell.coefficients,
                    (0, 0, 0),
                    derivatives=derivatives,
                )
            )
            for powers in _cartesian_powers(1):
                append_fields(
                    _evaluate_contraction_fields(
                        displacement,
                        shell.exponents,
                        shell.p_coefficients,
                        powers,
                        derivatives=derivatives,
                    )
                )
            continue

        powers_order = _cartesian_powers(shell.angular_momentum)
        shell_fields = [
            _evaluate_contraction_fields(
                displacement,
                shell.exponents,
                shell.coefficients,
                powers,
                derivatives=derivatives,
            )
            for powers in powers_order
        ]
        if shell.pure and shell.angular_momentum >= 2:
            transform = _pure_transform(shell.angular_momentum)
            cartesian_values = np.column_stack([item[0] for item in shell_fields])
            pure_values = cartesian_values @ transform.T
            if derivatives >= 1:
                cartesian_gradients = np.stack([item[1] for item in shell_fields], axis=1)
                pure_gradients = np.einsum("pac,qa->pqc", cartesian_gradients, transform)
            else:
                pure_gradients = np.empty((len(points), transform.shape[0], 0), dtype=float)
            if derivatives >= 2:
                cartesian_hessians = np.stack([item[2] for item in shell_fields], axis=1)
                pure_hessians = np.einsum("paij,qa->pqij", cartesian_hessians, transform)
            else:
                pure_hessians = np.empty((len(points), transform.shape[0], 0, 0), dtype=float)
            for index in range(transform.shape[0]):
                append_fields(
                    (
                        pure_values[:, index],
                        pure_gradients[:, index, :],
                        pure_hessians[:, index, :, :],
                    )
                )
        else:
            for fields in shell_fields:
                append_fields(fields)

    values = np.column_stack(value_columns) if value_columns else np.empty((len(points), 0), dtype=float)
    if derivatives >= 1:
        gradients = np.stack(gradient_columns, axis=1) if gradient_columns else np.empty((len(points), 0, 3), dtype=float)
    else:
        gradients = np.empty((len(points), values.shape[1], 0), dtype=float)
    if derivatives >= 2:
        hessians = np.stack(hessian_columns, axis=1) if hessian_columns else np.empty((len(points), 0, 3, 3), dtype=float)
    else:
        hessians = np.empty((len(points), values.shape[1], 0, 0), dtype=float)
    return AOFieldBatch(values=values, gradients=gradients, hessians=hessians)


def evaluate_ao(basis: BasisSet, molecule: Molecule, points_bohr: np.ndarray) -> np.ndarray:
    """Evaluate ordered atomic-orbital basis functions at Bohr-coordinate points."""

    return evaluate_ao_fields(basis, molecule, points_bohr, derivatives=0).values


def _function_specs(
    basis: BasisSet,
) -> list[tuple[int, tuple[float, ...], tuple[float, ...], tuple[int, int, int]]]:
    """Return the Cartesian working representation used for analytic overlaps."""

    specs: list[tuple[int, tuple[float, ...], tuple[float, ...], tuple[int, int, int]]] = []
    for shell in basis.shells:
        if shell.angular_momentum == -1:
            if shell.p_coefficients is None:
                raise ValueError("combined sp shell requires p coefficients")
            specs.append((shell.atom_index, shell.exponents, shell.coefficients, (0, 0, 0)))
            specs.extend(
                (shell.atom_index, shell.exponents, shell.p_coefficients, powers)
                for powers in _cartesian_powers(1)
            )
            continue
        if shell.pure and shell.angular_momentum >= 2:
            _pure_transform(shell.angular_momentum)
        specs.extend(
            (shell.atom_index, shell.exponents, shell.coefficients, powers)
            for powers in _cartesian_powers(shell.angular_momentum)
        )
    return specs


def _basis_transform(basis: BasisSet) -> np.ndarray:
    """Map the Cartesian working basis into Gaussian's final AO ordering."""

    cartesian_size = 0
    final_size = 0
    blocks: list[tuple[int, int, np.ndarray]] = []
    for shell in basis.shells:
        if shell.angular_momentum == -1:
            block = np.eye(4, dtype=float)
        elif shell.pure and shell.angular_momentum >= 2:
            block = _pure_transform(shell.angular_momentum)
        else:
            block = np.eye(len(_cartesian_powers(shell.angular_momentum)), dtype=float)
        blocks.append((final_size, cartesian_size, block))
        final_size += block.shape[0]
        cartesian_size += block.shape[1]

    transform = np.zeros((final_size, cartesian_size), dtype=float)
    for final_offset, cartesian_offset, block in blocks:
        rows, columns = block.shape
        transform[
            final_offset : final_offset + rows,
            cartesian_offset : cartesian_offset + columns,
        ] = block
    return transform


def ao_atom_indices(basis: BasisSet) -> tuple[int, ...]:
    """Return the zero-based center atom for each AO in Gaussian function order."""

    return tuple(
        shell.atom_index
        for shell in basis.shells
        for _ in range(shell.n_functions)
    )


@lru_cache(maxsize=4096)
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
    """Evaluate the normalized AO overlap matrix analytically."""

    specs = _function_specs(basis)
    centers = [np.asarray(molecule.atoms[atom].coordinates) / BOHR_TO_ANGSTROM for atom, *_ in specs]
    cartesian_matrix = np.empty((len(specs), len(specs)), dtype=float)
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
            cartesian_matrix[left, right] = cartesian_matrix[right, left] = value * scale_a * scale_b

    transform = _basis_transform(basis)
    return transform @ cartesian_matrix @ transform.T


def bounded_ao_chunk_size(basis: BasisSet, requested: int, *, working_bytes: int = 128*1024**2) -> int:
    """Conservative AO temporary estimate, including Cartesian/pure expansion.

    This bounds point-dependent arrays, not total process RSS or density-matrix
    storage. Contraction normalization and NumPy/library overhead are separate.
    """
    if isinstance(requested, bool) or not isinstance(requested, int) or requested <= 0:
        raise ValueError("chunk size must be a positive integer")
    if isinstance(working_bytes, bool) or not isinstance(working_bytes, int) or working_bytes <= 0:
        raise ValueError("working memory budget must be a positive integer")
    cartesian_count = len(_function_specs(basis))
    max_primitives = max((len(shell.exponents) for shell in basis.shells), default=0)
    per_point = 8*(3*cartesian_count + 2*basis.n_functions + 2*max_primitives + 20)
    if per_point > working_bytes:
        raise ValueError("AO temporary memory estimate exceeds budget even for one point")
    return min(requested, max(1, working_bytes//per_point))
