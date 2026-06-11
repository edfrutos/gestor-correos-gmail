import json
from io import BytesIO

import pytest

import ai_client
from validators import ApiError


def test_ai_status_is_disabled_without_configuration(monkeypatch):
    monkeypatch.delenv('AI_BASE_URL', raising=False)
    monkeypatch.delenv('AI_MODEL', raising=False)

    assert ai_client.ai_status() == {'configured': False, 'model': None, 'remote': False}


def test_summarize_requires_configuration(monkeypatch):
    monkeypatch.delenv('AI_BASE_URL', raising=False)
    monkeypatch.delenv('AI_MODEL', raising=False)

    with pytest.raises(ApiError) as exc:
        ai_client.summarize('Informe')

    assert exc.value.status == 503


def test_summarize_calls_openai_compatible_endpoint(monkeypatch):
    captured = {}

    class Response(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    def fake_urlopen(request, timeout):
        captured['url'] = request.full_url
        captured['headers'] = dict(request.header_items())
        captured['payload'] = json.loads(request.data.decode('utf-8'))
        captured['timeout'] = timeout
        return Response(json.dumps({
            'choices': [{'message': {'content': '  Riesgo principal: SSL  '}}],
        }).encode('utf-8'))

    monkeypatch.setenv('AI_BASE_URL', 'http://localhost:11434/v1')
    monkeypatch.setenv('AI_MODEL', 'local-model')
    monkeypatch.setenv('AI_API_KEY', 'secret')
    monkeypatch.setattr(ai_client, 'urlopen', fake_urlopen)

    result = ai_client.summarize('Informe operativo')

    assert result == {'summary': 'Riesgo principal: SSL', 'model': 'local-model'}
    assert captured['url'] == 'http://localhost:11434/v1/chat/completions'
    assert captured['payload']['model'] == 'local-model'
    assert captured['headers']['Authorization'] == 'Bearer secret'
    assert captured['timeout'] == 60
