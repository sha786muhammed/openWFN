import json
from pathlib import Path

import httpx

from openwfn.cli import main

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / 'examples/water/water.fchk'


def test_chat_without_model_explains_setup_and_does_not_install(monkeypatch, capsys):
    monkeypatch.delenv('OPENWFN_CHAT_MODEL', raising=False)
    assert main([str(WATER), 'chat', '--question', 'charge?']) == 2
    text = capsys.readouterr().err
    assert 'OPENWFN_CHAT_MODEL' in text
    assert 'guided' in text.lower()


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
