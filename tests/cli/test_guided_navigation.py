from pathlib import Path

from openwfn import interactive

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / 'examples/water/water.fchk'


def test_back_returns_to_category_and_home_returns_to_file_menu(monkeypatch, capsys):
    workflows = iter(['orbitals', 'exit'])
    navigation = iter(['back', 'home'])
    answers = iter(['frontier', 'alpha', 'dos', 'all'])
    monkeypatch.setattr(interactive, 'prompt_workflow', lambda _: next(workflows))
    monkeypatch.setattr(interactive, 'prompt_page_navigation', lambda _: next(navigation))
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    interactive.run_interactive(None, WATER)
    text = capsys.readouterr().out
    assert 'Homo' in text
    assert 'entries (use' in text
    assert 'Exiting openWFN.' in text


def test_eof_during_parameters_exits_instead_of_repeating(monkeypatch, capsys):
    workflows = iter(['density'])
    monkeypatch.setattr(interactive, 'prompt_workflow', lambda _: next(workflows))
    def end_input(_):
        raise EOFError
    monkeypatch.setattr('builtins.input', end_input)
    interactive.run_interactive(None, WATER)
    assert 'Exiting openWFN.' in capsys.readouterr().out
