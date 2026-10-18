import importlib.util
import json
import os
from pathlib import Path

import pytest

import updater

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("sign_manifest", ROOT / "macos" / "sign_manifest.py")
sign_manifest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sign_manifest)


def _keygen(tmp_path, capsys):
    key = tmp_path / "keys" / "update.pem"
    sign_manifest.keygen(key)
    public = capsys.readouterr().out.strip().splitlines()[-1]
    return key, public


def test_keygen_writes_private_key_600_and_prints_public(tmp_path, capsys):
    key, public = _keygen(tmp_path, capsys)
    assert (key.stat().st_mode & 0o777) == 0o600
    assert len(bytes.fromhex(public)) == 32
    with pytest.raises(SystemExit, match="ya existe"):
        sign_manifest.keygen(key)


def test_sign_produces_signature_the_updater_accepts(monkeypatch, tmp_path, capsys):
    key, public = _keygen(tmp_path, capsys)
    monkeypatch.setattr(updater, "UPDATE_PUBLIC_KEYS", (public,))
    manifest = tmp_path / "latest.json"
    manifest.write_text(json.dumps({"version": "9.9.9", "url": "https://x/y.zip", "sha256": "a" * 64}))
    sign_manifest.check(key)
    sign_manifest.sign(key, manifest)
    updater.verify_manifest_signature(manifest.read_bytes(), (tmp_path / "latest.json.sig").read_text())


def test_check_and_sign_refuse_key_not_embedded_in_app(monkeypatch, tmp_path, capsys):
    key, _ = _keygen(tmp_path, capsys)
    monkeypatch.setattr(updater, "UPDATE_PUBLIC_KEYS", ())
    manifest = tmp_path / "latest.json"
    manifest.write_text("{}")
    with pytest.raises(SystemExit, match="UPDATE_PUBLIC_KEYS"):
        sign_manifest.check(key)
    with pytest.raises(RuntimeError, match="clave pública"):
        sign_manifest.sign(key, manifest)
    assert not (tmp_path / "latest.json.sig").exists()


def test_load_key_refuses_readable_by_others(tmp_path, capsys):
    key, _ = _keygen(tmp_path, capsys)
    os.chmod(key, 0o644)
    with pytest.raises(SystemExit, match="chmod 600"):
        sign_manifest.load_key(key)


def test_app_embeds_a_valid_public_key():
    # Con la tupla vacía la app rechazaría todo manifiesto (y el build no arranca).
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    assert updater.UPDATE_PUBLIC_KEYS
    for key in updater.UPDATE_PUBLIC_KEYS:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(key))
