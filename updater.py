"""Buscar, descargar e instalar actualizaciones de la app macOS.

Modelo de confianza (cualquier fallo aborta la instalación):
  1. `latest.json` se descarga por HTTPS de GitHub Releases.
  2. El `.zip` se verifica por sha256 contra el manifiesto (integridad).
  3. El `.app` extraído se verifica con `codesign --verify --strict`, `spctl`
     (notarización) y se comprueba que el `TeamIdentifier` es el nuestro
     (autenticidad). Sin (3), un manifiesto manipulado permitiría ejecutar
     código arbitrario.

La comprobación funciona también desde el código fuente; la instalación
automática solo en la `.app` empaquetada (`paths.is_bundled()`).
"""

import hashlib
import json
import os
import plistlib
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import paths

APP_VERSION_FALLBACK = "0.0.0"
EXPECTED_TEAM_ID = "V29BTBRY6G"
DEFAULT_MANIFEST_URL = (
    "https://github.com/edfrutos/gestor-correos-gmail/releases/latest/download/latest.json"
)
_UA = "GestorDeCorreos-Updater"
_TIMEOUT = 20


def _read_version_file():
    for base in (paths.resource_dir(), Path(__file__).resolve().parent):
        try:
            value = (base / "VERSION").read_text(encoding="utf-8").strip()
            if value:
                return value
        except OSError:
            continue
    return APP_VERSION_FALLBACK


def bundle_path():
    """Ruta al `.app` en ejecución (…/Gestor de Correos.app), o `sys.executable`."""
    exe = Path(sys.executable).resolve()
    for parent in exe.parents:
        if parent.suffix == ".app":
            return parent
    return exe


def current_version():
    """Versión en ejecución. En la `.app`, el `CFBundleShortVersionString`."""
    if paths.is_bundled():
        try:
            info = bundle_path() / "Contents" / "Info.plist"
            data = plistlib.loads(info.read_bytes())
            version = data.get("CFBundleShortVersionString")
            if version:
                return str(version)
        except Exception:
            pass
    return _read_version_file()


def manifest_url():
    return os.environ.get("GESTOR_UPDATE_MANIFEST_URL", DEFAULT_MANIFEST_URL)


def parse_version(value):
    parts = tuple(int(x) for x in re.findall(r"\d+", str(value))[:4])
    return parts or (0,)


def _http_get(url, binary=False):
    req = Request(url, headers={"User-Agent": _UA, "Accept": "*/*"})
    with urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310  (HTTPS, host fijo)
        raw = resp.read()
    return raw if binary else raw.decode("utf-8")


def fetch_manifest():
    manifest = json.loads(_http_get(manifest_url()))
    required = ("version", "url", "sha256")
    if not isinstance(manifest, dict) or any(k not in manifest for k in required):
        raise ValueError("Manifiesto de actualización inválido")
    return {
        "version": str(manifest["version"]),
        "url": str(manifest["url"]),
        "sha256": str(manifest["sha256"]).lower(),
        "notes_url": str(manifest.get("notes_url") or ""),
        "notes": str(manifest.get("notes") or ""),
    }


def check_for_update():
    current = current_version()
    try:
        manifest = fetch_manifest()
    except HTTPError as exc:
        if exc.code == 404:
            return {"current": current, "update_available": False,
                    "no_feed": True,
                    "error": "Aún no hay ninguna versión publicada para comprobar."}
        return {"current": current, "error": f"No se pudo consultar actualizaciones (HTTP {exc.code})."}
    except Exception as exc:
        return {"current": current, "error": f"No se pudo consultar actualizaciones: {exc}"}
    available = parse_version(manifest["version"]) > parse_version(current)
    return {
        "current": current,
        "latest": manifest["version"],
        "update_available": available,
        "url": manifest["url"],
        "sha256": manifest["sha256"],
        "notes_url": manifest["notes_url"],
        "notes": manifest["notes"],
        "can_auto_install": paths.is_bundled(),
    }


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_app_signature(app_path):
    """codesign estricto + spctl (notarización) + TeamIdentifier esperado."""
    subprocess.run(
        ["/usr/bin/codesign", "--verify", "--strict", "--deep", str(app_path)],
        check=True, capture_output=True,
    )
    spctl = subprocess.run(
        ["/usr/sbin/spctl", "-a", "-t", "exec", "-vv", str(app_path)],
        capture_output=True, text=True,
    )
    if spctl.returncode != 0 or "accepted" not in (spctl.stderr + spctl.stdout):
        raise RuntimeError("La actualización no está firmada/notarizada correctamente")
    describe = subprocess.run(
        ["/usr/bin/codesign", "-dv", "--verbose=4", str(app_path)],
        capture_output=True, text=True,
    )
    team = ""
    for line in (describe.stderr + describe.stdout).splitlines():
        if line.startswith("TeamIdentifier="):
            team = line.split("=", 1)[1].strip()
    if team != EXPECTED_TEAM_ID:
        raise RuntimeError(f"TeamIdentifier inesperado en la actualización: {team!r}")


def download_and_stage(url, sha256, workdir=None):
    """Descarga el zip, verifica sha256, extrae y valida firma.

    Devuelve la ruta del `.app` extraído listo para instalar.
    """
    tmp = Path(workdir or tempfile.mkdtemp(prefix="gestor-update-"))
    zip_path = tmp / "update.zip"
    zip_path.write_bytes(_http_get(url, binary=True))
    got = _sha256(zip_path)
    if got.lower() != str(sha256).lower():
        raise RuntimeError(f"sha256 no coincide (esperado {sha256}, obtenido {got})")
    extract_dir = tmp / "extracted"
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(extract_dir)
    apps = list(extract_dir.glob("*.app")) or list(extract_dir.rglob("*.app"))
    if not apps:
        raise RuntimeError("El paquete de actualización no contiene ninguna .app")
    app_path = apps[0]
    _verify_app_signature(app_path)
    return app_path


_HELPER = r"""#!/bin/bash
set -e
APP_PID="$1"; NEW="$2"; CUR="$3"
while /bin/kill -0 "$APP_PID" 2>/dev/null; do /bin/sleep 0.5; done
if ! /usr/bin/ditto "$NEW" "$CUR" 2>/dev/null; then
  /usr/bin/osascript -e "do shell script \"/usr/bin/ditto \\\"$NEW\\\" \\\"$CUR\\\"\" with administrator privileges"
fi
/usr/bin/xattr -dr com.apple.quarantine "$CUR" 2>/dev/null || true
/usr/bin/open "$CUR"
"""


def install_and_relaunch(new_app_path):
    """Lanza un helper *detached* que espera a que este proceso termine,
    sustituye la `.app` instalada por `new_app_path` y relanza la app.

    El llamador debe salir del proceso justo después.
    """
    if not paths.is_bundled():
        raise RuntimeError("La instalación automática solo funciona en la app empaquetada")
    current_app = bundle_path()
    helper = Path(tempfile.mkdtemp(prefix="gestor-update-")) / "install.sh"
    helper.write_text(_HELPER, encoding="utf-8")
    helper.chmod(0o755)
    subprocess.Popen(  # noqa: S603
        ["/bin/bash", str(helper), str(os.getpid()), str(new_app_path), str(current_app)],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
