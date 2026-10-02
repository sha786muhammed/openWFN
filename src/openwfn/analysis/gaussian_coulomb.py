"""Gaussian Coulomb integrals using exact Cartesian moments and bounded quadrature.

The Laplace representation of 1/r reduces the primitive-pair integral to a
smooth one-dimensional integral. No spatial electron-density grid is used.
Normalization, Cartesian ordering and pure transforms come from the AO core.
"""
from functools import cache
from math import comb, exp, pi

import numpy as np

from ..constants import BOHR_TO_ANGSTROM
from ..model import BasisSet, DensityMatrix, Molecule
from .basis import (
    _basis_transform,
    _contraction_scale,
    _double_factorial,
    _function_specs,
    _primitive_normalization,
)

MAX_COULOMB_POINTS = 1024
MAX_COULOMB_WORK = 100_000_000


@cache
def _nodes(count: int):
    x, w = np.polynomial.legendre.leggauss(count)
    return (x+1)/2, w/2


def _moment_product(mu_a, mu_b, variance, power_a: int, power_b: int):
    """Expectation of (X-A)^i (X-B)^j under a normal distribution."""
    total = np.zeros_like(mu_a)
    for i in range(power_a+1):
        for j in range(power_b+1):
            degree = i+j
            if degree % 2:
                continue
            total += (comb(power_a, i)*comb(power_b, j)*
                      mu_a**(power_a-i)*mu_b**(power_b-j)*
                      _double_factorial(degree-1)*variance**(degree//2))
    return total


def _primitive(alpha, beta, center_a, center_b, powers_a, powers_b, points, nodes):
    p = alpha+beta
    product_center = (alpha*center_a+beta*center_b)/p
    delta = points-product_center
    t = p*np.sum(delta**2, axis=1)
    x, weights = _nodes(nodes)
    # For large T, v=sqrt(T)*u resolves the narrow exponential without requiring
    # a spatial grid or an unbounded number of nodes. v>14 contributes below
    # exp(-196); the supported polynomial degree is at most 10 per axis.
    root_t = np.sqrt(np.maximum(t, 1.))
    upper = np.minimum(1., 14/root_t)
    u = upper[:, None]*x
    u2 = u*u
    mu = product_center[None, None, :] + delta[:, None, :]*u2[:, :, None]
    variance = (1-u2)/(2*p)
    polynomial = np.ones_like(u)
    for axis in range(3):
        polynomial *= _moment_product(mu[:, :, axis]-center_a[axis],
                                      mu[:, :, axis]-center_b[axis], variance,
                                      powers_a[axis], powers_b[axis])
    radial = np.exp(-t[:, None]*u2)
    prefactor = 2*pi/p*exp(-alpha*beta/p*float(np.sum((center_a-center_b)**2)))
    return prefactor*upper*np.sum(radial*polynomial*weights, axis=1)


def electronic_potential(molecule: Molecule, basis: BasisSet, density: DensityMatrix,
                         points_bohr: np.ndarray):
    """Return -Tr(P V) and 64/96-node convergence diagnostics in hartree/e."""
    points = np.asarray(points_bohr, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or not 1 <= len(points) <= MAX_COULOMB_POINTS:
        raise ValueError('Coulomb points must have shape (N,3), with 1 to 1024 points')
    if not np.all(np.isfinite(points)):
        raise ValueError('Coulomb points must be finite')
    matrix = np.asarray(density.values, dtype=float)
    if matrix.shape != (basis.n_functions, basis.n_functions):
        raise ValueError('Coulomb density dimension must agree with basis')
    if not np.all(np.isfinite(matrix)) or not np.allclose(matrix, matrix.T, atol=1e-10, rtol=1e-10):
        raise ValueError('Coulomb density must be finite and symmetric')
    specs = _function_specs(basis)
    primitive_count = sum(len(spec[1]) for spec in specs)
    work = primitive_count*(primitive_count+1)//2*len(points)*160
    if work > MAX_COULOMB_WORK:
        raise ValueError('Gaussian Coulomb work exceeds safety limit; evaluate fewer points or a smaller basis')
    if any(atom >= len(molecule.atoms) for atom, *_ in specs):
        raise ValueError('Coulomb basis center is outside molecule')
    if any(exponent <= 0 for _, exponents, *_ in specs for exponent in exponents):
        raise ValueError('Coulomb Gaussian exponents must be positive')
    transform = _basis_transform(basis)
    cartesian_density = transform.T @ matrix @ transform
    centers = [np.asarray(molecule.atoms[atom].coordinates)/BOHR_TO_ANGSTROM for atom, *_ in specs]
    contractions = []
    for _, exponents, coefficients, powers in specs:
        scale = _contraction_scale(exponents, coefficients, powers)
        contractions.append([coefficient*_primitive_normalization(exponent, powers)*scale
                             for exponent, coefficient in zip(exponents, coefficients, strict=True)])
    values = [np.zeros(len(points)), np.zeros(len(points))]
    for left, (_, exponents_a, _, powers_a) in enumerate(specs):
        for right in range(left+1):
            density_weight = cartesian_density[left, right]*(1 if left == right else 2)
            if density_weight == 0:
                continue
            _, exponents_b, _, powers_b = specs[right]
            for alpha, ca in zip(exponents_a, contractions[left], strict=True):
                for beta, cb in zip(exponents_b, contractions[right], strict=True):
                    coefficient = density_weight*ca*cb
                    if coefficient == 0:
                        continue
                    for index, count in enumerate((64, 96)):
                        values[index] -= coefficient*_primitive(alpha, beta, centers[left], centers[right],
                                                                 powers_a, powers_b, points, count)
    if not all(np.all(np.isfinite(value)) for value in values):
        raise ValueError('Gaussian Coulomb integration produced nonfinite values')
    error = float(np.max(np.abs(values[1]-values[0])))
    return values[1], {'quadrature_nodes': 96, 'quadrature_check_nodes': 64,
                       'quadrature_max_error': error, 'quadrature_passed': error <= 1e-10,
                       'estimated_primitive_node_work': work,
                       'method': 'Gaussian Coulomb integrals (Cartesian moments and auxiliary Gauss-Legendre quadrature)'}
