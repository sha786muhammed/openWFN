"""Public ESP defaults avoid spatial-grid singularities and inaccurate grids."""
import json
from pathlib import Path

import pytest

from openwfn.api import load
from openwfn.cli import main

ROOT = Path(__file__).resolve().parents[2]


def test_default_electronic_esp_at_nucleus_and_api_parity(capsys):
    pytest.importorskip('iodata')
    source = ROOT/'examples/everyday-qc/water.molden'
    api = load(source).esp((0., 0., 0.), component='electronic')
    assert api.status == 'success'
    assert api.data['method'] == 'integrals'
    assert api.data['value'] < -10
    assert main(['--format', 'json', str(source), 'esp', 'point', '0', '0', '0', '--component', 'electronic']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['data'] == api.data
    assert result['provenance']['input_sha256'] == api.provenance['input_sha256']


def test_integral_method_corrects_charged_grid_failure():
    pytest.importorskip('iodata')
    source = ROOT/'examples/everyday-qc/ammonium_cation.molden'
    calc = load(source)
    result = calc.esp((1.127, 1.434, 1.741), method='integrals')
    assert result.status == 'success'
    assert result.data['electron_conservation_error'] < 1e-6
    assert result.data['quadrature_max_error'] < 1e-10
    assert calc.esp((0., 0., 0.), component='nuclear').status == 'failed'
