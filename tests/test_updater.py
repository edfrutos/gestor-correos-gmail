import base64
import json
import sys

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import updater


def test_parse_version_extracts_numeric_tuple():
    assert updater.parse_version("1.2.3") == (1, 2, 3)
    assert updater.parse_version("v1.10.0") == (1, 10, 0)
    assert updater.parse_version("nonsense") == (0,)
    assert updater.parse_version("2.0") < updater.parse_version("2.0.1")
    assert updater.parse_version("1.9.0") < updater.parse_version("1.10.0")


def test_current_version_reads_version_file(monkeypatch):
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert updater.current_version() == (updater.Path(updater.__file__).resolve().parent / "VERSION").read_text().strip()


def test_manifest_url_env_override(monkeypatch):
    monkeypatch.setenv("GESTOR_UPDATE_MANIFEST_URL", "https://example.test/latest.json")
    assert updater.manifest_url() == "https://example.test/latest.json"


@pytest.fixture(autouse=True)
def signing_key(monkeypatch):
    """Clave de prueba: la app solo acepta `latest.json` firmado con ella."""
    key = Ed25519PrivateKey.generate()
    monkeypatch.setattr(updater, "UPDATE_PUBLIC_KEYS", (_public_hex(key),))
    monkeypatch.setattr(_fake_http, "key", key, raising=False)
    return key


def _public_hex(key):
    return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def _sign(key, raw):
    return base64.b64encode(key.sign(updater.MANIFEST_SIG_CONTEXT + raw)).decode("ascii")


def _fake_http(manifest, key=None, signature=None):
    """Sirve `latest.json` y su `.sig` (firmado con `key` o con `signature` literal)."""
    raw = json.dumps(manifest).encode("utf-8")

    def _get(url, binary=False):
        if url.endswith(".sig"):
            sig = signature if signature is not None else _sign(key or _fake_http.key, raw)
            return sig
        return raw if binary else raw.decode("utf-8")
    return _get


def test_check_for_update_reports_available(monkeypatch):
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(updater, "current_version", lambda: "1.0.0")
    monkeypatch.setattr(updater, "_http_get", _fake_http({
        "version": "1.2.0",
        "url": "https://example.test/app-1.2.0.zip",
        "sha256": "ABC123",
        "notes_url": "https://example.test/notes",
    }))
    result = updater.check_for_update()
    assert result["update_available"] is True
    assert result["latest"] == "1.2.0"
    assert result["sha256"] == "abc123"          # normalizado a minúsculas
    assert result["can_auto_install"] is False   # no bundled en tests


def test_check_for_update_reports_up_to_date(monkeypatch):
    monkeypatch.setattr(updater, "current_version", lambda: "3.0.0")
    monkeypatch.setattr(updater, "_http_get", _fake_http({
        "version": "3.0.0", "url": "https://x/y.zip", "sha256": "d",
    }))
    result = updater.check_for_update()
    assert result["update_available"] is False


def test_check_for_update_reports_missing_feed_as_404(monkeypatch):
    from urllib.error import HTTPError

    def raise_404(url, binary=False):
        raise HTTPError(url, 404, "Not Found", {}, None)

    monkeypatch.setattr(updater, "current_version", lambda: "1.0.0")
    monkeypatch.setattr(updater, "_http_get", raise_404)
    result = updater.check_for_update()
    assert result["no_feed"] is True
    assert result["update_available"] is False
    assert "publicada" in result["error"]


def test_check_for_update_handles_network_error(monkeypatch):
    def boom(url, binary=False):
        raise OSError("sin red")
    monkeypatch.setattr(updater, "current_version", lambda: "1.0.0")
    monkeypatch.setattr(updater, "_http_get", boom)
    result = updater.check_for_update()
    assert "error" in result and result["current"] == "1.0.0"
    assert "update_available" not in result


def test_fetch_manifest_rejects_incomplete_json(monkeypatch):
    monkeypatch.setattr(updater, "_http_get", _fake_http({"version": "1.0.0"}))
    with pytest.raises(ValueError):
        updater.fetch_manifest()


# ── Firma Ed25519 de latest.json ──

_MANIFEST = {"version": "9.0.0", "url": "https://example.test/evil.zip", "sha256": "e" * 64}


def test_check_for_update_rejects_tampered_manifest(monkeypatch, signing_key):
    # Firma válida de un manifiesto, servida junto a otro distinto.
    genuine = json.dumps({**_MANIFEST, "version": "1.0.1"}).encode()
    monkeypatch.setattr(updater, "current_version", lambda: "1.0.0")
    monkeypatch.setattr(updater, "_http_get", _fake_http(_MANIFEST, signature=_sign(signing_key, genuine)))
    result = updater.check_for_update()
    assert "update_available" not in result
    assert "firma" in result["error"]


def test_check_for_update_rejects_manifest_signed_with_other_key(monkeypatch):
    monkeypatch.setattr(updater, "current_version", lambda: "1.0.0")
    monkeypatch.setattr(updater, "_http_get", _fake_http(_MANIFEST, key=Ed25519PrivateKey.generate()))
    result = updater.check_for_update()
    assert "update_available" not in result
    assert "firma" in result["error"]


def test_check_for_update_rejects_missing_signature_not_as_no_feed(monkeypatch):
    from urllib.error import HTTPError

    def get(url, binary=False):
        if url.endswith(".sig"):
            raise HTTPError(url, 404, "Not Found", {}, None)
        return json.dumps(_MANIFEST).encode()

    monkeypatch.setattr(updater, "current_version", lambda: "1.0.0")
    monkeypatch.setattr(updater, "_http_get", get)
    result = updater.check_for_update()
    assert "no_feed" not in result and "update_available" not in result
    assert "firma" in result["error"] and "404" in result["error"]


@pytest.mark.parametrize("signature", ["", "no-es-base64!!", base64.b64encode(b"x" * 63).decode()])
def test_verify_manifest_signature_rejects_malformed(signature):
    with pytest.raises(RuntimeError, match="firma"):
        updater.verify_manifest_signature(b"{}", signature)


def test_verify_manifest_signature_fails_closed_without_keys(monkeypatch, signing_key):
    monkeypatch.setattr(updater, "UPDATE_PUBLIC_KEYS", ())
    with pytest.raises(RuntimeError, match="clave pública"):
        updater.verify_manifest_signature(b"{}", _sign(signing_key, b"{}"))


def test_verify_manifest_signature_accepts_any_listed_key_for_rotation(monkeypatch, signing_key):
    new_key = Ed25519PrivateKey.generate()
    monkeypatch.setattr(updater, "UPDATE_PUBLIC_KEYS", (_public_hex(signing_key), _public_hex(new_key)))
    updater.verify_manifest_signature(b"{}", _sign(new_key, b"{}"))


def test_verify_manifest_signature_is_bound_to_context(signing_key):
    # Una firma Ed25519 de los mismos bytes sin el contexto no vale.
    raw = b"{}"
    bare = base64.b64encode(signing_key.sign(raw)).decode()
    with pytest.raises(RuntimeError, match="firma"):
        updater.verify_manifest_signature(raw, bare)


def test_install_and_relaunch_refuses_when_not_bundled(monkeypatch):
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    with pytest.raises(RuntimeError):
        updater.install_and_relaunch("/tmp/whatever.app")


def test_download_and_stage_rejects_sha_mismatch(monkeypatch, tmp_path):
    monkeypatch.setattr(updater, "_http_get", lambda url, binary=False: b"payload-bytes")
    with pytest.raises(RuntimeError, match="sha256 no coincide"):
        updater.download_and_stage("https://x/y.zip", "0" * 64, workdir=tmp_path)


# ── Validación del índice del zip antes de extraer (hallazgo de seguridad PR #2) ──
import hashlib
import os
import plistlib
import stat
import warnings
import zipfile

APP = "Gestor de Correos.app"


def build_zip(path, files=(), links=()):
    """files: [(nombre, bytes)], links: [(nombre, destino)] como symlinks."""
    with warnings.catch_warnings(), zipfile.ZipFile(path, "w") as zf:
        warnings.simplefilter("ignore")  # algunos casos repiten nombres a propósito
        for name, data in files:
            zf.writestr(name, data)
        for name, target in links:
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o755) << 16
            zf.writestr(info, target)
    return path


FRAMEWORK = f"{APP}/Contents/Frameworks/Python.framework"
LEGIT_FILES = [
    (f"{APP}/Contents/Info.plist", b"plist"),
    (f"{APP}/Contents/MacOS/Gestor", b"bin"),
    (f"{FRAMEWORK}/Versions/3.12/Python", b"lib"),
    ("__MACOSX/._Gestor de Correos.app", b"appledouble"),
]
LEGIT_LINKS = [
    (f"{FRAMEWORK}/Versions/Current", "3.12"),
    (f"{FRAMEWORK}/Python", "Versions/Current/Python"),
    (f"{APP}/Contents/MacOS/python", "../Frameworks/Python.framework/Python"),
]


def test_check_zip_entries_accepts_real_bundle_layout(tmp_path):
    z = build_zip(tmp_path / "u.zip", LEGIT_FILES, LEGIT_LINKS)
    assert updater._check_zip_entries(z) == APP


@pytest.mark.parametrize("files,links,match", [
    ([(f"{APP}/x", b""), ("../../Library/LaunchAgents/evil.plist", b"")], [], "fuera del paquete"),
    ([(f"{APP}/x", b""), ("/tmp/evil", b"")], [], "fuera del paquete"),
    ([(f"{APP}/x", b""), ("Otra.app/x", b"")], [], "única .app"),
    ([("payload/x", b"")], [], "única .app"),
    # symlink directo fuera de la .app y escritura a través de él
    ([(f"{APP}/x", b""), (f"{APP}/la/evil.plist", b"")], [(f"{APP}/la", "../../../Library/LaunchAgents")], "sale de la .app|bajo un symlink"),
    ([(f"{APP}/x", b"")], [(f"{APP}/abs", "/Users/victima")], "sale de la .app"),
    # cadena: cada destino parece interno textualmente, pero físicamente sale
    ([(f"{APP}/x", b"")], [(f"{APP}/Contents/Frameworks/up", "../.."), (f"{APP}/esc", "Contents/Frameworks/up/..")], "sale de la .app"),
    ([(f"{APP}/x", b"")], [("__MACOSX/l", "x")], "Symlink no permitido"),
    ([(f"{APP}/x", b"")], [(f"{APP}/a", "b"), (f"{APP}/b", "a")], "demasiado larga"),
    # mismo nombre dos veces: ditto aplica en orden, el validador vería solo el último
    ([(f"{APP}/x", b""), (f"{APP}/la/evil.plist", b"")], [(f"{APP}/la", "Contents"), (f"{APP}/la", "Contents")], "duplicada"),
    ([(f"{APP}/x", b""), (f"{APP}/x", b"otra")], [], "duplicada"),
    ([(f"{APP}/d/", b""), (f"{APP}/x", b"")], [(f"{APP}/d", "Contents")], "duplicada"),
    # APFS no distingue mayúsculas ni NFC/NFD: "la" y "LA" son la misma ruta
    ([(f"{APP}/x", b""), (f"{APP}/LA/evil.plist", b"")], [(f"{APP}/la", "../../..")], "sale de la .app|bajo un symlink"),
    ([(f"{APP}/x", b""), (f"{APP}/X", b"")], [], "duplicada"),
    ([(f"{APP}/caf\u00e9", b""), (f"{APP}/cafe\u0301", b"")], [], "duplicada"),
])
def test_check_zip_entries_rejects_escapes(tmp_path, files, links, match):
    z = build_zip(tmp_path / "u.zip", files, links)
    with pytest.raises(RuntimeError, match=match):
        updater._check_zip_entries(z)


def build_zip_with_modes(path, version="99.0.0"):
    """Zip con la forma del de `ditto -c -k --keepParent`: modos Unix + symlinks."""
    plist = plistlib.dumps({"CFBundleShortVersionString": version})
    with zipfile.ZipFile(path, "w") as zf:
        for name, data, mode in [
            (f"{APP}/", b"", stat.S_IFDIR | 0o755),
            (f"{APP}/Contents/Info.plist", plist, stat.S_IFREG | 0o644),
            (f"{APP}/Contents/MacOS/Gestor", b"bin", stat.S_IFREG | 0o755),
            (f"{FRAMEWORK}/Versions/3.12/Python", b"lib", stat.S_IFREG | 0o755),
            ("__MACOSX/._x", b"appledouble", stat.S_IFREG | 0o644),
        ]:
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = mode << 16
            zf.writestr(info, data)
    with zipfile.ZipFile(path, "a") as zf:
        for name, target in LEGIT_LINKS:
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o755) << 16
            zf.writestr(info, target)
    return path


def test_download_and_stage_never_runs_ditto_and_rejects_before_writing(monkeypatch, tmp_path):
    bad = build_zip(tmp_path / "bad.zip", [(f"{APP}/x", b""), ("../evil", b"")]).read_bytes()
    calls = []
    (tmp_path / "w").mkdir()
    monkeypatch.setattr(updater, "_http_get", lambda url, binary=False: bad)
    monkeypatch.setattr(updater, "_run", lambda cmd: calls.append(cmd))
    with pytest.raises(RuntimeError, match="fuera del paquete"):
        updater.download_and_stage("https://x/u.zip", hashlib.sha256(bad).hexdigest(), workdir=tmp_path / "w")
    assert calls == []
    assert not (tmp_path / "evil").exists() and not (tmp_path / "w" / "extracted").exists()


def test_download_and_stage_extracts_bundle_with_symlinks_and_modes(monkeypatch, tmp_path):
    good = build_zip_with_modes(tmp_path / "good.zip").read_bytes()
    verified = []
    (tmp_path / "work").mkdir()
    monkeypatch.setattr(updater, "_http_get", lambda url, binary=False: good)
    monkeypatch.setattr(updater, "_run", lambda cmd: pytest.fail(f"no debe invocar {cmd[0]}"))
    monkeypatch.setattr(updater, "_verify_app_signature", verified.append)

    app = updater.download_and_stage("https://x/u.zip", hashlib.sha256(good).hexdigest(), workdir=tmp_path / "work")

    assert app == tmp_path / "work" / "extracted" / APP
    assert verified == [app]
    fw = app / "Contents/Frameworks/Python.framework"
    assert os.readlink(fw / "Versions/Current") == "3.12"
    assert (fw / "Python").read_bytes() == b"lib"  # symlink resuelto de verdad
    assert os.readlink(app / "Contents/MacOS/python") == "../Frameworks/Python.framework/Python"
    assert stat.S_IMODE(os.stat(app / "Contents/MacOS/Gestor").st_mode) == 0o755
    assert stat.S_IMODE(os.stat(app / "Contents/Info.plist").st_mode) == 0o644
    assert not (tmp_path / "work" / "extracted" / "__MACOSX").exists()


def test_extract_zip_strips_setuid_bits(tmp_path):
    z = tmp_path / "u.zip"
    with zipfile.ZipFile(z, "w") as zf:
        info = zipfile.ZipInfo(f"{APP}/Contents/MacOS/Gestor")
        info.create_system = 3
        info.external_attr = (stat.S_IFREG | 0o4755) << 16
        zf.writestr(info, b"bin")
    updater._check_zip_entries(z)
    updater._extract_zip(z, tmp_path / "out")
    assert stat.S_IMODE(os.stat(tmp_path / "out" / APP / "Contents/MacOS/Gestor").st_mode) == 0o755


def test_check_zip_entries_rejects_entry_under_symlink(tmp_path):
    z = build_zip(tmp_path / "u.zip", [(f"{APP}/Contents/x", b""), (f"{APP}/l/y", b"")], [(f"{APP}/l", "Contents")])
    with pytest.raises(RuntimeError, match="bajo un symlink"):
        updater._check_zip_entries(z)


def test_check_zip_entries_rejects_zip_bomb(monkeypatch, tmp_path):
    monkeypatch.setattr(updater, "_MAX_UNCOMPRESSED", 10)
    z = build_zip(tmp_path / "u.zip", [(f"{APP}/x", b"0" * 11)])
    with pytest.raises(RuntimeError, match="demasiado grande"):
        updater._check_zip_entries(z)


def test_check_extracted_links_catches_escape_on_disk(tmp_path):
    app = tmp_path / APP
    app.mkdir()
    os.symlink(str(tmp_path), app / "fuera")
    with pytest.raises(RuntimeError, match="tras extraer"):
        updater._check_extracted_links(app)


def test_check_zip_entries_rejects_ordered_overwrite_from_review(tmp_path):
    # Caso exacto del PR #2 (2ª revisión): enlace que sale, fichero escrito a
    # través de él y un segundo enlace inocuo con el mismo nombre al final.
    z = build_zip(tmp_path / "u.zip", [(f"{APP}/x", b"")], [])
    with zipfile.ZipFile(z, "a") as zf:
        for name, target in [(f"{APP}/la", "../../.."), (f"{APP}/la/evil.plist", None), (f"{APP}/la", "Contents")]:
            info = zipfile.ZipInfo(name)
            if target is None:
                zf.writestr(info, b"evil")
                continue
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o755) << 16
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # zipfile avisa del nombre duplicado
                zf.writestr(info, target)
    with pytest.raises(RuntimeError, match="duplicada|sale de la .app"):
        updater._check_zip_entries(z)


def test_check_zip_entries_returns_root_with_original_case(tmp_path):
    z = build_zip(tmp_path / "u.zip", LEGIT_FILES, LEGIT_LINKS)
    assert updater._check_zip_entries(z) == APP  # no la forma canónica en minúsculas


@pytest.mark.parametrize("version", ["1.2.2", "1.0.0"])
def test_download_and_stage_rejects_same_or_older_signed_app(monkeypatch, tmp_path, version):
    # Release comprometido: .app antigua legítima (firma válida) con latest.json que miente
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(updater, "_read_version_file", lambda: "1.2.2")
    old = build_zip_with_modes(tmp_path / "old.zip", version=version).read_bytes()
    (tmp_path / "work").mkdir()
    monkeypatch.setattr(updater, "_http_get", lambda url, binary=False: old)
    monkeypatch.setattr(updater, "_verify_app_signature", lambda app: None)
    with pytest.raises(RuntimeError, match="no es más nuevo"):
        updater.download_and_stage("https://x/u.zip", hashlib.sha256(old).hexdigest(), workdir=tmp_path / "work")


def test_download_and_stage_rejects_app_without_version(monkeypatch, tmp_path):
    z = build_zip_with_modes(tmp_path / "u.zip")
    with zipfile.ZipFile(z) as src, zipfile.ZipFile(tmp_path / "nov.zip", "w") as dst:
        for info in src.infolist():
            data = src.read(info)
            if info.filename.endswith("Info.plist"):
                data = plistlib.dumps({"CFBundleIdentifier": "x"})
            dst.writestr(info, data)
    raw = (tmp_path / "nov.zip").read_bytes()
    (tmp_path / "work").mkdir()
    monkeypatch.setattr(updater, "_http_get", lambda url, binary=False: raw)
    monkeypatch.setattr(updater, "_verify_app_signature", lambda app: None)
    with pytest.raises(RuntimeError, match="versión del paquete"):
        updater.download_and_stage("https://x/u.zip", hashlib.sha256(raw).hexdigest(), workdir=tmp_path / "work")
