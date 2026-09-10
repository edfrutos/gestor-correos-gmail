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
