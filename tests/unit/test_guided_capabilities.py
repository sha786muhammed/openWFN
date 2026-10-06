from pathlib import Path

import pytest

from openwfn import load

ROOT = Path(__file__).resolve().parents[2]


def test_xyz_does_not_invent_electronic_state(tmp_path):
    path = tmp_path / 'water.xyz'
    path.write_text('3\nwater\nO 0 0 0\nH 0 0 1\nH 1 0 0\n')
    result = load(path).analyze('summary')
    assert result.data['charge'] is None
    assert result.data['multiplicity'] is None
    assert result.data['formula'] == 'H2O'
    geometry = load(path).analyze_geometry()
    assert geometry.data['charge'] is None
    assert geometry.data['multiplicity'] is None


def test_xyz_actions_exclude_missing_wavefunction(tmp_path):
    from openwfn.guided import available_workflows, build_guided_session
    path = tmp_path / 'water.xyz'
    path.write_text('3\nwater\nO 0 0 0\nH 0 0 1\nH 1 0 0\n')
    session = build_guided_session(path)
    commands = {item.command for item in available_workflows(session)}
    assert {'summary', 'geometry', 'export'} <= commands
    assert not {'orbitals', 'population', 'density', 'vibrations', 'workbench', 'report'} & commands


def test_grid_session_does_not_require_molecule():
    from openwfn.guided import available_workflows, build_guided_session
    session = build_guided_session(ROOT / 'tests/fixtures/interop/cube/water.cube')
    assert session.data.calculation is None
    commands = {item.command for item in available_workflows(session)}
    assert 'grid' in commands
    assert 'orbitals' not in commands


def test_molden_actions_and_state():
    pytest.importorskip('iodata')
    from openwfn.guided import available_workflows, build_guided_session
    session = build_guided_session(ROOT / 'tests/fixtures/interop/molden/water.molden')
    commands = {item.command for item in available_workflows(session)}
    assert {'orbitals', 'population', 'density'} <= commands
    assert 'vibrations' not in commands
    assert session.data.structure.charge == 0


def test_source_formal_charge_preserved(tmp_path):
    text = (ROOT / 'tests/fixtures/interop/sdf/water.sdf').read_text()
    path = tmp_path / 'charged.sdf'
    path.write_text(text.replace('M  END', 'M  CHG  1   1   1\nM  END'))
    assert load(path).data.structure.charge == 1


def test_ghost_hirshfeld_is_unavailable_before_computation():
    import iodata

    from openwfn.guided import build_guided_session
    path = Path(iodata.__file__).parent / 'test/data/water_dimer_ghost.fchk'
    session = build_guided_session(path)
    assert session.eligible('hirshfeld') is False
    assert any('ghost' in reason.lower() for reason in session.analyses['hirshfeld']['missing_requirements'])
