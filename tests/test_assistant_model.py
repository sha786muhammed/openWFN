import json

import httpx
import pytest


def test_local_model_adapter_exists():
    import importlib.util
    assert importlib.util.find_spec('openwfn.assistant_model') is not None


def test_model_request_is_bounded_and_contains_no_raw_input():
    from openwfn.assistant_model import LocalModel
    def respond(request):
        payload = json.loads(request.content)
        assert payload['model'] == 'test-local'
        assert payload['stream'] is False
        assert payload['max_tokens'] <= 2048
        assert payload['response_format']['type'] == 'json_schema'
        assert payload['response_format']['json_schema']['schema']['properties']['explanation']['enum'] == ['none']
        assert payload['messages'][-1]['role'] == 'user'
        assert 'charge?' in payload['messages'][-1]['content']
        assert 'filename' not in payload['messages'][0]['content']
        return httpx.Response(200, json={'choices': [{'message': {
            'content': '{"action":"analysis","analysis":"summary"}'}}]})
    backend = LocalModel('test-local', transport=httpx.MockTransport(respond))
    plan = backend.plan('charge?', {'analyses': {'summary': {'available': True}}})
    assert plan.analysis == 'summary'


def test_remote_endpoint_requires_explicit_consent_and_https():
    from openwfn.assistant_model import LocalModel
    with pytest.raises(ValueError, match='permission'):
        LocalModel('test', endpoint='https://example.com/v1')
    with pytest.raises(ValueError, match='HTTPS'):
        LocalModel('test', endpoint='http://example.com/v1', allow_remote=True)
    for endpoint in ('http://user:secret@localhost:11434/v1',
                     'http://localhost:11434/v1?token=secret',
                     'file:///tmp/model'):
        with pytest.raises(ValueError):
            LocalModel('test', endpoint=endpoint)


@pytest.mark.parametrize('response', [
    httpx.Response(302, headers={'Location': 'https://example.com/'}),
    httpx.Response(200, json={'choices': [{'message': {'content': 'The gap is 99 eV'}}]}),
    httpx.Response(200, json={'choices': [{'message': {'content': '{"action":"analysis","analysis":"summary","charge":999}'}}]}),
    httpx.Response(200, content='x' * 100_000),
])
def test_model_failure_and_invented_values_do_not_become_answers(response):
    from openwfn.assistant_model import LocalModel
    backend = LocalModel('test', transport=httpx.MockTransport(lambda _: response))
    with pytest.raises((ValueError, RuntimeError)):
        backend.plan('charge?', {'analyses': {}})


def test_duplicate_json_keys_are_rejected():
    from openwfn.assistant import AnalysisPlan
    with pytest.raises(ValueError, match='Duplicate'):
        AnalysisPlan.from_json('{"action":"analysis","analysis":"summary","analysis":"frontier"}')


def test_model_followup_receives_prior_user_question_as_conversation():
    from openwfn.assistant_model import LocalModel
    def respond(request):
        messages = json.loads(request.content)['messages']
        assert messages[1] == {'role': 'user', 'content': 'Which atoms contribute to HOMO?'}
        assert messages[-1]['content'] == 'Use Lowdin'
        return httpx.Response(200, json={'choices': [{'message': {
            'content': '{"action":"analysis","analysis":"orbital-composition","parameters":{"mo":"homo","method":"lowdin"}}'}}]})
    context = {'analyses': {'orbital-composition': {'parameters': ['mo', 'method']}},
               'previous_question': 'Which atoms contribute to HOMO?'}
    plan = LocalModel('test', transport=httpx.MockTransport(respond)).plan('Use Lowdin', context)
    assert plan.analysis == 'orbital-composition' and plan.parameters['mo'] == 'homo'


def test_model_schema_constrains_spin_method_and_explicit_homo():
    from openwfn.assistant_model import LocalModel
    def respond(request):
        schema = json.loads(request.content)['response_format']['json_schema']['schema']
        fields = schema['properties']['parameters']['properties']
        assert fields['spin']['enum'] == ['alpha', 'beta', 'all', 'restricted', None]
        assert fields['method']['enum'] == ['mulliken', 'lowdin']
        assert fields['mo']['enum'] == ['homo']
        return httpx.Response(200, json={'choices': [{'message': {'content':
            '{"action":"analysis","analysis":"orbital-composition","parameters":{"mo":"homo","spin":"alpha","method":"lowdin"}}'}}]})
    context = {'analyses': {'orbital-composition': {'parameters': ['mo', 'spin', 'method']}}}
    plan = LocalModel('test', transport=httpx.MockTransport(respond)).plan('Which atoms contribute to HOMO?', context)
    assert plan.parameters['mo'] == 'homo'


def test_model_read_timeout_is_not_reported_as_unreachable_server():
    from openwfn.assistant_model import LocalModel
    def timeout(request):
        raise httpx.ReadTimeout('response timed out', request=request)
    with pytest.raises(RuntimeError, match='timed out') as caught:
        LocalModel('test', timeout=2, transport=httpx.MockTransport(timeout)).plan('question', {'analyses': {}})
    assert 'reach' not in str(caught.value)
