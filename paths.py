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

Distribución (`distribution`): `"mas"` en la build de la Mac App Store
(`macos/build_mas.sh` deja un archivo `DISTRIBUTION` en `Contents/Resources`),
`"direct"` en el resto (Developer ID + Sparkle, web, CLI). En la Mac App Store
la app corre en App Sandbox (`Path.home()` ya es su contenedor) y no se
actualiza sola: lo hace la tienda.
"""

import os
import sys
from pathlib import Path

APP_SUPPORT_NAME = "GestorDeCorreos"
DISTRIBUTION_FILE = "DISTRIBUTION"
BUNDLED_OAUTH_CLIENT = "oauth_client.json"  # lo añade build_mas.sh
APP_STORE = "mas"
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


def distribution() -> str:
    """`"mas"` (Mac App Store) o `"direct"`. Override: `GESTOR_DISTRIBUTION`."""
    override = os.environ.get("GESTOR_DISTRIBUTION", "").strip().lower()
    if override:
        return override
    if not is_bundled():
        return "direct"
    try:
        value = (resource_dir() / DISTRIBUTION_FILE).read_text(encoding="utf-8").strip().lower()
    except OSError:
        return "direct"
    return value or "direct"


def is_app_store() -> bool:
    return distribution() == APP_STORE


def has_bundled_oauth_client() -> bool:
    """La build lleva el cliente OAuth del proyecto (`MAS_OAUTH_CLIENT` o
    `DIRECT_OAUTH_CLIENT`)."""
    return (resource_dir() / BUNDLED_OAUTH_CLIENT).is_file()


def verified_scope_only() -> bool:
    """Solo `gmail.modify` y datos que no salen del Mac.

    Es lo declarado a Google para el cliente OAuth del proyecto, así que rige en
    la Mac App Store y en cualquier build que lleve ese cliente (también la de
    descarga directa): sin borrado permanente (`mail.google.com`) ni IA remota.
    """
    return is_app_store() or has_bundled_oauth_client()


def data_path(name: str) -> Path:
    """Ruta de un archivo de estado dentro de `data_dir()`."""
    return data_dir() / name


def real_home() -> str:
    """Carpeta real del usuario (pwd), no HOME: en App Sandbox HOME apunta al
    contenedor de la app."""
    import pwd
    try:
        return pwd.getpwuid(os.getuid()).pw_dir.rstrip("/")
    except (KeyError, OSError):
        return os.path.expanduser("~").rstrip("/")


def display_path(path) -> str:
    """Ruta para enseñar en la interfaz, con la carpeta del usuario como «~»,
    para que el nombre de usuario no salga en las capturas."""
    text = str(path)
    home = real_home()
    if home and (text == home or text.startswith(home + "/")):
        return "~" + text[len(home):]
    return text


def expand_display_path(text: str) -> str:
    """Inversa de display_path: «~» o «~/…» pasan a la carpeta real del usuario.
    No usa expanduser, que en App Sandbox expandiría al contenedor."""
    text = str(text)
    if text == "~" or text.startswith("~/"):
        return real_home() + text[1:]
    return text
