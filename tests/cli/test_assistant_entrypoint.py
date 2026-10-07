import json
from pathlib import Path

import httpx

from openwfn.cli import main

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / 'examples/water/water.fchk'


def test_chat_direct_property_without_model_runs_engine(monkeypatch, capsys):
    monkeypatch.delenv('OPENWFN_CHAT_MODEL', raising=False)
    assert main([str(WATER), 'chat', '--question', 'charge?']) == 0
    assert 'Charge' in capsys.readouterr().out


def test_chat_json_is_only_an_engine_record(monkeypatch, capsys):
    from openwfn.assistant_model import LocalModel
    backend = LocalModel('test', transport=httpx.MockTransport(lambda _: httpx.Response(200,
        json={'choices': [{'message': {'content': '{"action":"analysis","analysis":"frontier"}'}}]})))
    monkeypatch.setattr('openwfn.assistant_terminal.configured_model', lambda **_: backend)
    assert main(['--format', 'json', str(WATER), 'chat', '--model', 'test',
                 '--question', 'What is the gap?']) == 0
    record = json.loads(capsys.readouterr().out)
    assert record['kind'] == 'frontier_orbitals'
    assert record['units']['gap_ev'] == 'eV'
    assert len(record['provenance']['input_sha256']) == 64


def test_chat_eof_exits_without_outputs(monkeypatch, tmp_path, capsys):
    from openwfn.assistant import AssistantSession
    from openwfn.assistant_model import LocalModel
    from openwfn.assistant_terminal import run_chat
    backend = LocalModel('test')
    monkeypatch.chdir(tmp_path)
    def eof(_):
        raise EOFError
    monkeypatch.setattr('builtins.input', eof)
    assert run_chat(AssistantSession(WATER), backend) == 0
    assert not list(tmp_path.iterdir())
    assert 'Assistant' in capsys.readouterr().out


def test_cli_chat_rejects_unattended_density_without_confirmation(monkeypatch, capsys):
    from openwfn.assistant_model import LocalModel
    backend = LocalModel('test', transport=httpx.MockTransport(lambda _: httpx.Response(200,
        json={'choices': [{'message': {'content': '{"action":"analysis","analysis":"density"}'}}]})))
    monkeypatch.setattr('openwfn.assistant_terminal.configured_model', lambda **_: backend)
    assert main(['--format', 'json', str(WATER), 'chat', '--model', 'test',
                 '--question', 'Check density']) == 1
    record = json.loads(capsys.readouterr().out)
    assert record['status'] == 'failed'
    assert 'confirm' in record['error']['message'].lower()


def test_chat_output_cannot_replace_the_input_even_with_overwrite(tmp_path, monkeypatch, capsys):
    from openwfn.assistant_model import LocalModel
    source = tmp_path / 'water.fchk'
    original = WATER.read_bytes()
    source.write_bytes(original)
    backend = LocalModel('test', transport=httpx.MockTransport(lambda _: httpx.Response(200,
        json={'choices': [{'message': {'content': '{"action":"analysis","analysis":"summary"}'}}]})))
    monkeypatch.setattr('openwfn.assistant_terminal.configured_model', lambda **_: backend)
    assert main(['--format', 'json', '--output', str(source), '--overwrite',
                 str(source), 'chat', '--model', 'test', '--question', 'charge?']) != 0
    assert source.read_bytes() == original


def test_chat_malformed_input_exits_cleanly(tmp_path, capsys):
    source = tmp_path / 'bad.fchk'
    source.write_text('not a formatted checkpoint')
    assert main([str(source), 'chat', '--model', 'test', '--question', 'charge?']) != 0
    text = capsys.readouterr().err
    assert text and 'Traceback' not in text


def test_chat_json_setup_failure_is_a_record(monkeypatch, capsys):
    monkeypatch.delenv('OPENWFN_CHAT_MODEL', raising=False)
    assert main(['--format', 'json', str(WATER), 'chat', '--question', 'Inspect another property']) != 0
    assert json.loads(capsys.readouterr().out)['status'] == 'failed'


def test_chat_quiet_single_question_has_no_human_stdout(monkeypatch, capsys):
    from openwfn.assistant_model import LocalModel
    backend = LocalModel('test', transport=httpx.MockTransport(lambda _: httpx.Response(200,
        json={'choices': [{'message': {'content': '{"action":"analysis","analysis":"summary"}'}}]})))
    monkeypatch.setattr('openwfn.assistant_terminal.configured_model', lambda **_: backend)
    assert main(['--quiet', str(WATER), 'chat', '--model', 'test', '--question', 'charge?']) == 0
    assert capsys.readouterr().out == ''


def test_chat_noninteractive_json_does_not_open_a_conversation(monkeypatch, capsys):
    import sys
    monkeypatch.setattr(sys.stdin, 'isatty', lambda: True)
    monkeypatch.setattr(sys.stdout, 'isatty', lambda: True)
    monkeypatch.setattr('builtins.input', lambda _: (_ for _ in ()).throw(AssertionError('prompted')))
    assert main(['--format', 'json', '--non-interactive', str(WATER), 'chat', '--model', 'test']) != 0
    assert json.loads(capsys.readouterr().out)['status'] == 'failed'


def test_chat_fallback_progress_does_not_pollute_json(monkeypatch, capsys):
    from openwfn.assistant_model import LocalModel
    backend = LocalModel('test', transport=httpx.MockTransport(lambda _: httpx.Response(200,
        json={'choices': [{'message': {'content': '{"action":"analysis","analysis":"summary"}'}}]})))
    monkeypatch.setattr('openwfn.assistant_terminal.configured_model', lambda **_: backend)
    assert main(['--format', 'json', str(WATER), 'chat', '--model', 'test',
                 '--question', 'Tell me about this calculation']) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)['status'] == 'success'
    assert 'Waiting for test' in captured.err


def test_file_free_single_question_returns_labelled_model_explanation(monkeypatch, capsys):
    from openwfn.assistant_model import LocalModel
    backend = LocalModel('test', transport=httpx.MockTransport(lambda _: httpx.Response(200,
        json={'choices': [{'message': {'content': 'A basis set represents orbitals.'}}]})))
    monkeypatch.setattr('openwfn.assistant_terminal.configured_model', lambda **_: backend)
    assert main(['chat', '--model', 'test', '--question', 'Explain basis sets']) == 0
    text = capsys.readouterr().out
    assert 'Model explanation' in text and 'No calculation was run' in text


def test_file_free_structured_chat_does_not_fabricate_record(capsys):
    assert main(['--format', 'json', 'chat', '--question', 'Explain basis sets']) != 0
    assert json.loads(capsys.readouterr().out)['status'] == 'failed'


def test_cancelled_chat_returns_to_prompt(monkeypatch, capsys):
    from openwfn.assistant_terminal import run_chat
    answers = iter([KeyboardInterrupt(), '/quit'])
    def prompt(_):
        value = next(answers)
        if isinstance(value, BaseException):
            raise value
        return value
    monkeypatch.setattr('builtins.input', prompt)
    assert run_chat(None, None) == 0
    assert 'Cancelled' in capsys.readouterr().out
