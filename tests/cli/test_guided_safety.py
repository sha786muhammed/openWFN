from pathlib import Path

from openwfn import interactive

ROOT = Path(__file__).resolve().parents[2]


def test_xyz_menu_preserves_unknown_state(tmp_path, monkeypatch, capsys):
    source = tmp_path / 'water.xyz'
    source.write_text('3\nwater\nO 0 0 0\nH 0 0 1\nH 0 1 0\n')
    choices = []
    def select(workflows):
        choices.extend(workflow.command for workflow in workflows)
        return 'exit'
    monkeypatch.setattr(interactive, 'prompt_workflow', select)
    interactive.run_interactive(None, source)
    output = capsys.readouterr().out
    assert 'charge unknown' in output
    assert 'multiplicity unknown' in output
    assert 'density' not in choices
    assert 'orbitals' not in choices
    assert 'Ready' not in output


def test_density_settings_forwarded(monkeypatch):
    from openwfn.api import OpenWFNCalculation
    workflows = iter(['density', 'exit'])
    answers = iter(['integrate', 'total', '0.3', '5'])
    captured = []
    monkeypatch.setattr(interactive, 'prompt_workflow', lambda _: next(workflows))
    monkeypatch.setattr(interactive, 'prompt_page_navigation', lambda _: 'back')
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    monkeypatch.setattr(OpenWFNCalculation, 'density', lambda self, kind, **settings:
                        captured.append((kind, settings)) or self.analyze('summary'))
    interactive.run_interactive(None, ROOT / 'examples/water/water.fchk')
    assert captured == [('total', {'spacing_bohr': .3, 'padding_bohr': 5.})]


def test_enum_rejects_terminal_escape(monkeypatch, capsys):
    answers = iter(['total\x1b[3~', 'spin'])
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    assert interactive.prompt_choice('Density', ('total', 'spin'), 'total') == 'spin'
    assert 'Choose' in capsys.readouterr().out


def test_output_path_adds_extension_and_requires_confirmation(tmp_path, monkeypatch):
    from openwfn.guided import build_guided_session
    session = build_guided_session(ROOT / 'examples/water/water.fchk')
    answers = iter([str(tmp_path / 'report'), 'no'])
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    assert interactive.confirm_output_path(session, 'report', '.html') is None
    assert not (tmp_path / 'report.html').exists()


def test_output_path_never_replaces_input(tmp_path, monkeypatch):
    from openwfn.guided import build_guided_session
    path = tmp_path / 'water.xyz'
    path.write_text('1\natom\nH 0 0 0\n')
    session = build_guided_session(path)
    answers = iter([str(path), 'back'])
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    assert interactive.confirm_output_path(session, 'structure', '.xyz') is None
    assert path.read_text() == '1\natom\nH 0 0 0\n'


def test_density_preflight_does_not_allocate_points(monkeypatch):
    import numpy as np

    from openwfn import load
    from openwfn.analysis.grids import molecular_grid_layout
    molecule = load(ROOT / 'examples/water/water.fchk').molecule
    def blocked(*args, **kwargs):
        raise AssertionError('point allocation during preflight')
    monkeypatch.setattr(np, 'empty', blocked)
    _, shape = molecular_grid_layout(molecule, spacing_bohr=.3, padding_bohr=5)
    assert len(shape) == 3
    assert all(size > 0 for size in shape)
