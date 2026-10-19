import pytest

import settings


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    # Ningún test debe leer ni escribir el settings.json real de la carpeta de datos.
    monkeypatch.setattr(settings, 'SETTINGS_FILE', tmp_path / 'settings.json')
