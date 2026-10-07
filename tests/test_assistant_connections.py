import importlib
import importlib.util
import json

import httpx
import pytest

from openwfn.assistant_model import LocalModel


def connections():
    assert importlib.util.find_spec('openwfn.assistant_connections'), 'Connection manager missing'
    return importlib.import_module('openwfn.assistant_connections')


def test_discovery_uses_models_endpoint_and_keeps_ids():
    def reply(request):
        assert request.method == 'GET'
        assert request.url.path == '/v1/models'
        return httpx.Response(200, json={'data': [{'id': 'qwen3:8b'}, {'id': 'other'}]})
    model = LocalModel('qwen3:8b', transport=httpx.MockTransport(reply))
    assert connections().discover_models(model) == ['qwen3:8b', 'other']


def test_failed_switch_keeps_old_connection():
    manager = connections().ModelConnection(LocalModel('old'))
    candidate = LocalModel('missing', transport=httpx.MockTransport(lambda _: httpx.Response(200, json={'data': []})))
    with pytest.raises(ValueError, match='available'):
        manager.connect(candidate)
    assert manager.active.model == 'old'
    manager.disconnect()
    assert manager.active is None


@pytest.mark.parametrize('response', [httpx.Response(302), httpx.Response(200, json={'data': 'bad'}),
                                    httpx.Response(200, content='x' * 70000)])
def test_discovery_rejects_invalid_or_oversized_responses(response):
    candidate = LocalModel('test', transport=httpx.MockTransport(lambda _: response))
    with pytest.raises((ValueError, RuntimeError)):
        connections().discover_models(candidate)


def test_general_reply_is_separate_from_tool_plan():
    def reply(request):
        body = json.loads(request.content)
        assert 'response_format' not in body
        assert body['max_tokens'] <= 2048
        assert 'file-specific' in body['messages'][0]['content']
        return httpx.Response(200, json={'choices': [{'message': {'content': 'Correlation describes motion beyond mean field.'}}]})
    backend = LocalModel('test', transport=httpx.MockTransport(reply))
    assert hasattr(backend, 'explain'), 'Conceptual conversation missing'
    assert backend.explain('Explain correlation', []) == 'Correlation describes motion beyond mean field.'


def test_explanation_history_is_bounded():
    model = LocalModel('test')
    assert hasattr(model, 'explain'), 'Conceptual conversation missing'
    with pytest.raises(ValueError, match='context|history'):
        model.explain('Explain correlation', [{'role': 'user', 'content': 'x' * 40000}])


def test_server_model_identifiers_cannot_inject_terminal_controls():
    candidate = LocalModel('test', transport=httpx.MockTransport(lambda _: httpx.Response(200,
        json={'data': [{'id': '\x1b[2Jdanger'}]})))
    with pytest.raises(ValueError):
        connections().discover_models(candidate)


def test_model_name_rejects_control_characters():
    with pytest.raises(ValueError):
        LocalModel('model\nsecret')
