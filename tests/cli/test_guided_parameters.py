
from pathlib import Path

from openwfn import interactive
from openwfn.app import CommandContext
from openwfn.presentation import render
from openwfn.results import ResultRecord

ROOT = Path(__file__).resolve().parents[2]


def test_human_missing_values_never_have_fake_units():
    result = ResultRecord(kind='summary', data={'energy_hartree': None}, units={'energy_hartree': 'hartree'})
    text = render(result, CommandContext(format='plain'))
    assert 'Unavailable' in text
    assert 'None hartree' not in text


def test_missing_formchk_is_recoverable(tmp_path, monkeypatch, capsys):
    path = tmp_path / 'input.chk'
    path.write_bytes(b'binary checkpoint')
    monkeypatch.setattr('shutil.which', lambda _: None)
    assert interactive.run_interactive(None, path) == 2
    assert 'formchk' in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == [path]


def test_density_cube_uses_explicit_settings_and_final_destination(tmp_path, monkeypatch, capsys):
    from openwfn.parsers.gaussian.cube import parse_cube
    workflows = iter(['density', 'exit'])
    answers = iter(['cube', 'total', '.4', '4', str(tmp_path / 'density'), 'yes'])
    monkeypatch.setattr(interactive, 'prompt_workflow', lambda _: next(workflows))
    monkeypatch.setattr(interactive, 'prompt_page_navigation', lambda _: 'home')
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    interactive.run_interactive(None, ROOT / 'examples/water/water.fchk')
    grid = parse_cube(tmp_path / 'density.cube')
    assert len(grid.values) > 0
    assert '.openwfn-export-' not in capsys.readouterr().out


def test_geometry_reprompts_before_dispatch_for_out_of_range_atom(monkeypatch):
    answers = iter(['0', '4', '2', '3'])
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    assert interactive.prompt_indices(('i', 'j'), atom_count=3) == [2, 3]


def test_plain_terminal_context_has_no_color_sequences(capsys):
    from openwfn import utils
    with utils.terminal_color(False):
        utils.print_header('Header')
        utils.print_warning('Warning')
        print(utils.highlight('Label'))
    assert '\x1b[' not in capsys.readouterr().out


def test_consistency_check_does_not_offer_unrelated_esp_operation(monkeypatch, capsys):
    workflows = iter(['validate', 'exit'])
    answers = iter(['.3', '5'])
    monkeypatch.setattr(interactive, 'prompt_workflow', lambda _: next(workflows))
    monkeypatch.setattr(interactive, 'prompt_page_navigation', lambda _: 'home')
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    interactive.run_interactive(None, ROOT / 'examples/water/water.fchk')
    assert 'Electron Count' in capsys.readouterr().out
