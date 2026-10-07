"""The shared welcome mark belongs only to interactive entrypoints."""

from pathlib import Path

from openwfn.assistant import AssistantSession
from openwfn.assistant_model import LocalModel
from openwfn.assistant_terminal import run_chat
from openwfn.presentation import CommandContext

ROOT = Path(__file__).resolve().parents[2]


def test_chat_welcome_uses_shared_wordmark(monkeypatch, capsys):
    monkeypatch.setattr('builtins.input', lambda _: '/quit')
    session = AssistantSession(ROOT / 'src/openwfn/example_data/everyday-qc/ethanol.molden')
    assert run_chat(session, LocalModel('test-model')) == 0
    output = capsys.readouterr().out
    assert 'Wavefunction analysis toolkit' in output
    assert 'Scientific Assistant' in output
    assert '▄▀▀▄' in output or 'openWFN' in output


def test_guided_welcome_uses_shared_wordmark_once(monkeypatch, capsys):
    from openwfn import interactive

    monkeypatch.setattr(interactive, 'prompt_workflow', lambda _: 'q')
    assert interactive.run_interactive(None, ROOT / 'src/openwfn/example_data/everyday-qc/ethanol.molden') in {None, 0}
    output = capsys.readouterr().out
    assert output.count('Wavefunction analysis toolkit') == 1


def test_chat_banner_honours_no_color_environment_in_a_terminal(monkeypatch, capsys):
    monkeypatch.setenv('NO_COLOR', '1')
    monkeypatch.setenv('TERM', 'xterm-256color')
    monkeypatch.setattr('sys.stdout.isatty', lambda: True)
    monkeypatch.setattr('builtins.input', lambda _: '/quit')
    assert run_chat(None, None, context=CommandContext(format='table', color=True)) == 0
    assert '\x1b[' not in capsys.readouterr().out
