import json
import stat

import pytest

import ai_client
import server
import settings
from validators import ApiError
from test_server_api import DummyHandler, ExistingPath, request_body, response_json


def test_defaults_without_file():
    assert settings.load_settings() == settings.DEFAULT_SETTINGS
    assert settings.public_settings()['ai_source'] is None


def test_save_persists_with_private_permissions():
    settings.save_settings({'ai_base_url': 'https://api.openai.com/v1', 'ai_model': 'gpt-4o-mini', 'ai_api_key': 'sk-x'})

    mode = stat.S_IMODE(settings.SETTINGS_FILE.stat().st_mode)
    assert mode == 0o600
    assert json.loads(settings.SETTINGS_FILE.read_text())['ai_api_key'] == 'sk-x'


def test_public_settings_never_exposes_key():
    settings.save_settings({'ai_base_url': 'http://localhost:11434/v1', 'ai_model': 'llama3', 'ai_api_key': 'secret'})

    public = settings.public_settings()
    assert 'secret' not in json.dumps(public)
    assert public['ai_api_key_set'] is True
    assert public['ai_source'] == 'app'


def test_empty_key_keeps_saved_one_and_clear_removes_it():
    settings.save_settings({'ai_api_key': 'secret'})
    settings.save_settings({'ai_model': 'otro', 'ai_api_key': ''})
    assert settings.load_settings()['ai_api_key'] == 'secret'

    settings.save_settings({'ai_api_key_clear': True})
    assert settings.load_settings()['ai_api_key'] == ''


@pytest.mark.parametrize('url', ['ftp://x', 'api.openai.com', 'https://api.openai.com/v1/chat/completions'])
def test_rejects_invalid_base_url(url):
    with pytest.raises(ApiError):
        settings.save_settings({'ai_base_url': url})


def test_app_settings_override_env(monkeypatch):
    monkeypatch.setenv('AI_BASE_URL', 'http://env/v1')
    monkeypatch.setenv('AI_MODEL', 'env-model')
    monkeypatch.setenv('AI_API_KEY', 'env-key')
    assert settings.ai_config() == ('http://env/v1', 'env-model', 'env-key')
    assert settings.ai_source() == 'env'

    settings.save_settings({'ai_base_url': 'https://app/v1', 'ai_model': 'app-model'})
    # Sin clave en la app se usa la del entorno.
    assert settings.ai_config() == ('https://app/v1', 'app-model', 'env-key')
    assert ai_client.ai_status()['model'] == 'app-model'
    assert settings.ai_source() == 'app'


def test_backup_dir_must_exist_and_be_absolute(tmp_path):
    with pytest.raises(ApiError):
        settings.save_settings({'backup_dir': 'relativo/carpeta'})
    with pytest.raises(ApiError):
        settings.save_settings({'backup_dir': str(tmp_path / 'no-existe')})

    settings.save_settings({'backup_dir': str(tmp_path)})
    assert settings.load_settings()['backup_dir'] == str(tmp_path.resolve())
    settings.save_settings({'backup_dir': ''})
    assert settings.load_settings()['backup_dir'] == ''


def test_post_settings_endpoint_returns_public_view():
    handler = DummyHandler(request_body({'ai_base_url': 'http://localhost:11434/v1', 'ai_model': 'llama3', 'ai_api_key': 'k'}))

    handler.handle_post_settings()

    assert handler.status_sent == 200
    body = response_json(handler)
    assert body['settings']['ai_api_key_set'] is True
    assert 'ai_api_key' not in body['settings']
    assert body['ai']['configured'] is True


def test_post_settings_endpoint_rejects_bad_backup_dir(tmp_path):
    handler = DummyHandler(request_body({'backup_dir': str(tmp_path / 'nope')}))

    handler.handle_post_settings()

    assert handler.status_sent == 400


def _export(monkeypatch, exports, ids):
    handler = DummyHandler(request_body({'message_ids': ids}))
    monkeypatch.setattr(server, 'GMAIL_OK', True)
    monkeypatch.setattr(server, 'CREDS', ExistingPath())
    monkeypatch.setattr(server, 'gmail', lambda: object())
    monkeypatch.setattr(server, 'get_message_raw', lambda mid: f'EML {mid}'.encode())
    monkeypatch.setattr(server, 'EXPORTS_DIR', exports)
    handler.handle_messages_export()
    assert handler.status_sent == 200
    return response_json(handler)


@pytest.mark.parametrize('ids', [['m1'], ['m1', 'm2']])
def test_export_is_copied_to_backup_dir(monkeypatch, tmp_path, ids):
    exports, backup = tmp_path / 'exports', tmp_path / 'backup'
    exports.mkdir()
    backup.mkdir()
    settings.save_settings({'backup_dir': str(backup)})

    body = _export(monkeypatch, exports, ids)

    assert body['backup'] == str(backup.resolve() / body['file'])
    assert body['backup_error'] is None
    assert (backup / body['file']).read_bytes() == (exports / body['file']).read_bytes()


def test_export_without_backup_dir_reports_none(monkeypatch, tmp_path):
    body = _export(monkeypatch, tmp_path, ['m1'])

    assert body['backup'] is None
    assert body['backup_error'] is None


def test_backup_failure_does_not_break_export(monkeypatch, tmp_path):
    exports, backup = tmp_path / 'exports', tmp_path / 'backup'
    exports.mkdir()
    backup.mkdir()
    settings.save_settings({'backup_dir': str(backup)})
    backup.rmdir()  # la carpeta desaparece (p. ej. disco externo desmontado)

    body = _export(monkeypatch, exports, ['m1'])

    assert (exports / 'm1.eml').exists()
    assert body['backup'] is None
    assert 'respaldo' in body['backup_error']
