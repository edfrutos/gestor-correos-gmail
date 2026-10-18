"""Buscar, descargar e instalar actualizaciones de la app macOS.

Modelo de confianza (cualquier fallo aborta la instalación):
  1. `latest.json` se descarga por HTTPS de GitHub Releases.
  2. El `.zip` se verifica por sha256 contra el manifiesto (integridad).
  3. El `.app` extraído se verifica con `codesign --verify --strict`, `spctl`
     (notarización) y se comprueba que el `TeamIdentifier` es el nuestro
     (autenticidad). Sin (3), un manifiesto manipulado permitiría ejecutar
     código arbitrario.
  4. Antes de extraer, el índice del zip se valida (`_check_zip_entries`):
     una única `.app` raíz, sin rutas absolutas ni `..`, y todo symlink
     resuelto dentro de esa `.app`. La firma de (3) solo cubre la `.app`;
     sin (4), un zip con entradas extra podría escribir fuera del directorio
     temporal durante la extracción, antes de verificar nada.

La comprobación funciona también desde el código fuente; la instalación
automática solo en la `.app` empaquetada (`paths.is_bundled()`).
"""

import hashlib
import json
import os
import plistlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
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


def _run(cmd):
    """subprocess.run con el motivo real del fallo si el comando falla.

    `check=True` por sí solo solo da el returncode: para diagnosticar hace
    falta el stderr/stdout del propio comando.
    """
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"{cmd[0]} falló: {detail or f'exit {result.returncode}'}")
    return result


def _verify_app_signature(app_path):
    """codesign estricto + spctl (notarización) + TeamIdentifier esperado."""
    _run(["/usr/bin/codesign", "--verify", "--strict", "--deep", str(app_path)])
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


_MAX_SYMLINK_DEPTH = 40
# `ditto -c -k` puede guardar metadatos AppleDouble aquí; nunca se instala.
_ZIP_METADATA_ROOT = "__MACOSX"


def _virtual_realpath(parts, links, depth=0):
    """Resuelve `parts` sobre el árbol del zip siguiendo sus symlinks.

    Igual que `os.path.realpath`, pero sin tocar disco: así se sabe a dónde
    apuntaría cada enlace *antes* de que `ditto` lo cree. Devuelve None si la
    ruta sube por encima de la raíz del archivo.
    """
    if depth > _MAX_SYMLINK_DEPTH:
        raise RuntimeError("Cadena de symlinks demasiado larga en la actualización")
    resolved = []
    for comp in parts:
        if comp in ("", "."):
            continue
        if comp == "..":
            if not resolved:
                return None
            resolved.pop()
            continue
        resolved.append(comp)
        target = links.get("/".join(resolved))
        if target is None:
            continue
        if target.startswith("/"):
            return None
        resolved = _virtual_realpath(resolved[:-1] + target.split("/"), links, depth + 1)
        if resolved is None:
            return None
    return resolved


def _check_zip_entries(zip_path):
    """Valida el índice del zip antes de extraerlo; devuelve el nombre de la `.app`."""
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        raise RuntimeError(f"El paquete de actualización no es un zip válido: {exc}") from exc
    with zf:
        infos = zf.infolist()
        entries, links = [], {}
        for info in infos:
            name = info.filename
            if not name or "\\" in name or any(ord(c) < 32 for c in name):
                raise RuntimeError(f"Entrada no válida en la actualización: {name!r}")
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts:
                raise RuntimeError(f"Ruta fuera del paquete en la actualización: {name!r}")
            parts = [p for p in path.parts if p != "."]
            if not parts:
                continue
            entries.append(parts)
            if stat.S_ISLNK(info.external_attr >> 16):
                if parts[0] == _ZIP_METADATA_ROOT:
                    raise RuntimeError(f"Symlink no permitido en la actualización: {name!r}")
                links["/".join(parts)] = zf.read(info).decode("utf-8", "strict")
        roots = {parts[0] for parts in entries} - {_ZIP_METADATA_ROOT}
        if len(roots) != 1 or not next(iter(roots)).endswith(".app"):
            raise RuntimeError("El paquete de actualización debe contener una única .app en la raíz")
        root = next(iter(roots))

        def inside(parts):
            return parts is not None and len(parts) >= 1 and parts[0] == root

        for link, target in links.items():
            link_parts = link.split("/")
            if target.startswith("/") or not inside(_virtual_realpath(link_parts[:-1] + target.split("/"), links)):
                raise RuntimeError(f"Symlink que sale de la .app en la actualización: {link!r} -> {target!r}")
        for parts in entries:
            # Una entrada se escribe en el directorio real de su padre: si el
            # padre pasa por un symlink, debe seguir dentro de su raíz.
            if parts[0] == _ZIP_METADATA_ROOT:
                continue
            parent = _virtual_realpath(parts[:-1], links)
            if not inside(parent) and parts[:-1]:
                raise RuntimeError(f"Entrada escrita fuera de la .app: {'/'.join(parts)!r}")
    return root


def _check_extracted_links(app_path):
    """Segunda barrera tras extraer: ningún symlink real sale de la `.app`."""
    root = os.path.realpath(app_path)
    for dirpath, dirnames, filenames in os.walk(app_path):
        for name in dirnames + filenames:
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                real = os.path.realpath(full)
                if real != root and not real.startswith(root + os.sep):
                    raise RuntimeError(f"Symlink que sale de la .app tras extraer: {full}")


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
    app_name = _check_zip_entries(zip_path)
    extract_dir = tmp / "extracted"
    # `ditto`, no `zipfile`: el zip lo genera `build_app.sh` con
    # `ditto -c -k --keepParent`, que preserva symlinks (p.ej. el framework
    # de Python, lleno de `Versions/Current -> 3.x`), atributos extendidos y
    # resource forks. El módulo `zipfile` de Python no reconstruye symlinks
    # (los deja como archivos regulares con el texto del destino dentro), lo
    # que descuadra el bundle frente a lo firmado y `codesign --verify`
    # falla. `ditto -x -k` es el extractor simétrico de `ditto -c -k`.
    #
    # `ditto` puede fallar de forma puntual creando algún symlink (fallo
    # transitorio de filesystem); un solo reintento, limpiando el directorio
    # de extracción antes de repetir, resuelve ese caso sin exponerlo al
    # usuario como un error de actualización.
    extract_error = None
    for attempt in range(2):
        if extract_dir.exists():
            shutil.rmtree(extract_dir, ignore_errors=True)
        extract_dir.mkdir(parents=True, exist_ok=True)
        try:
            _run(["/usr/bin/ditto", "-x", "-k", str(zip_path), str(extract_dir)])
            extract_error = None
            break
        except RuntimeError as exc:
            extract_error = exc
    if extract_error is not None:
        raise extract_error
    app_path = extract_dir / app_name
    if app_path.is_symlink() or not app_path.is_dir():
        raise RuntimeError("El paquete de actualización no contiene ninguna .app")
    _check_extracted_links(app_path)
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
