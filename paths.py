"""Resolución de rutas del proyecto.

Distingue dos carpetas:

- **datos escribibles** (`data_dir`): tokens OAuth, `app_state.json`, exports,
  `.env` opcional. Cuando la app corre desde el código fuente (app web / CLI)
  es la carpeta del proyecto, como siempre. Cuando corre dentro de un `.app`
  empaquetado con py2app (`sys.frozen`), va a
  `~/Library/Application Support/GestorDeCorreos/`, porque el bundle es de solo
  lectura y está firmado.
- **recursos de solo lectura** (`resource_dir`): `index.html`, `static/*`.
  En el bundle, `Contents/Resources/`; desde fuente, la carpeta del proyecto.

Override explícito para ambos casos de datos: variable de entorno
`GESTOR_DATA_DIR` (útil en tests y para usuarios avanzados).
"""

import os
import sys
from pathlib import Path

APP_SUPPORT_NAME = "GestorDeCorreos"
_PROJECT_DIR = Path(__file__).resolve().parent


def is_bundled() -> bool:
    """True si se ejecuta dentro de un .app empaquetado (py2app / PyInstaller)."""
    return bool(getattr(sys, "frozen", False))


def data_dir() -> Path:
    """Carpeta escribible para estado local. Se crea si no existe."""
    override = os.environ.get("GESTOR_DATA_DIR")
    if override:
        target = Path(override).expanduser()
    elif is_bundled():
        target = Path.home() / "Library" / "Application Support" / APP_SUPPORT_NAME
    else:
        target = _PROJECT_DIR
    target.mkdir(parents=True, exist_ok=True)
    return target


def resource_dir() -> Path:
    """Carpeta de assets de solo lectura (HTML/CSS/JS servidos por el servidor)."""
    res = os.environ.get("RESOURCEPATH")  # py2app define esta variable en runtime
    if res:
        return Path(res)
    if is_bundled():
        return Path(sys.executable).resolve().parent.parent / "Resources"
    return _PROJECT_DIR


def data_path(name: str) -> Path:
    """Ruta de un archivo de estado dentro de `data_dir()`."""
    return data_dir() / name
