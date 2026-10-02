"""Coarse Coulomb quadrature must not hide failed electron conservation."""
from pathlib import Path

import pytest

from openwfn.api import load
from openwfn.services import electrostatic_potential_point


def test_coarse_esp_is_partial_when_grid_electron_count_fails():
    pytest.importorskip('iodata')
    source = Path(__file__).resolve().parents[2]/'examples/everyday-qc/water.molden'
    result = electrostatic_potential_point(load(source).data.calculation, (1.13, 1.43, 1.73), 'electronic', .3, 4.)
    assert result.status == 'partial'
    assert result.data['grid_electron_conservation_error'] > .1
    assert any('conservation' in warning.lower() for warning in result.warnings)
