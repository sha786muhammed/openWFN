"""Independent contracted s–h integral references at off-center points."""
import numpy as np
import pytest

from openwfn.analysis.gaussian_coulomb import electronic_potential
from openwfn.model import Atom, BasisSet, BasisShell, CalculationMetadata, DensityMatrix, Molecule


@pytest.mark.parametrize('momentum', range(6))
@pytest.mark.parametrize('pure', [False, True])
def test_contracted_off_center_coulomb(momentum, pure):
    gto = pytest.importorskip('pyscf.gto')
    # Centered He basis: no SCF or openWFN reference generation is involved.
    source = gto.M(atom='He 0 0 0', basis={'He': [[momentum, [1.3, .4], [.2, .7]]]}, cart=not pure, verbose=0)
    basis = BasisSet((BasisShell(0, momentum, (1.3, .2), (.4, .7), pure=pure),))
    molecule = Molecule((Atom(2, (0., 0., 0.)),), 0, 1, CalculationMetadata('analytic'))
    density = np.zeros((basis.n_functions, basis.n_functions))
    density[0, 0] = 1.
    record = DensityMatrix(tuple(map(tuple, density)), 'total')
    # Gaussian pure m=0 is first; PySCF has ascending m for d and higher.
    index = momentum if pure and momentum >= 2 else 0
    # Gaussian g/h Cartesian ordering starts with z**l; PySCF's alphabetical
    # ordering ends with it. Through f, the first Cartesian component is x**l.
    if not pure and momentum >= 4:
        index = source.nao_nr()-1
    overlap = source.intor('int1e_ovlp')[index, index]
    points = np.array([[.3, -.7, 1.1], [4.1, 3.2, -2.3], [100., 0., 0.]])
    values, diagnostics = electronic_potential(molecule, basis, record, points)
    references = []
    for point in points:
        with source.with_rinv_origin(point):
            references.append(-source.intor('int1e_rinv')[index, index]/overlap)
    assert values == pytest.approx(references, abs=1e-10)
    assert diagnostics['quadrature_passed']
