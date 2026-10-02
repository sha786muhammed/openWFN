"""Mayer formula checks with analytic restricted and spin-resolved densities."""
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from openwfn.analysis.registry import run_analysis_safe
from openwfn.api import load
from openwfn.model import (
    Atom,
    BasisSet,
    BasisShell,
    CalculationData,
    CalculationMetadata,
    DensityMatrix,
    MolecularOrbitals,
    Molecule,
)

WATER = Path(__file__).resolve().parents[2]/'examples/water/water.fchk'


def test_analytic_restricted_single_bond_and_unrestricted_half_bond():
    from openwfn.analysis.bondorder import mayer_matrix
    overlap = np.array([[1., .3], [.3, 1.]])
    p = np.ones((2, 2))/1.3
    restricted = mayer_matrix(p, np.zeros((2, 2)), overlap, (0, 1), 2)
    assert restricted == pytest.approx(np.array([[0., 1.], [1., 0.]]), abs=1e-12)
    # One alpha electron: P=Q=p/2, giving BO=0.5, not 0.25.
    unrestricted = mayer_matrix(p/2, p/2, overlap, (0, 1), 2)
    assert unrestricted == pytest.approx(np.array([[0., .5], [.5, 0.]]), abs=1e-12)


def test_independent_spin_channel_expression():
    from openwfn.analysis.bondorder import mayer_matrix
    s = np.array([[1., .2], [.2, 1.]])
    alpha = np.array([[.7, .3], [.3, .4]])
    beta = np.array([[.2, -.1], [-.1, .6]])
    reference = 2*((alpha@s)[0, 1]*(alpha@s)[1, 0] + (beta@s)[0, 1]*(beta@s)[1, 0])
    result = mayer_matrix(alpha+beta, alpha-beta, s, (0, 1), 2)
    assert result[0, 1] == pytest.approx(reference, abs=1e-14)


def test_mayer_service_filter_and_conservation():
    calc = load(WATER)
    result = calc.mayer(threshold=.1)
    assert result.status == 'success'
    matrix = np.asarray(result.data['bond_order_matrix'])
    assert matrix == pytest.approx(matrix.T)
    assert np.diag(matrix) == pytest.approx(np.zeros(3))
    assert matrix[0, 1] == pytest.approx(matrix[0, 2], abs=1e-8)
    assert result.data['bonded_valence'] == pytest.approx(matrix.sum(axis=1))
    assert all(abs(pair['bond_order']) >= .1 for pair in result.data['pairs'])
    assert result.data['charge_conservation_error'] < 1e-6
    assert calc.mayer(threshold=100.).data['pairs'] == []


def test_open_shell_without_spin_matrix_fails_instead_of_assuming_zero():
    molecule = Molecule((Atom(1, (0., 0., 0.)),), 0, 2, CalculationMetadata('analytic'))
    data = CalculationData(molecule, BasisSet((BasisShell(0, 0, (1.,), (1.,)),)), MolecularOrbitals((-.5,), ((1.,),), (1.,), 'alpha'), total_density=DensityMatrix(((1.,),), 'total'))
    result = run_analysis_safe(data, 'mayer')
    assert result.status == 'failed'
    assert 'Spin density' in result.error.message
    data = replace(data, spin_density=DensityMatrix(((1.,),), 'spin'))
    assert run_analysis_safe(data, 'mayer').status == 'success'
    for threshold in (-1., float('nan')):
        assert run_analysis_safe(data, 'mayer', threshold=threshold).status == 'failed'


def test_mayer_malformed_density_is_rejected():
    from openwfn.analysis.bondorder import mayer_matrix
    with pytest.raises(ValueError, match='symmetric'):
        mayer_matrix(np.array([[1., .3], [0., 1.]]), np.zeros((2, 2)), np.eye(2), (0, 1), 2)


@pytest.mark.parametrize('unrestricted', [False, True])
def test_independent_cclib_mbo_contraction(unrestricted):
    pytest.importorskip('cclib')
    from cclib.method import MBO
    from cclib.parser.data import ccData

    from openwfn.analysis.bondorder import mayer_matrix

    # The external evaluator independently builds occupied density; same
    # coefficient/overlap input isolates the contraction and spin convention.
    s = np.array([[1., .3], [.3, 1.]])
    bonding = np.ones(2)/np.sqrt(2*1.3)
    antibonding = np.array([1., -1.])/np.sqrt(2*.7)
    coeffs = np.array([bonding, antibonding])
    raw = ccData({'mocoeffs': [coeffs, coeffs] if unrestricted else [coeffs],
                  'homos': [0, -1] if unrestricted else [0], 'nbasis': 2,
                  'aooverlaps': s, 'aonames': ['H1_1S', 'H2_1S']})
    reference = MBO(raw, None, 50)
    assert reference.calculate()
    pa = np.outer(bonding, bonding)
    pb = np.zeros((2, 2)) if unrestricted else pa
    result = mayer_matrix(pa+pb, pa-pb, s, (0, 1), 2)
    assert result == pytest.approx(reference.fragresults.sum(axis=0), abs=1e-12)
