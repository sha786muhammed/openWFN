"""Stream conceptual prose without streaming or inventing scientific records."""

import io
import json

import httpx
import pytest

from openwfn.assistant_conversation import ConversationSession
from openwfn.assistant_model import LocalModel


def event(text=None, finish=None):
    delta = {} if text is None else {'content': text}
    return ('data: ' + json.dumps({'choices': [{'delta': delta, 'finish_reason': finish}]}) + '\n\n').encode()


def model_with_stream(chunks):
    class Stream(httpx.SyncByteStream):
        def __iter__(self):
            yield from chunks

    def handle(request):
        payload = json.loads(request.content)
        assert payload['stream'] is True
        return httpx.Response(200, headers={'content-type': 'text/event-stream'}, stream=Stream())
    return LocalModel('test', transport=httpx.MockTransport(handle))


def test_explanation_emits_first_text_before_second_chunk_is_consumed():
    received = []

    def chunks():
        yield event('A basis ')
        assert received == ['A basis '], 'The model response was buffered instead of displayed'
        yield event('represents orbitals.')
        yield event(finish='stop')
        yield b'data: [DONE]\n\n'

    backend = model_with_stream(chunks())
    text = backend.explain('Explain basis sets', [], on_text=received.append)
    assert text == 'A basis represents orbitals.'
    assert received == ['A basis ', 'represents orbitals.']


def test_streamed_conversation_is_labelled_prose_not_a_record():
    backend = model_with_stream([event('A basis represents orbitals.'), event(finish='stop')])
    controller = ConversationSession(model=backend)
    received = []
    answer = controller.ask('Explain basis sets', on_model_text=received.append)
    assert received == ['A basis represents orbitals.']
    assert answer.record is None and controller.last_record is None
    assert 'No calculation was run' in answer.text
    assert 'not independently verified' in answer.text
    assert controller.history[-1]['content'] == 'A basis represents orbitals.'


@pytest.mark.parametrize('end', [None, 'length'])
def test_incomplete_model_stream_is_not_added_to_history(end):
    chunks = [event('Incomplete explanation')]
    if end:
        chunks += [event(finish=end), b'data: [DONE]\n\n']
    controller = ConversationSession(model=model_with_stream(chunks))
    with pytest.raises(ValueError):
        controller.ask('Explain basis sets', on_model_text=lambda text: None)
    assert controller.history == [] and controller.last_record is None


def test_cancelled_stream_does_not_add_history():
    def cancel(text):
        raise KeyboardInterrupt
    controller = ConversationSession(model=model_with_stream([event('Partial prose')]))
    with pytest.raises(KeyboardInterrupt):
        controller.ask('Explain basis sets', on_model_text=cancel)
    assert controller.history == []


@pytest.mark.parametrize('reason', ['length', 'content_filter'])
def test_json_fallback_does_not_emit_or_remember_truncated_explanation(reason):
    backend = LocalModel('test', transport=httpx.MockTransport(lambda request: httpx.Response(200,
        json={'choices': [{'message': {'content': 'A truncated explanation'}, 'finish_reason': reason}]})))
    controller = ConversationSession(model=backend)
    received = []
    with pytest.raises(ValueError, match='incomplete'):
        controller.ask('Explain basis sets', on_model_text=received.append)
    assert received == [] and controller.history == []


def test_normal_long_stream_is_not_rejected_for_protocol_framing():
    chunks = [event('word ')] * 1000 + [event(finish='stop')]
    received = []
    text = model_with_stream(chunks).explain('Explain basis sets', [], on_text=received.append)
    assert len(received) == 1000 and len(text) == 4999


def test_long_stream_can_arrive_in_one_network_chunk():
    data = event('word ') * 1000 + event(finish='stop')
    text = model_with_stream([data]).explain('Explain basis sets', [], on_text=lambda text: None)
    assert len(text) == 4999


@pytest.mark.parametrize('payload', [[], {'choices': ['invalid']}, {'choices': [{'delta': []}]}])
def test_malformed_stream_event_fails_cleanly(payload):
    stream = [('data: ' + json.dumps(payload) + '\n\n').encode()]
    with pytest.raises(ValueError):
        model_with_stream(stream).explain('Explain basis sets', [], on_text=lambda text: None)


def test_terminal_stream_is_labelled_sanitized_and_not_duplicated():
    from openwfn.assistant_terminal import run_chat
    from openwfn.presentation import CommandContext

    backend = model_with_stream([event('A basis\x1b[2J represents orbitals.'), event(finish='stop')])
    output = io.StringIO()
    context = CommandContext(format='plain', output_stream=output, error_stream=io.StringIO())
    assert run_chat(None, backend, question='Explain basis sets', context=context) == 0
    text = output.getvalue()
    assert '\x1b' not in text
    assert text.index('No calculation was run') < text.index('A basis')
    assert text.count('A basis') == 1
    assert 'not independently verified' in text
