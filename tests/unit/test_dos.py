"""Orbital-energy DOS normalization, channel semantics and bounds."""
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from openwfn.api import load
from openwfn.model import Atom, CalculationData, CalculationMetadata, MolecularOrbitals, Molecule

WATER = Path(__file__).resolve().parents[2]/'examples/water/water.fchk'


def test_single_line_gaussian_against_closed_form_and_integral():
    from openwfn.analysis.spectra import gaussian_spectrum
    x = np.linspace(-2., 2., 1001)
    values = gaussian_spectrum(np.array([0.]), x, .2)
    assert values[500] == pytest.approx(1/(.2*math.sqrt(2*math.pi)), abs=1e-12)
    assert np.trapezoid(values, x) == pytest.approx(1., abs=1e-12)
    assert values == pytest.approx(np.exp(-.5*(x/.2)**2)/(.2*math.sqrt(2*math.pi)), abs=1e-12)


def test_dos_counts_orbitals_not_electrons_and_spin_channels():
    from openwfn.spectral_services import orbital_dos
    mol = Molecule((Atom(1, (0., 0., 0.)),), 0, 2, CalculationMetadata('analytic'))
    alpha = MolecularOrbitals((0.,), ((1.,),), (1.,), 'alpha')
    data = CalculationData(mol, alpha_orbitals=alpha, beta_orbitals=replace(alpha, spin='beta'))
    result = orbital_dos(data, sigma_ev=.2)
    assert result.data['orbital_count'] == 2
    assert result.data['integrated_dos'] == pytest.approx(2., abs=2e-6)
    assert np.asarray(result.data['total_dos']) == pytest.approx(np.asarray(result.data['channels']['alpha'])+result.data['channels']['beta'])
    restricted = replace(data, alpha_orbitals=replace(alpha, spin='restricted', occupations=(2.,)), beta_orbitals=None)
    assert orbital_dos(restricted).data['orbital_count'] == 1


def test_dos_truncation_and_grid_resolution_are_partial():
    result = load(WATER).dos(energy_min_ev=-1., energy_max_ev=1., sigma_ev=.2, points=11)
    assert result.status == 'partial'
    assert result.warnings
    assert result.data['integrated_dos'] < result.data['orbital_count']


@pytest.mark.parametrize('params', [{'sigma_ev': 0.}, {'sigma_ev': float('nan')}, {'points': 1}, {'points': 100001}, {'energy_min_ev': 2., 'energy_max_ev': 1.}, {'energy_min_ev': 1.}, {'spin': 'wrong'}])
def test_dos_bad_parameters_are_structured_failures(params):
    assert load(WATER).dos(**params).status == 'failed'


def test_dos_no_basis_dependency_and_beta_unavailable():
    calc = load(WATER)
    assert calc.dos().data == calc.analyze('dos').data
    assert calc.dos(spin='beta').status == 'failed'


def test_spectrum_csv_and_svg_exports(tmp_path):
    from openwfn.exporters.spectra import write_spectrum
    record = load(WATER).dos()
    write_spectrum(record, tmp_path/'dos.csv')
    import csv
    rows = list(csv.reader((tmp_path/'dos.csv').open()))
    assert rows[0][:2] == ['energy_ev', 'total_dos']
    assert len(rows) == len(record.data['energy_ev'])+1
    write_spectrum(record, tmp_path/'dos.svg')
    assert '<svg' in (tmp_path/'dos.svg').read_text()
    with pytest.raises(FileExistsError):
        write_spectrum(record, tmp_path/'dos.csv')
