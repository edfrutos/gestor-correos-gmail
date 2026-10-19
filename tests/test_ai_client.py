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


@pytest.mark.parametrize('text,expected', [
    ('<think>\nrazono…\n</think>\n\nhola', 'hola'),
    ('<THINK>a</THINK>[{"label": "x"}]', '[{"label": "x"}]'),
    ('razonamiento sin apertura</think>\nresultado', 'resultado'),
    ('  sin razonamiento  ', 'sin razonamiento'),
])
def test_strip_reasoning(text, expected):
    assert ai_client.strip_reasoning(text) == expected


@pytest.mark.parametrize('base_url,model,remote', [
    ('http://localhost:11434/v1', 'qwen3:8b', False),
    ('http://localhost:11434/v1', 'kimi-k2.5:cloud', True),
    ('http://localhost:11434/v1', 'gpt-oss:20b-cloud', True),
    ('http://127.0.0.1:11434/v1', 'qwen3-coder:480b-cloud', True),
    ('http://localhost:11434/v1', 'cloudy-model:latest', False),
    ('https://api.openai.com/v1', 'gpt-4o-mini', True),
    ('', 'kimi-k2.5:cloud', False),
])
def test_is_remote_flags_ollama_cloud_models(base_url, model, remote):
    assert ai_client.is_remote(base_url, model) is remote


def _fake_completion(monkeypatch, content):
    class Response(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    monkeypatch.setenv('AI_BASE_URL', 'http://localhost:11434/v1')
    monkeypatch.setenv('AI_MODEL', 'qwen3:8b')
    monkeypatch.setattr(ai_client, 'urlopen', lambda request, timeout: Response(json.dumps({
        'choices': [{'message': {'content': content}}],
    }).encode('utf-8')))


def test_summarize_drops_think_block(monkeypatch):
    _fake_completion(monkeypatch, '<think>pienso</think>\nRiesgo: SSL')

    assert ai_client.summarize('Informe')['summary'] == 'Riesgo: SSL'


def test_suggest_rules_parses_json_after_think_block(monkeypatch):
    _fake_completion(monkeypatch, '<think>analizo patrones</think>\n```json\n[{"label": "Plesk"}]\n```')

    result = ai_client.suggest_rules([{'from': 'a@plesk.com', 'sub': 'SSL'}])

    assert result['suggestions'] == [{'label': 'Plesk'}]
