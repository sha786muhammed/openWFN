from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from openwfn.analysis.grids import molecular_grid_points
from openwfn.constants import BOHR_TO_ANGSTROM
from openwfn.exporters.cube import format_cube, write_cube
from openwfn.model import VolumetricGrid
from openwfn.parsers.gaussian.fchk import parse_fchk

ROOT = Path(__file__).resolve().parents[2]


def test_grid_matches_original_ij_order_without_mesh_temporaries():
    molecule = parse_fchk(ROOT/'examples/water/water.fchk').molecule
    with patch('openwfn.analysis.grids.np.meshgrid', side_effect=AssertionError('mesh allocation')):
        points, origin, shape = molecular_grid_points(molecule, spacing_bohr=.4, padding_bohr=2.)
    axes = [origin[i]+np.arange(shape[i])*.4 for i in range(3)]
    expected = np.column_stack([a.ravel() for a in np.meshgrid(*axes, indexing='ij')])
    np.testing.assert_array_equal(points, expected)


def fixture_grid():
    return VolumetricGrid(origin=(0., 0., 0.),
        axes=((BOHR_TO_ANGSTROM, 0., 0.), (0., BOHR_TO_ANGSTROM, 0.), (0., 0., BOHR_TO_ANGSTROM)),
        shape=(2, 2, 2), values=tuple(float(i) for i in range(8)), value_unit='e/bohr^3')


def test_writer_does_not_materialize_entire_cube(tmp_path):
    molecule = parse_fchk(ROOT/'examples/water/water.fchk').molecule
    grid = fixture_grid()
    expected = format_cube(grid, molecule)
    with patch('openwfn.exporters.cube.format_cube', side_effect=AssertionError('full text allocation')):
        write_cube(grid, molecule, tmp_path/'density.cube')
    assert (tmp_path/'density.cube').read_text() == expected


def test_failed_export_preserves_previous_target(tmp_path):
    molecule = parse_fchk(ROOT/'examples/water/water.fchk').molecule
    target = tmp_path/'density.cube'
    target.write_text('previous valid data')
    with patch('openwfn.exporters.cube.effective_nuclear_charge', side_effect=ValueError('invalid charge')):
        with pytest.raises(ValueError, match='invalid charge'):
            write_cube(fixture_grid(), molecule, target, overwrite=True)
    assert target.read_text() == 'previous valid data'
    assert list(tmp_path.iterdir()) == [target]
