"""Orbital projections must preserve a named AO metric convention."""
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
    MolecularOrbitals,
    Molecule,
)

WATER = Path(__file__).resolve().parents[2]/'examples/water/water.fchk'


def test_lowdin_and_mulliken_independent_two_center_reference():
    from openwfn.analysis.composition import orbital_weights
    # Analytic eigensystem: symmetric bonding orbital gives exactly half on each AO.
    s = np.array([[1., .3], [.3, 1.]])
    c = np.ones((2, 1))/np.sqrt(2*1.3)
    for method in ('lowdin', 'mulliken'):
        weights, norms, diagnostics = orbital_weights(c, s, method)
        assert weights[:, 0] == pytest.approx([.5, .5], abs=1e-13)
        assert norms == pytest.approx([1.], abs=1e-13)
        assert diagnostics['overlap_condition_number'] == pytest.approx(1.3/.7)


def test_negative_mulliken_and_nonnegative_lowdin():
    from openwfn.analysis.composition import orbital_weights
    c = np.array([[1.], [-.1]])
    s = np.array([[1., .8], [.8, 1.]])
    mulliken, _, _ = orbital_weights(c, s, 'mulliken')
    lowdin, _, _ = orbital_weights(c, s, 'lowdin')
    assert mulliken[1, 0] < 0
    assert np.all(lowdin >= 0)
    assert mulliken.sum() == pytest.approx(1.)
    assert lowdin.sum() == pytest.approx(1.)


def test_registered_composition_partitions_and_raw_norm():
    result = load(WATER).orbital_composition(mo='homo')
    assert result.status == 'success'
    assert result.data['method'] == 'lowdin'
    for key in ('atom_contributions', 'angular_contributions', 'shell_contributions'):
        assert sum(row['fraction'] for row in result.data[key]) == pytest.approx(1., abs=1e-12)
    assert result.data['ao_metric_norm'] == pytest.approx(1., abs=1e-6)
    assert result.provenance['input_sha256']
    assert load(WATER).analyze('orbital-composition').data == result.data


def test_raw_bad_norm_is_partial_and_missing_beta_fails():
    molecule = Molecule((Atom(1, (0., 0., 0.)),), 0, 2, CalculationMetadata('analytic'))
    data = CalculationData(molecule, BasisSet((BasisShell(0, 0, (1.,), (1.,)),)), MolecularOrbitals((-.5,), ((2.,),), (1.,), 'alpha'))
    result = run_analysis_safe(data, 'orbital-composition')
    assert result.status == 'partial'
    assert result.data['ao_metric_norm'] == pytest.approx(4.)
    result = run_analysis_safe(replace(data, alpha_orbitals=None), 'orbital-composition')
    assert result.status == 'failed'


def test_projection_rejects_invalid_overlap_and_zero_norm():
    from openwfn.analysis.composition import orbital_weights
    for s in (np.array([[1., 2.], [2., 1.]]), np.array([[1., .3], [.1, 1.]])):
        with pytest.raises(ValueError):
            orbital_weights(np.ones((2, 1)), s, 'lowdin')
    with pytest.raises(ValueError, match='norm'):
        orbital_weights(np.zeros((2, 1)), np.eye(2), 'lowdin')
