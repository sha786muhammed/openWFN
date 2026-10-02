"""Closed-form Coulomb integral checks, independent of spatial density grids."""
import math

import numpy as np
import pytest

from openwfn.analysis.gaussian_coulomb import electronic_potential
from openwfn.model import Atom, BasisSet, BasisShell, CalculationMetadata, DensityMatrix, Molecule


def test_normalized_s_gaussian_at_origin_and_far_field():
    molecule = Molecule((Atom(1, (0., 0., 0.)),), 0, 2, CalculationMetadata("analytic"))
    basis = BasisSet((BasisShell(0, 0, (.7,), (1.,)),))
    density = DensityMatrix(((1.,),), 'total')
    points = np.array([[0., 0., 0.], [1., 0., 0.], [100., 0., 0.]])
    values, diagnostics = electronic_potential(molecule, basis, density, points)
    expected = [-2*math.sqrt(1.4/math.pi), -math.erf(math.sqrt(1.4)), -.01]
    assert values == pytest.approx(expected, abs=1e-11)
    assert diagnostics['quadrature_max_error'] < 1e-10


def test_integral_resource_checks_precede_evaluation():
    molecule = Molecule((Atom(1, (0., 0., 0.)),), 0, 2, CalculationMetadata("analytic"))
    basis = BasisSet((BasisShell(0, 0, (1.,), (1.,)),))
    density = DensityMatrix(((1.,),), 'total')
    with pytest.raises(ValueError, match='point'):
        electronic_potential(molecule, basis, density, np.zeros((1025, 3)))
    with pytest.raises(ValueError, match='finite'):
        electronic_potential(molecule, basis, density, np.array([[np.nan, 0., 0.]]))


@pytest.mark.parametrize('momentum', range(6))
@pytest.mark.parametrize('pure', [False, True])
def test_all_primitive_components_at_center(momentum, pure):
    """Independent radial expectation for every Cartesian/pure s through h AO."""
    import math

    exponent = .7
    molecule = Molecule((Atom(1, (0., 0., 0.)),), 0, 2, CalculationMetadata('analytic'))
    basis = BasisSet((BasisShell(0, momentum, (exponent,), (1.,), pure=pure),))
    expected = -math.sqrt(2*exponent)*math.gamma(momentum+1)/math.gamma(momentum+1.5)
    for index in range(basis.n_functions):
        matrix = np.zeros((basis.n_functions, basis.n_functions))
        matrix[index, index] = 1.
        density = DensityMatrix(tuple(map(tuple, matrix)), 'total')
        values, diagnostics = electronic_potential(molecule, basis, density, np.zeros((1, 3)))
        assert values[0] == pytest.approx(expected, abs=1e-12)
        assert diagnostics['quadrature_passed']
