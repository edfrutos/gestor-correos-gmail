import base64
import importlib.util
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

import updater

MACOS = Path(__file__).parents[1] / 'macos'
sys.path.insert(0, str(MACOS))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, MACOS / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


make_appcast = _load('make_appcast')
delta_base = _load('delta_base')
app_main = _load('app_main')
SPARKLE_NS = '{http://www.andymatuschak.org/xml-namespaces/sparkle}'


def test_sparkle_public_key_is_the_manifest_key_in_base64():
    raw = base64.b64decode(updater.sparkle_public_key())
    assert raw.hex() == updater.UPDATE_PUBLIC_KEYS[0]
    assert len(raw) == 32


def test_sparkle_signature_cannot_be_reused_as_manifest_signature():
    # Separación de dominio: Sparkle firma los bytes del zip a pelo y el
    # manifiesto lleva MANIFEST_SIG_CONTEXT delante.
    key = Ed25519PrivateKey.generate()
    public_hex = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    raw = b'{"version": "9.9.9", "url": "x", "sha256": "y"}'
    sparkle_style = base64.b64encode(key.sign(raw)).decode()
    with pytest.raises(RuntimeError):
        updater.verify_manifest_signature(raw, sparkle_style, public_keys=(public_hex,))


@pytest.fixture
def signing_key(tmp_path, monkeypatch):
    key = Ed25519PrivateKey.generate()
    path = tmp_path / 'k.pem'
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                       serialization.NoEncryption()))
    path.chmod(0o600)
    public_hex = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    monkeypatch.setattr(updater, 'UPDATE_PUBLIC_KEYS', (public_hex,))
    return path


def test_make_appcast_writes_signed_feed(tmp_path, signing_key, capsys):
    archive = tmp_path / 'GestorDeCorreos-1.3.0.zip'
    archive.write_bytes(b'PK\x03\x04 contenido del zip')
    out = tmp_path / 'appcast.xml'

    make_appcast.main(['make_appcast.py', str(signing_key), str(archive), '1.3.0', str(out)])

    item = ET.parse(out).getroot().find('channel/item')
    assert item.find(f'{SPARKLE_NS}version').text == '1.3.0'
    assert item.find(f'{SPARKLE_NS}minimumSystemVersion').text == '12.0'
    enclosure = item.find('enclosure')
    assert enclosure.get('url') == (
        'https://github.com/edfrutos/gestor-correos-gmail/releases/download/v1.3.0/GestorDeCorreos-1.3.0.zip')
    assert enclosure.get('length') == str(archive.stat().st_size)
    public = Ed25519PublicKey.from_public_bytes(base64.b64decode(updater.sparkle_public_key()))
    public.verify(base64.b64decode(enclosure.get(f'{SPARKLE_NS}edSignature')), archive.read_bytes())


def test_make_appcast_refuses_key_not_embedded_in_app(tmp_path, signing_key, monkeypatch):
    monkeypatch.setattr(updater, 'UPDATE_PUBLIC_KEYS', ('00' * 32,))
    archive = tmp_path / 'a.zip'
    archive.write_bytes(b'PK')

    with pytest.raises(Exception):
        make_appcast.main(['make_appcast.py', str(signing_key), str(archive), '1.3.0', str(tmp_path / 'o.xml')])


def test_appcast_escapes_values():
    xml = make_appcast.build_appcast('1.3.0', 'a&b.zip', 10, 'c2ln', datetime(2026, 10, 20, tzinfo=timezone.utc))
    ET.fromstring(xml)  # XML bien formado
    assert 'a&amp;b.zip' in xml
    assert 'Tue, 20 Oct 2026 00:00:00 +0000' in xml


def test_sparkle_unavailable_without_framework(tmp_path):
    sparkle = app_main.SparkleUpdater(framework_path=str(tmp_path / 'no-existe.framework'))

    assert sparkle.start() is False
    assert sparkle.available is False
    assert sparkle.check_for_updates() is False


def test_sparkle_check_runs_on_main_thread_via_call_after():
    calls = []

    class Controller:
        def checkForUpdates_(self, sender):
            calls.append(('check', sender))

    sparkle = app_main.SparkleUpdater(call_after=lambda fn, arg: calls.append(('after', fn.__name__, arg)))
    sparkle.controller = Controller()

    assert sparkle.check_for_updates() is True
    assert calls == [('after', 'checkForUpdates_', None)]


def test_js_api_check_updates_falls_back_without_sparkle():
    assert app_main.JsApi().check_updates() is False
    assert app_main.JsApi(app_main.SparkleUpdater(framework_path='/no')).check_updates() is False


def test_update_menu_prefers_sparkle(monkeypatch):
    seen = []

    class FakeSparkle:
        def check_for_updates(self):
            seen.append('sparkle')
            return True

    menu = app_main._build_menu(None, object(), FakeSparkle())
    if not menu:
        pytest.skip('pywebview no instalado')
    menu[0].items[0].function()
    assert seen == ['sparkle']


def test_info_plist_declares_sparkle_feed_and_key():
    setup_py = (MACOS / 'setup.py').read_text(encoding='utf-8')
    assert '"SUFeedURL": updater.SPARKLE_FEED_URL' in setup_py
    assert '"SUPublicEDKey": updater.sparkle_public_key()' in setup_py
    assert updater.SPARKLE_FEED_URL.endswith('/releases/latest/download/appcast.xml')


def test_build_script_pins_sparkle_and_publishes_appcast():
    script = (MACOS / 'build_app.sh').read_text(encoding='utf-8')
    assert 'SPARKLE_SHA256="' in script and 'shasum -a 256 -c -' in script
    assert 'make_appcast.py' in script
    assert 'dist/latest.json dist/latest.json.sig dist/appcast.xml' in script


# --- Deltas (Fase 38) ---

def _signing(path):
    from sign_manifest import load_key
    return load_key(path)


def test_make_appcast_adds_signed_delta(tmp_path, signing_key):
    archive = tmp_path / 'GestorDeCorreos-1.3.2.zip'
    archive.write_bytes(b'PK\x03\x04 zip completo')
    delta = tmp_path / 'GestorDeCorreos-1.3.2-from-1.3.1.delta'
    delta.write_bytes(b'SPDA delta')
    out = tmp_path / 'appcast.xml'

    make_appcast.main(['make_appcast.py', str(signing_key), str(archive), '1.3.2', str(out), str(delta), '1.3.1'])

    item = ET.parse(out).getroot().find('channel/item')
    assert item.find('enclosure').get('url').endswith('/v1.3.2/GestorDeCorreos-1.3.2.zip')
    deltas = item.findall(f'{SPARKLE_NS}deltas/enclosure')
    assert len(deltas) == 1
    assert deltas[0].get(f'{SPARKLE_NS}deltaFrom') == '1.3.1'
    assert deltas[0].get('url') == ('https://github.com/edfrutos/gestor-correos-gmail/releases/download/'
                                    'v1.3.2/GestorDeCorreos-1.3.2-from-1.3.1.delta')
    assert deltas[0].get('length') == str(delta.stat().st_size)
    public = Ed25519PublicKey.from_public_bytes(base64.b64decode(updater.sparkle_public_key()))
    public.verify(base64.b64decode(deltas[0].get(f'{SPARKLE_NS}edSignature')), delta.read_bytes())


def test_make_appcast_without_delta_has_no_deltas_element():
    xml = make_appcast.build_appcast('1.3.2', 'a.zip', 10, 'c2ln')
    assert 'sparkle:deltas' not in xml


def _published(tmp_path, signing_key, version='1.3.1', data=b'PK\x03\x04 zip publicado', **overrides):
    url = overrides.pop('url', f'{make_appcast.REPO_URL}/releases/download/v{version}/GestorDeCorreos-{version}.zip')
    signature = make_appcast.sign_archive(_signing(signing_key), data)
    feed = make_appcast.build_appcast(version, url.rsplit('/', 1)[1], overrides.pop('length', len(data)),
                                      overrides.pop('signature', signature))
    feed = feed.replace(f'{make_appcast.REPO_URL}/releases/download/v{version}/{url.rsplit("/", 1)[1]}', url)
    files = {updater.SPARKLE_FEED_URL: feed.encode(), url: data}

    def http_get(u, binary=False):
        if u not in files:
            raise OSError(f'404 {u}')
        return files[u]
    return http_get, data


def test_delta_base_downloads_and_verifies_previous_release(tmp_path, signing_key, capsys):
    http_get, data = _published(tmp_path, signing_key)
    out = tmp_path / 'base.zip'

    assert delta_base.main(['delta_base.py', '1.3.2', str(out)], http_get=http_get) == 0

    assert out.read_bytes() == data
    assert capsys.readouterr().out.strip() == '1.3.1'


def test_delta_base_skips_when_published_is_not_older(tmp_path, signing_key):
    http_get, _ = _published(tmp_path, signing_key, version='1.3.2')
    out = tmp_path / 'base.zip'

    assert delta_base.main(['delta_base.py', '1.3.2', str(out)], http_get=http_get) == delta_base.NO_BASE
    assert not out.exists()


def test_delta_base_skips_when_offline(tmp_path):
    def offline(url, binary=False):
        raise OSError('sin red')

    assert delta_base.main(['delta_base.py', '1.3.2', str(tmp_path / 'b.zip')], http_get=offline) == delta_base.NO_BASE


def test_delta_base_rejects_bad_signature(tmp_path, signing_key):
    http_get, _ = _published(tmp_path, signing_key, signature=base64.b64encode(b'\0' * 64).decode())
    out = tmp_path / 'base.zip'

    with pytest.raises(SystemExit, match='firma'):
        delta_base.main(['delta_base.py', '1.3.2', str(out)], http_get=http_get)
    assert not out.exists()


def test_delta_base_rejects_wrong_length(tmp_path, signing_key):
    http_get, _ = _published(tmp_path, signing_key, length=3)

    with pytest.raises(SystemExit, match='mide'):
        delta_base.main(['delta_base.py', '1.3.2', str(tmp_path / 'b.zip')], http_get=http_get)


def test_delta_base_only_downloads_from_own_release(tmp_path, signing_key):
    http_get, _ = _published(tmp_path, signing_key, url='https://evil.example/GestorDeCorreos-1.3.1.zip')

    with pytest.raises(SystemExit, match='URL inesperada'):
        delta_base.main(['delta_base.py', '1.3.2', str(tmp_path / 'b.zip')], http_get=http_get)


def test_build_script_builds_verifies_and_publishes_delta():
    script = (MACOS / 'build_app.sh').read_text(encoding='utf-8')
    assert './Sparkle.framework ./bin/BinaryDelta' in script
    assert 'macos/delta_base.py' in script
    assert '"${BINARY_DELTA}" create' in script and '"${BINARY_DELTA}" apply' in script
    assert 'cdhash "${applied}"' in script
    assert '${DELTA_FILE:+' in script  # el delta va en el gh release create impreso
