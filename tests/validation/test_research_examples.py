import importlib.util
import json
from hashlib import sha256
from pathlib import Path

import pytest


def test_larger_conjugated_example_has_independent_reference_checks(tmp_path):
    pytest.importorskip('pyscf')
    assert importlib.util.find_spec('scripts.validate_research_examples'), 'Research example procedure missing'
    from scripts.validate_research_examples import validate_biphenyl
    report = validate_biphenyl(tmp_path)
    assert report['atoms'] == 22
    assert report['formula'] == 'C12H10'
    assert report['reference']['status'] == 'passed'
    assert report['reference']['mayer_max_error'] < 2e-7
    assert report['reference']['dos_max_error'] < 2e-6
    assert report['reference']['density_point_max_error'] < 2e-7
    assert report['reference']['mulliken_charge_max_error'] < 2e-7
    assert report['reference']['lowdin_charge_max_error'] < 2e-7
    assert len(report['input_sha256']) == 64
    assert (tmp_path / 'biphenyl.molden').is_file()
    assert report['geometry_status'] == 'constructed, not optimized'


def test_bundled_biphenyl_matches_recorded_reference_charges_and_density():
    import numpy as np

    from openwfn.analysis.density import evaluate_density
    from openwfn.api import load

    directory = Path(__file__).resolve().parents[2] / 'examples/research-workflows/biphenyl'
    source = directory / 'biphenyl.molden'
    evidence = json.loads((directory / 'reference.json').read_text())
    assert sha256(source.read_bytes()).hexdigest() == evidence['input_sha256']
    calculation = load(source)
    reference = evidence['reference']
    for method in ('mulliken', 'lowdin'):
        observed = calculation.population(method)
        np.testing.assert_allclose(observed.data['atomic_charges'],
                                   reference[f'reference_{method}_charges'], rtol=0, atol=2e-7)
    data = calculation.data.calculation
    rho = evaluate_density(data.molecule, data.basis, data.total_density,
                           np.array(reference['reference_density_points_bohr']))
    np.testing.assert_allclose(rho, reference['reference_density_electron_per_bohr3'],
                               rtol=0, atol=2e-7)
