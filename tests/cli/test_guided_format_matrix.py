import json
from pathlib import Path

import pytest

from openwfn.cli import main
from openwfn.guided import build_guided_session, build_overview

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(('relative', 'suffix'), [
    ('examples/water/water.fchk', '.fchk'),
    ('examples/water/water.fchk', '.fch'),
    ('tests/fixtures/interop/molden/water.molden', '.molden'),
    ('tests/fixtures/interop/molden/water.molden', '.molden.input'),
    ('tests/fixtures/interop/wfn/water.wfn', '.wfn'),
    ('tests/fixtures/interop/wfx/water.wfx', '.wfx'),
    ('tests/fixtures/interop/mwfn/water.mwfn', '.mwfn'),
    ('tests/fixtures/interop/molekel/water.mkl', '.mkl'),
    ('tests/fixtures/interop/cube/water.cube', '.cube'),
    ('tests/fixtures/interop/cube/water.cube', '.cub'),
    ('tests/fixtures/interop/pdb/water.pdb', '.pdb'),
    ('tests/fixtures/interop/sdf/water.sdf', '.sdf'),
    ('tests/fixtures/interop/sdf/water.sdf', '.mol'),
])
def test_bounded_overview_format_matrix(relative, suffix, tmp_path):
    path = tmp_path / ('water β' + suffix)
    path.write_bytes((ROOT / relative).read_bytes())
    result = build_overview(build_guided_session(path))
    assert result.status in {'success', 'partial'}
    assert result.data['results']['summary']['status'] != 'failed'
    assert len(result.provenance['input_sha256']) == 64
    assert not (tmp_path / 'results').exists()


def test_orca_overview_contains_reported_properties(capsys):
    import iodata
    path = Path(iodata.__file__).parent / 'test/data/orca_gradient.out'
    assert main(['--format', 'json', str(path), 'analyze']) == 0
    result = json.loads(capsys.readouterr().out)
    properties = result['data']['results']['properties']['data']
    assert properties['atom_count'] == 32
    assert properties['charge'] == 0
    assert properties['multiplicity'] == 1
    assert properties['normal_termination'] is True
    assert abs(properties['scf_energy_hartree'] - (-742.985592886484)) < 1e-8
    assert properties['dipole_debye'] == pytest.approx([1.0851223, 6.3264572, 1.93165088], abs=1e-6)


def test_stored_grid_integral_has_no_invented_electron_target():
    from openwfn.guided import inspect_stored_grid
    from openwfn.model import VolumetricGrid
    grid = VolumetricGrid(origin=(0., 0., 0.), axes=((1., 0., 0.), (0., 2., 0.), (0., 0., 3.)),
                          shape=(2, 1, 1), values=(2., 3.), value_unit='unknown')
    result = inspect_stored_grid(grid)
    assert result.data['mathematical_integral'] == pytest.approx(30.)
    assert result.data['field_identity'] == 'unverified scalar field'
    assert 'electron_count' not in result.data
    assert 'expected_electrons' not in result.data
    assert result.units['mathematical_integral'] == 'unknown * angstrom^3'


def test_qchem_reported_energy_matches_source(capsys):
    import iodata
    path = Path(iodata.__file__).parent / 'test/data/water_hf_ccpvtz_freq_qchem.out'
    assert main(['--format', 'json', str(path), 'properties']) == 0
    record = json.loads(capsys.readouterr().out)
    assert record['data']['scf_energy_hartree'] == pytest.approx(-76.0571936393, abs=1e-8)
    assert record['data']['atom_count'] == 3
    assert record['data']['charge'] == 0
    assert record['data']['multiplicity'] == 1


def test_incomplete_output_keeps_readable_overview(tmp_path, capsys):
    path = tmp_path / 'incomplete.log'
    path.write_text('# RHF/3-21G\nSCF Done: E(RHF) = -7.5\nNormal termination of Gaussian\n')
    assert main(['--format', 'json', str(path), 'analyze']) == 0
    record = json.loads(capsys.readouterr().out)
    assert record['kind'] == 'overview'
    assert record['status'] == 'partial'
    assert record['data']['results']['summary']['data']['energy_hartree'] == -7.5
