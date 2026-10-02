"""PDOS partitions sum to orbital-energy DOS without losing normalization warnings."""
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from openwfn.analysis.registry import run_analysis_safe
from openwfn.api import load

WATER = Path(__file__).resolve().parents[2]/'examples/water/water.fchk'


@pytest.mark.parametrize('group_by', ['atom', 'element', 'angular'])
@pytest.mark.parametrize('method', ['mulliken', 'lowdin'])
def test_pdos_sums_to_total_pointwise(group_by, method):
    result = load(WATER).pdos(group_by=group_by, method=method)
    assert result.status == 'success'
    assert result.data['projection_method'] == method
    assert result.data['group_by'] == group_by
    values = np.asarray(list(result.data['projections'].values()))
    assert values.sum(axis=0) == pytest.approx(result.data['total_dos'], abs=1e-10)
    assert result.data['projection_sum_max_error'] < 1e-10
    assert result.provenance['input_sha256']


def test_pdos_norm_error_is_not_hidden_by_normalized_projections():
    calc = load(WATER).data.calculation
    coefficients = np.asarray(calc.alpha_orbitals.coefficients)*2
    bad = replace(calc, alpha_orbitals=replace(calc.alpha_orbitals, coefficients=tuple(map(tuple, coefficients))))
    result = run_analysis_safe(bad, 'pdos')
    assert result.status == 'partial'
    assert result.data['max_raw_mo_norm_error'] > 2.9
    assert result.warnings


def test_pdos_limits_and_missing_basis_are_explicit():
    calc = load(WATER).data.calculation
    assert run_analysis_safe(replace(calc, basis=None), 'pdos').status == 'failed'
    assert load(WATER).pdos(group_by='fake').status == 'failed'
    assert load(WATER).pdos(method='fake').status == 'failed'
    result = load(WATER).pdos(spin='beta')
    assert result.status == 'failed'
    assert 'Beta' in result.error.message
