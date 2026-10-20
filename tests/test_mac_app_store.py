"""Fase 35 — variante Mac App Store (ADR-015)."""

import importlib.util
import json
import plistlib
import sys
import webbrowser
from pathlib import Path

import pytest

import gmail_client
import paths
import server
import updater
from test_server_api import DummyHandler, request_body, response_json

ROOT = Path(__file__).parents[1]
MACOS = ROOT / 'macos'
spec = importlib.util.spec_from_file_location('app_main', MACOS / 'app_main.py')
app_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_main)

CLIENT = {'installed': {'client_id': 'abc.apps.googleusercontent.com', 'client_secret': 's3cr3t',
                        'redirect_uris': ['http://localhost']}}


# --- paths.distribution ---

def test_distribution_is_direct_from_source(monkeypatch):
    monkeypatch.delenv('GESTOR_DISTRIBUTION', raising=False)
    assert paths.distribution() == 'direct'
    assert paths.is_app_store() is False


def test_distribution_reads_bundled_marker(monkeypatch, tmp_path):
    monkeypatch.delenv('GESTOR_DISTRIBUTION', raising=False)
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setenv('RESOURCEPATH', str(tmp_path))
    assert paths.distribution() == 'direct'  # build de Developer ID: sin archivo

    (tmp_path / paths.DISTRIBUTION_FILE).write_text('mas\n', encoding='utf-8')
    assert paths.is_app_store() is True


def test_distribution_env_override(monkeypatch):
    monkeypatch.setenv('GESTOR_DISTRIBUTION', 'MAS')
    assert paths.is_app_store() is True


# --- Sin updater propio en la Mac App Store ---

def test_check_for_update_never_hits_network_in_app_store(monkeypatch):
    monkeypatch.setenv('GESTOR_DISTRIBUTION', 'mas')
    monkeypatch.setattr(updater, 'fetch_manifest', lambda: pytest.fail('no debe consultar GitHub'))

    info = updater.check_for_update()

    assert info['app_store'] is True
    assert info['update_available'] is False
    assert 'App Store' in info['error']


def test_updater_refuses_to_download_or_install_in_app_store(monkeypatch, tmp_path):
    monkeypatch.setenv('GESTOR_DISTRIBUTION', 'mas')
    monkeypatch.setattr(updater, '_http_get', lambda *a, **k: pytest.fail('no debe descargar'))

    with pytest.raises(RuntimeError, match='App Store'):
        updater.download_and_stage('https://example.com/x.zip', '00', workdir=tmp_path)
    with pytest.raises(RuntimeError, match='App Store'):
        updater.install_and_relaunch(tmp_path / 'x.app')


def test_update_install_endpoint_refused_in_app_store(monkeypatch):
    handler = DummyHandler(request_body({}))
    monkeypatch.setattr(server, 'is_app_store', lambda: True)
    monkeypatch.setattr(server, 'is_bundled', lambda: True)
    monkeypatch.setattr(server.updater, 'check_for_update', lambda: pytest.fail('no debe comprobar'))

    handler.handle_update_install()

    assert handler.status_sent == 403


def test_status_reports_distribution(monkeypatch):
    handler = DummyHandler()
    handler.path = '/api/status'
    monkeypatch.setattr(server, 'distribution', lambda: 'mas')
    monkeypatch.setattr(server, 'gmail_status', lambda: {'ok': False})
    monkeypatch.setattr(server, 'ai_status', lambda: {})
    monkeypatch.setattr(server, 'delete_status', lambda: {})

    handler.do_GET()

    assert response_json(handler)['distribution'] == 'mas'


def test_app_store_build_has_no_update_menu_or_sparkle():
    source = (MACOS / 'app_main.py').read_text(encoding='utf-8')
    assert 'sparkle = None if app_store else SparkleUpdater()' in source
    assert 'menu=[] if app_store else _build_menu(' in source


# --- OAuth en el navegador del sistema ---

class RecordingFlow:
    def __init__(self):
        self.kwargs = None

    def run_local_server(self, **kwargs):
        self.kwargs = kwargs
        return 'creds'


def test_oauth_flow_opens_registered_browser_even_headless(monkeypatch):
    monkeypatch.setenv('HEADLESS', '1')
    monkeypatch.setenv('GESTOR_OAUTH_BROWSER', 'gestor-nsworkspace')
    flow = RecordingFlow()

    assert gmail_client.run_oauth_flow(flow) == 'creds'

    assert flow.kwargs == {'port': 0, 'open_browser': True, 'browser': 'gestor-nsworkspace',
                           'timeout_seconds': gmail_client.OAUTH_TIMEOUT_SECONDS}


def test_oauth_flow_headless_server_only_prints_url(monkeypatch):
    monkeypatch.setenv('HEADLESS', '1')
    monkeypatch.delenv('GESTOR_OAUTH_BROWSER', raising=False)
    flow = RecordingFlow()

    gmail_client.run_oauth_flow(flow)

    assert flow.kwargs['open_browser'] is False
    assert flow.kwargs['browser'] is None


def test_destructive_flow_uses_same_oauth_helper():
    source = (ROOT / 'destructive_gmail.py').read_text(encoding='utf-8')
    assert 'run_oauth_flow(flow)' in source
    assert 'run_local_server' not in source


def test_register_oauth_browser_needs_appkit(monkeypatch):
    monkeypatch.setitem(sys.modules, 'AppKit', None)  # import AppKit -> ImportError
    monkeypatch.delenv('GESTOR_OAUTH_BROWSER', raising=False)

    assert app_main.register_oauth_browser() is False
    assert 'GESTOR_OAUTH_BROWSER' not in __import__('os').environ


def test_register_oauth_browser_with_appkit(monkeypatch):
    monkeypatch.setitem(sys.modules, 'AppKit', object())
    monkeypatch.delenv('GESTOR_OAUTH_BROWSER', raising=False)

    assert app_main.register_oauth_browser() is True
    assert isinstance(webbrowser.get(app_main.OAUTH_BROWSER), app_main.WorkspaceBrowser)
    assert __import__('os').environ['GESTOR_OAUTH_BROWSER'] == app_main.OAUTH_BROWSER


# --- Importar credentials.json ---

@pytest.fixture
def creds_paths(tmp_path, monkeypatch):
    creds, token = tmp_path / 'data' / 'credentials.json', tmp_path / 'data' / 'token.json'
    creds.parent.mkdir()
    monkeypatch.setattr(gmail_client, 'CREDS', creds)
    monkeypatch.setattr(gmail_client, 'TOKEN', token)
    monkeypatch.setattr(gmail_client, '_svc', object())
    return creds, token


def test_import_client_secrets_copies_with_private_permissions(tmp_path, creds_paths):
    creds, token = creds_paths
    src = tmp_path / 'descargado.json'
    src.write_text(json.dumps(CLIENT), encoding='utf-8')
    token.write_text(json.dumps({'client_id': 'otro.apps.googleusercontent.com'}), encoding='utf-8')

    assert gmail_client.import_client_secrets(src) == 'abc.apps.googleusercontent.com'

    assert json.loads(creds.read_text(encoding='utf-8')) == CLIENT
    assert creds.stat().st_mode & 0o777 == 0o600
    assert not token.exists()  # token de otro cliente: hay que volver a autorizar
    assert gmail_client._svc is None


def test_import_client_secrets_keeps_token_of_same_client(tmp_path, creds_paths):
    creds, token = creds_paths
    src = tmp_path / 'c.json'
    src.write_text(json.dumps(CLIENT), encoding='utf-8')
    token.write_text(json.dumps({'client_id': CLIENT['installed']['client_id']}), encoding='utf-8')

    gmail_client.import_client_secrets(src)

    assert token.exists()


@pytest.mark.parametrize('content', [
    'no es json',
    json.dumps({'web': CLIENT['installed']}),
    json.dumps({'installed': {'client_id': 'x'}}),
    json.dumps(['installed']),
])
def test_import_client_secrets_rejects_invalid(tmp_path, creds_paths, content):
    creds, _ = creds_paths
    src = tmp_path / 'malo.json'
    src.write_text(content, encoding='utf-8')

    with pytest.raises(ValueError):
        gmail_client.import_client_secrets(src)
    assert not creds.exists()


def test_import_client_secrets_rejects_huge_file(tmp_path, creds_paths):
    src = tmp_path / 'grande.json'
    src.write_bytes(b' ' * (gmail_client.MAX_CLIENT_SECRETS_BYTES + 1))

    with pytest.raises(ValueError, match='grande'):
        gmail_client.import_client_secrets(src)


class FakeDialogWindow:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def create_file_dialog(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.result


def _fake_webview(monkeypatch):
    fake = type(sys)('webview')
    fake.OPEN_DIALOG, fake.FOLDER_DIALOG = 10, 20
    monkeypatch.setitem(sys.modules, 'webview', fake)


def test_js_api_import_credentials(monkeypatch, tmp_path, creds_paths):
    _fake_webview(monkeypatch)
    src = tmp_path / 'c.json'
    src.write_text(json.dumps(CLIENT), encoding='utf-8')
    api = app_main.JsApi()
    api._window = FakeDialogWindow((str(src),))

    assert api.import_credentials() == {'ok': True, 'client_id': 'abc.apps.googleusercontent.com'}
    assert api._window.calls[0] == ((10,), {'file_types': ('JSON (*.json)',)})


def test_js_api_import_credentials_reports_errors_and_cancel(monkeypatch, tmp_path, creds_paths):
    _fake_webview(monkeypatch)
    bad = tmp_path / 'b.json'
    bad.write_text('{}', encoding='utf-8')
    api = app_main.JsApi()

    api._window = FakeDialogWindow(None)
    assert api.import_credentials() == {'ok': False, 'cancelled': True}
    api._window = FakeDialogWindow([str(bad)])
    result = api.import_credentials()
    assert result['ok'] is False and 'installed' in result['error']


def test_gmail_status_tells_app_users_to_import(monkeypatch, creds_paths):
    monkeypatch.setattr(gmail_client, 'GMAIL_OK', True)
    monkeypatch.setattr(gmail_client, 'is_bundled', lambda: True)
    assert 'Importa credentials.json' in gmail_client.gmail_status()['msg']


# --- Cliente OAuth incluido en la build ---

def test_bundled_oauth_client_installed_when_missing(tmp_path):
    res, creds = tmp_path / 'Resources', tmp_path / 'credentials.json'
    res.mkdir()
    (res / app_main.BUNDLED_OAUTH_CLIENT).write_text(json.dumps(CLIENT), encoding='utf-8')

    assert app_main.install_bundled_oauth_client(res, creds) is True
    data = json.loads(creds.read_text(encoding='utf-8'))
    assert data['installed'] == CLIENT['installed'] and data[app_main.BUNDLED_MARK] is True
    assert creds.stat().st_mode & 0o777 == 0o600
    assert app_main.install_bundled_oauth_client(res, creds) is False  # ya al día


def test_bundled_oauth_client_replaces_older_bundled_copy(tmp_path):
    res, creds = tmp_path / 'Resources', tmp_path / 'credentials.json'
    res.mkdir()
    creds.write_text(json.dumps({'installed': {'client_id': 'viejo'}, app_main.BUNDLED_MARK: True}))
    (res / app_main.BUNDLED_OAUTH_CLIENT).write_text(json.dumps(CLIENT), encoding='utf-8')

    assert app_main.install_bundled_oauth_client(res, creds) is True
    assert json.loads(creds.read_text())['installed']['client_id'] == CLIENT['installed']['client_id']


def test_bundled_oauth_client_never_overwrites_user_credentials(tmp_path):
    res, creds = tmp_path / 'Resources', tmp_path / 'credentials.json'
    res.mkdir()
    user = json.dumps({'installed': {'client_id': 'mio', 'client_secret': 'x'}})
    creds.write_text(user)
    (res / app_main.BUNDLED_OAUTH_CLIENT).write_text(json.dumps(CLIENT), encoding='utf-8')

    assert app_main.install_bundled_oauth_client(res, creds) is False
    assert creds.read_text() == user


def test_no_bundled_oauth_client_is_noop(tmp_path):
    assert app_main.install_bundled_oauth_client(tmp_path, tmp_path / 'credentials.json') is False


# --- Carpeta de respaldo: bookmarks con ámbito de seguridad ---

def test_pick_folder_remembers_bookmark_only_with_store(monkeypatch):
    _fake_webview(monkeypatch)
    remembered = []

    class Bookmarks:
        def remember(self, path):
            remembered.append(path)

    api = app_main.JsApi(bookmarks=Bookmarks())
    api._window = FakeDialogWindow(('/Users/yo/Correos',))
    assert api.pick_folder() == '/Users/yo/Correos'
    assert remembered == ['/Users/yo/Correos']

    plain = app_main.JsApi()
    plain._window = FakeDialogWindow(('/x',))
    assert plain.pick_folder() == '/x'


def test_folder_bookmarks_store_tolerates_missing_or_corrupt_file(tmp_path):
    store = tmp_path / 'bookmarks.json'
    bookmarks = app_main.FolderBookmarks(store)
    assert bookmarks._load() == {}
    store.write_text('{roto', encoding='utf-8')
    assert bookmarks._load() == {}
    bookmarks._save({'/a': 'Ym0='})
    assert bookmarks._load() == {'/a': 'Ym0='}
    assert store.stat().st_mode & 0o777 == 0o600


# --- Build ---

def test_mas_entitlements_are_sandboxed_and_match_bundle():
    ent = plistlib.loads((MACOS / 'entitlements-mas.plist').read_bytes())
    inherit = plistlib.loads((MACOS / 'entitlements-mas-inherit.plist').read_bytes())
    setup_py = (MACOS / 'setup.py').read_text(encoding='utf-8')

    assert ent['com.apple.security.app-sandbox'] is True
    for key in ('network.client', 'network.server', 'files.user-selected.read-write', 'files.bookmarks.app-scope'):
        assert ent[f'com.apple.security.{key}'] is True
    assert not [k for k in ent if k.startswith('com.apple.security.cs.')]  # sin Hardened Runtime
    team = ent['com.apple.developer.team-identifier']
    assert ent['com.apple.application-identifier'] == f'{team}.com.edefrutos.gestorcorreos'
    assert '"CFBundleIdentifier": "com.edefrutos.gestorcorreos"' in setup_py
    assert inherit == {'com.apple.security.app-sandbox': True, 'com.apple.security.inherit': True}


def test_setup_omits_sparkle_keys_in_app_store_flavor():
    setup_py = (MACOS / 'setup.py').read_text(encoding='utf-8')
    assert 'if not APP_STORE:' in setup_py
    head, tail = setup_py.split('if not APP_STORE:', 1)
    assert '"SUFeedURL"' not in head and '"SUFeedURL"' in tail
    assert '"LSApplicationCategoryType"' in head
    assert '"CFBundleVersion": BUNDLE_VERSION' in head


def test_build_mas_script_contract():
    script = (MACOS / 'build_mas.sh').read_text(encoding='utf-8')
    assert 'GESTOR_DISTRIBUTION=mas' in script
    assert 'echo "mas" > "${RES}/DISTRIBUTION"' in script
    assert 'embedded.provisionprofile' in script
    assert '--entitlements "${ENTITLEMENTS_INHERIT}"' in script
    assert 'com.apple.security.app-sandbox' in script
    assert 'Sparkle.framework' in script  # comprueba que NO va dentro
    assert 'productbuild --component' in script
    assert 'MAS_LOCAL' in script
    assert '--options runtime' not in script


def test_frontend_hides_updates_and_offers_credentials_import():
    js = (ROOT / 'static' / 'app.js').read_text(encoding='utf-8')
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert "d.distribution==='mas'" in js
    assert 'window.pywebview.api.import_credentials()' in js
    assert 'id="cfg-creds-import"' in html and 'id="cfg-google"' in html
