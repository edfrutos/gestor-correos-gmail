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
