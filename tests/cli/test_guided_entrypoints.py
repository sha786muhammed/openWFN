import json
from pathlib import Path

from openwfn.cli import main

ROOT = Path(__file__).resolve().parents[2]
WATER = str(ROOT / 'examples/water/water.fchk')


def test_analyze_is_bounded_json(monkeypatch, capsys):
    monkeypatch.setattr('builtins.input', lambda _: (_ for _ in ()).throw(AssertionError('unexpected prompt')))
    assert main(['--format', 'json', WATER, 'analyze']) == 0
    data = json.loads(capsys.readouterr().out)
    assert data['kind'] == 'overview'
    assert data['data']['results']['summary']['data']['formula'] == 'H2O'
    assert set(data['data']['results']) == {'summary', 'frontier-all'}


def test_explicit_open_without_terminal_fails_cleanly(monkeypatch, capsys):
    monkeypatch.setattr('sys.stdin.isatty', lambda: False)
    assert main([WATER, 'open']) != 0
    assert 'analyze' in capsys.readouterr().err


def test_no_file_noninteractive_prints_help(monkeypatch, capsys):
    monkeypatch.setattr('sys.stdin.isatty', lambda: False)
    assert main([]) == 2
    assert 'usage:' in capsys.readouterr().out


def test_file_only_json_never_prompts_in_terminal(monkeypatch, capsys):
    monkeypatch.setattr('sys.stdin.isatty', lambda: True)
    monkeypatch.setattr('sys.stdout.isatty', lambda: True)
    monkeypatch.setattr('builtins.input', lambda _: (_ for _ in ()).throw(AssertionError('prompt')))
    assert main(['--format', 'json', WATER]) == 0
    assert json.loads(capsys.readouterr().out)['kind'] == 'overview'


def test_overview_runs_no_expensive_operations(monkeypatch):
    from openwfn.api import OpenWFNCalculation
    from openwfn.guided import build_guided_session, build_overview
    def blocked(*args, **kwargs):
        raise AssertionError('expensive operation')
    monkeypatch.setattr(OpenWFNCalculation, 'density', blocked)
    monkeypatch.setattr(OpenWFNCalculation, 'population', blocked)
    result = build_overview(build_guided_session(Path(WATER)))
    assert result.status == 'success'


def test_no_arguments_prompts_for_file_in_terminal(monkeypatch):
    monkeypatch.setattr('sys.stdin.isatty', lambda: True)
    monkeypatch.setattr('sys.stdout.isatty', lambda: True)
    monkeypatch.setattr('builtins.input', lambda _: WATER)
    opened = []
    monkeypatch.setattr('openwfn.cli.run_interactive',
                        lambda lines, filename, **options: opened.append((filename, options)))
    assert main([]) == 0
    assert opened == [(WATER, {'format_hint': None})]


def test_file_only_explicit_input_format_is_bounded(monkeypatch, capsys):
    monkeypatch.setattr('sys.stdin.isatty', lambda: False)
    assert main(['--input-format', 'fchk', '--format', 'json', WATER]) == 0
    assert json.loads(capsys.readouterr().out)['kind'] == 'overview'
