"""Checked-in actual SCF inputs, hashes, invariants and visualization routing."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from openwfn.analysis.orbitals import evaluate_orbital
from openwfn.api import load
from openwfn.cli import main
from openwfn.workbench.payload import WorkbenchPayload

ROOT = Path(__file__).resolve().parents[2]
REPORT = json.loads((ROOT/'validation/everyday-qc/pyscf-report.json').read_text())


@pytest.mark.parametrize('case', REPORT['cases'], ids=[case['case'] for case in REPORT['cases']])
def test_checked_in_wavefunction(case):
    pytest.importorskip('iodata')
    source = ROOT/f"examples/everyday-qc/{case['case']}.molden"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == case['input_sha256']
    calc = load(source)
    assert calc.molecule.charge == case['charge']
    assert calc.molecule.multiplicity == case['spin']+1
    matrix = np.array(calc.mayer().data['bond_order_matrix'])
    assert matrix == pytest.approx(np.array(case['reference_mayer_matrix']), abs=2e-7)
    for method in ('mulliken', 'lowdin'):
        result = calc.pdos(group_by='atom', method=method)
        assert result.status == 'success', result.warnings
        assert result.data['projection_sum_max_error'] < 1e-10
    assert calc.orbital_composition().validation_status == 'Validated'


@pytest.mark.parametrize('name', ['water', 'oh_diffuse_uhf'])
def test_real_workbench_serializes_shared_homo_field(name):
    pytest.importorskip('iodata')
    data = load(ROOT/f'examples/everyday-qc/{name}.molden').data.calculation
    payload = WorkbenchPayload.from_calculation(data, include_fields=True)
    field = next(field for field in payload.fields if field['id'] == 'orbital-homo')
    lines = field['cube'].splitlines()
    origin = np.array([float(v) for v in lines[2].split()[1:]])
    axes = np.array([[float(v) for v in line.split()[1:]] for line in lines[3:6]])
    shape = tuple(int(line.split()[0]) for line in lines[3:6])
    points = origin + np.indices(shape).reshape(3, -1).T @ axes
    index = payload.properties['frontier']['homo_number']-1
    values = np.fromstring(' '.join(lines[6+len(data.molecule.atoms):]), sep=' ')
    reference = evaluate_orbital(data.molecule, data.basis, data.alpha_orbitals, index, points)
    assert values == pytest.approx(reference, abs=5e-6)
    density = next(field for field in payload.fields if field['id'] == 'density-total')
    assert density['status'] == 'partial'
    assert density['warnings']


@pytest.mark.parametrize('name', ['oxygen_triplet', 'ammonium_cation'])
@pytest.mark.parametrize('analysis', ['mayer', 'dos', 'pdos', 'orbital-composition'])
def test_real_charged_open_shell_cli_api_parity(name, analysis, capsys):
    pytest.importorskip('iodata')
    source = ROOT/f'examples/everyday-qc/{name}.molden'
    expected = load(source).analyze(analysis)
    command = ['bondorder', 'mayer'] if analysis == 'mayer' else ['orbitals', 'composition' if analysis == 'orbital-composition' else analysis]
    assert main(['--format', 'json', str(source), *command]) == 0
    actual = json.loads(capsys.readouterr().out)
    assert actual['data'] == expected.data
    assert actual['provenance']['input_sha256'] == expected.provenance['input_sha256']


@pytest.mark.parametrize('case', REPORT['cases'], ids=[case['case'] for case in REPORT['cases']])
def test_checked_in_electronic_coulomb_reference(case):
    """The committed input produces the independent reference, not just fresh SCF."""
    pytest.importorskip('iodata')
    from openwfn.constants import BOHR_TO_ANGSTROM

    calc = load(ROOT/f"examples/everyday-qc/{case['case']}.molden")
    for point, expected in zip(case['reference_esp_points_bohr'], case['reference_electronic_esp'], strict=True):
        coordinates = tuple(value*BOHR_TO_ANGSTROM for value in point)
        result = calc.esp(coordinates, component='electronic')
        assert result.status == 'success', result.warnings
        assert result.validation_status == 'Validated'
        assert result.data['value'] == pytest.approx(expected, abs=1e-8)
        assert result.data['quadrature_passed']
        assert result.data['electron_conservation_error'] < 1e-6
