import importlib
import importlib.util
from pathlib import Path

import httpx

from openwfn.assistant_model import LocalModel

SOURCE = Path(__file__).resolve().parents[1] / 'src/openwfn/example_data/everyday-qc/ethanol.molden'


def conversation():
    assert importlib.util.find_spec('openwfn.assistant_conversation'), 'Conversation controller missing'
    return importlib.import_module('openwfn.assistant_conversation')


def test_no_file_chat_generates_labelled_explanation_not_record():
    backend = LocalModel('test', transport=httpx.MockTransport(lambda _: httpx.Response(200,
        json={'choices': [{'message': {'content': 'A basis set represents orbitals.'}}]})))
    controller = conversation().ConversationSession(model=backend)
    answer = controller.ask('Explain basis sets')
    assert answer.record is None
    assert 'Model explanation' in answer.text
    assert 'No calculation was run' in answer.text
    assert 'basis set' in answer.text


def test_file_direct_query_works_without_model():
    from openwfn.assistant import AssistantSession
    controller = conversation().ConversationSession(file_session=AssistantSession(SOURCE))
    answer = controller.ask('What is the HOMO energy?')
    assert answer.record.status == 'success'
    assert answer.record.data['overall_homo_hartree'] == -0.331537655


def test_no_file_property_request_does_not_invent_values():
    controller = conversation().ConversationSession()
    answer = controller.ask('What is my HOMO energy?')
    assert answer.record is None
    assert 'file' in answer.text.lower()


def test_close_and_clear_keep_labelled_scientific_record():
    from openwfn.assistant import AssistantSession
    controller = conversation().ConversationSession(file_session=AssistantSession(SOURCE))
    result = controller.ask('charge?').record
    controller.close_file()
    controller.clear_context()
    assert controller.file_session is None
    assert controller.last_record is result
    assert result.provenance['input_sha256']


def test_failed_open_keeps_selected_file(tmp_path):
    import pytest

    from openwfn.assistant import AssistantSession
    controller = conversation().ConversationSession(file_session=AssistantSession(SOURCE))
    with pytest.raises((ValueError, OSError)):
        controller.open_file(tmp_path / 'missing.fchk')
    assert controller.file_session.source == SOURCE.resolve()


def test_how_many_electrons_is_not_a_general_explanation():
    from openwfn.assistant import AssistantSession
    backend = LocalModel('test', transport=httpx.MockTransport(lambda request: httpx.Response(200,
        json={'choices': [{'message': {'content': '{"action":"analysis","analysis":"summary"}'}}]})))
    controller = conversation().ConversationSession(file_session=AssistantSession(SOURCE), model=backend)
    answer = controller.ask('How many electrons?')
    assert answer.record is not None
    assert answer.record.status == 'success'


def test_no_colour_chat_scopes_picker_styles(monkeypatch):
    from openwfn import assistant_terminal
    from openwfn.presentation import CommandContext
    from openwfn.utils import color_enabled
    observed = []
    monkeypatch.setattr(assistant_terminal, 'run_chat', lambda *args, **kwargs: observed.append(color_enabled()) or 0)
    monkeypatch.setattr('sys.stdin.isatty', lambda: True)
    monkeypatch.setattr('sys.stdout.isatty', lambda: True)
    monkeypatch.delenv('NO_COLOR', raising=False)
    assert assistant_terminal.chat_command(context=CommandContext(color=False)) == 0
    assert observed == [False]
