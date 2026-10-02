"""Signed orbital cubes: analytic invariants, routing and resource limits."""
import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from openwfn import services
from openwfn.api import load
from openwfn.cli import main
from openwfn.errors import DataUnavailableError
from openwfn.model import (
    Atom,
    BasisSet,
    BasisShell,
    CalculationData,
    CalculationMetadata,
    MolecularOrbitals,
    Molecule,
)

WATER = Path(__file__).resolve().parents[2] / 'examples/water/water.fchk'


def gaussian():
    molecule = Molecule((Atom(1, (0., 0., 0.)),), 0, 2, CalculationMetadata('analytic'))
    basis = BasisSet((BasisShell(0, 0, (1.,), (1.,)),))
    orbital = MolecularOrbitals((-.5,), ((-1.,),), (1.,), 'alpha')
    return CalculationData(molecule, basis, orbital)


def test_cube_matches_signed_normalized_gaussian_and_integral(tmp_path):
    grid = services.orbital_grid(gaussian(), 1, 'alpha', .2, 4., chunk_size=7)
    center = np.asarray(grid.values).reshape(grid.shape)[20, 20, 20]
    assert center == pytest.approx(-(2/math.pi)**.75, abs=1e-12)
    result = services.orbital_cube_export(gaussian(), 1, 'alpha', .2, 4., tmp_path/'h.cube', False)
    assert result.data['squared_amplitude_integral'] == pytest.approx(1., abs=1e-9)
    assert result.data['ao_metric_norm'] == pytest.approx(1., abs=1e-12)
    assert result.units['amplitude'] == 'bohr^-3/2'
    assert result.validation_status == 'Validated'
    assert 'mo=1' in (tmp_path/'h.cube').read_text().splitlines()[1]


def test_selector_homo_without_virtual_and_spin_errors():
    assert services.select_orbital(gaussian(), 'homo', 'alpha')[1] == 0
    with pytest.raises(DataUnavailableError, match='LUMO'):
        services.select_orbital(gaussian(), 'lumo', 'alpha')
    with pytest.raises(DataUnavailableError, match='Beta'):
        services.select_orbital(gaussian(), 1, 'beta')
    for value in (0, -1, 2, 'wrong', 1.5, True):
        with pytest.raises((ValueError, IndexError)):
            services.select_orbital(gaussian(), value, 'alpha')


def test_grid_chunk_equivalence_safety_and_bad_norm(tmp_path):
    a = services.orbital_grid(gaussian(), 1, 'alpha', .4, 3., chunk_size=1)
    b = services.orbital_grid(gaussian(), 1, 'alpha', .4, 3., chunk_size=40)
    assert a.values == pytest.approx(b.values, abs=1e-14)
    with pytest.raises(ValueError, match='safety limit'):
        services.orbital_grid(gaussian(), 1, 'alpha', .00001, 4.)
    with pytest.raises(DataUnavailableError, match='basis'):
        services.orbital_grid(replace(gaussian(), basis=None), 1, 'alpha', .4, 3.)
    bad = replace(gaussian(), alpha_orbitals=replace(gaussian().alpha_orbitals, coefficients=((2.,),)))
    result = services.orbital_cube_export(bad, 1, 'alpha', .4, 4., tmp_path/'bad.cube', False)
    assert result.status == 'partial'
    assert result.warnings


def test_api_cli_cube_parity_and_provenance(tmp_path, capsys):
    calc = load(WATER)
    api = calc.orbital_cube(tmp_path/'api.cube', mo='homo', spacing_bohr=.4, padding_bohr=4.)
    assert api.provenance['input_sha256']
    assert main(['--format', 'json', str(WATER), 'orbitals', 'cube', '--mo', 'homo', '--output', str(tmp_path/'cli.cube'), '--spacing', '.4', '--padding', '4']) == 0
    cli = json.loads(capsys.readouterr().out)
    assert cli['data']['squared_amplitude_integral'] == api.data['squared_amplitude_integral']
    assert cli['provenance']['input_sha256'] == api.provenance['input_sha256']
    assert (tmp_path/'api.cube').read_text() == (tmp_path/'cli.cube').read_text()


@pytest.mark.parametrize('format_id', ['fchk', 'molden', 'mwfn', 'wfn', 'wfx'])
def test_cross_format_signed_orbital_field(format_id):
    if format_id != 'fchk':
        pytest.importorskip('iodata')
    root = WATER.parents[2]
    source = WATER if format_id == 'fchk' else root/f'tests/fixtures/interop/{format_id}/water.{format_id}'
    native = services.orbital_grid(load(WATER).data.calculation, 'homo', 'alpha', .5, 3.)
    converted = services.orbital_grid(load(source).data.calculation, 'homo', 'alpha', .5, 3.)
    # File conventions can change a global MO phase; compare up to that phase.
    a, b = np.asarray(native.values), np.asarray(converted.values)
    phase = 1 if a @ b >= 0 else -1
    assert a == pytest.approx(phase*b, abs=1e-7)


@pytest.mark.parametrize('pure', [False, True])
def test_polarized_unrestricted_orbital_against_independent_gbasis(pure, tmp_path):
    pytest.importorskip('iodata')
    pytest.importorskip('gbasis')
    from gbasis.evals.eval import evaluate_basis

    from openwfn.analysis.orbitals import evaluate_orbital

    data = gaussian()
    basis = BasisSet((BasisShell(0, 2, (.7,), (1.,), pure=pure),))
    orbital = MolecularOrbitals((-.5,), tuple(((-1.)**i/(i+1),) for i in range(basis.n_functions)), (1.,), 'beta')
    data = replace(data, basis=basis, beta_orbitals=orbital)
    # Write independently interpretable FCHK through IOData is unnecessary here:
    # GBasis consumes the same physical shell definition in a separate evaluator.
    from gbasis.contractions import GeneralizedContractionShell
    shell = GeneralizedContractionShell(2, np.zeros(3), np.array([1.]), np.array([.7]), 'spherical' if pure else 'cartesian')
    points = np.array([[.2, .3, -.4], [.6, -.5, .7], [0., 0., 0.]])
    reference = evaluate_basis([shell], points)
    # GBasis Cartesian order is alphabetical, pure order is -l..+l; map explicitly.
    if pure:
        order = [2, 3, 1, 4, 0]
    else:
        order = [0, 3, 5, 1, 2, 4]
    reference = reference[order].T @ np.asarray(orbital.coefficients)[:, 0]
    actual = evaluate_orbital(data.molecule, data.basis, orbital, 0, points)
    assert actual == pytest.approx(reference, abs=1e-12)
