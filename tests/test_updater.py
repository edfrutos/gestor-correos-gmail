import json
import sys

import pytest

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


def _fake_http(manifest):
    def _get(url, binary=False):
        return json.dumps(manifest)
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
    ([(f"{APP}/x", b""), (f"{APP}/la/evil.plist", b"")], [(f"{APP}/la", "../../../Library/LaunchAgents")], "sale de la .app"),
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
    ([(f"{APP}/x", b""), (f"{APP}/LA/evil.plist", b"")], [(f"{APP}/la", "../../..")], "sale de la .app"),
    ([(f"{APP}/x", b""), (f"{APP}/X", b"")], [], "duplicada"),
    ([(f"{APP}/caf\u00e9", b""), (f"{APP}/cafe\u0301", b"")], [], "duplicada"),
])
def test_check_zip_entries_rejects_escapes(tmp_path, files, links, match):
    z = build_zip(tmp_path / "u.zip", files, links)
    with pytest.raises(RuntimeError, match=match):
        updater._check_zip_entries(z)


def fake_ditto_extract(cmd):
    """Sustituto de `ditto -x -k` para Linux/CI: extrae y recrea symlinks."""
    zip_path, dest = cmd[-2], cmd[-1]
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            out = os.path.join(dest, info.filename)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            if stat.S_ISLNK(info.external_attr >> 16):
                os.symlink(zf.read(info).decode(), out)
            elif not info.filename.endswith("/"):
                with open(out, "wb") as fh:
                    fh.write(zf.read(info))


def stage(monkeypatch, tmp_path, zip_bytes):
    calls = []
    (tmp_path / "work").mkdir()
    monkeypatch.setattr(updater, "_http_get", lambda url, binary=False: zip_bytes)
    monkeypatch.setattr(updater, "_run", lambda cmd: (calls.append(cmd), fake_ditto_extract(cmd)))
    monkeypatch.setattr(updater, "_verify_app_signature", lambda p: calls.append(("verify", p)))
    sha = hashlib.sha256(zip_bytes).hexdigest()
    return calls, updater.download_and_stage("https://x/u.zip", sha, workdir=tmp_path / "work")


def test_download_and_stage_validates_before_extracting(monkeypatch, tmp_path):
    bad = build_zip(tmp_path / "bad.zip", [(f"{APP}/x", b""), ("../evil", b"")]).read_bytes()
    calls = []
    (tmp_path / "w").mkdir()
    monkeypatch.setattr(updater, "_http_get", lambda url, binary=False: bad)
    monkeypatch.setattr(updater, "_run", lambda cmd: calls.append(cmd))
    with pytest.raises(RuntimeError, match="fuera del paquete"):
        updater.download_and_stage("https://x/u.zip", hashlib.sha256(bad).hexdigest(), workdir=tmp_path / "w")
    assert calls == []  # ditto nunca llega a ejecutarse


def test_download_and_stage_happy_path_returns_root_app(monkeypatch, tmp_path):
    good = build_zip(tmp_path / "good.zip", LEGIT_FILES, LEGIT_LINKS).read_bytes()
    calls, app_path = stage(monkeypatch, tmp_path, good)
    assert app_path == tmp_path / "work" / "extracted" / APP
    assert calls[0][0] == "/usr/bin/ditto"
    assert calls[-1] == ("verify", app_path)


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
