import sys
from pathlib import Path

import paths


PROJECT_DIR = Path(paths.__file__).resolve().parent


def test_data_dir_defaults_to_project_dir_from_source(monkeypatch):
    monkeypatch.delenv('GESTOR_DATA_DIR', raising=False)
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    assert paths.data_dir() == PROJECT_DIR


def test_data_dir_honours_env_override_and_creates_it(monkeypatch, tmp_path):
    target = tmp_path / 'estado'
    monkeypatch.setenv('GESTOR_DATA_DIR', str(target))
    assert not target.exists()
    assert paths.data_dir() == target
    assert target.is_dir()


def test_data_path_joins_under_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv('GESTOR_DATA_DIR', str(tmp_path))
    assert paths.data_path('token.json') == tmp_path / 'token.json'


def test_is_bundled_false_under_tests(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    assert paths.is_bundled() is False


def test_resource_dir_prefers_resourcepath(monkeypatch, tmp_path):
    monkeypatch.setenv('RESOURCEPATH', str(tmp_path))
    assert paths.resource_dir() == tmp_path


def test_resource_dir_defaults_to_project_dir_from_source(monkeypatch):
    monkeypatch.delenv('RESOURCEPATH', raising=False)
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    assert paths.resource_dir() == PROJECT_DIR


def test_bundled_mode_uses_application_support(monkeypatch, tmp_path):
    monkeypatch.delenv('GESTOR_DATA_DIR', raising=False)
    monkeypatch.setattr(sys, 'frozen', 'macosx_app', raising=False)
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))
    expected = tmp_path / 'Library' / 'Application Support' / 'GestorDeCorreos'
    assert paths.data_dir() == expected
    assert expected.is_dir()
