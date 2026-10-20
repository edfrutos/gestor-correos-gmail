"""Buscar, descargar e instalar actualizaciones de la app macOS.

Modelo de confianza (cualquier fallo aborta la instalación):
  1. `latest.json` se descarga por HTTPS de GitHub Releases y se verifica su
     firma Ed25519 (`latest.json.sig`) con la clave pública embebida
     (`UPDATE_PUBLIC_KEYS`). Así ni la versión, ni la url, ni el sha256
     dependen de quien pueda publicar assets en el Release.
  2. El `.zip` se verifica por sha256 contra el manifiesto (integridad).
  3. El `.app` extraído se verifica con `codesign --verify --strict`, `spctl`
     (notarización) y se comprueba que el `TeamIdentifier` es el nuestro
     (autenticidad). Sin (3), un manifiesto manipulado permitiría ejecutar
     código arbitrario.
  4. El zip lo valida (`_check_zip_entries`) y lo extrae (`_extract_zip`) el
     mismo código, con el mismo parser: una única `.app` raíz, sin rutas
     absolutas ni `..`, sin nombres repetidos, ninguna entrada bajo un
     symlink y todo symlink resuelto dentro de la `.app`. La firma de (3) solo
     cubre la `.app`; sin (4), un zip con entradas extra podría escribir fuera
     del directorio temporal durante la extracción, antes de verificar nada.

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
import unicodedata
import zipfile
from base64 import b64decode
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

import paths

APP_VERSION_FALLBACK = "0.0.0"
EXPECTED_TEAM_ID = "V29BTBRY6G"
DEFAULT_MANIFEST_URL = (
    "https://github.com/edfrutos/gestor-correos-gmail/releases/latest/download/latest.json"
)
# Claves públicas Ed25519 (hex, 32 bytes) que firman `latest.json`. La privada
# no está en el repo: la usa `macos/sign_manifest.py` desde `build_app.sh`.
# Se admite más de una para poder rotar: un Release firmado con la clave vieja
# puede traer ya la nueva en esta tupla.
UPDATE_PUBLIC_KEYS = (
    "39a604179dc5b892e40bce062513c09faa5e0ac584b8be52461ec021312a3035",
)
# Separación de dominio: la firma solo vale para este manifiesto.
MANIFEST_SIG_CONTEXT = b"gestor-correos/latest.json/v1\n"
# Sparkle (desde v1.3.0, ADR-014) usa la misma clave Ed25519: firma los bytes
# del .zip sin contexto, y como un zip empieza por "PK\x03\x04" y nunca por
# MANIFEST_SIG_CONTEXT, ninguna de las dos firmas sirve para la otra.
SPARKLE_FEED_URL = (
    "https://github.com/edfrutos/gestor-correos-gmail/releases/latest/download/appcast.xml"
)


def sparkle_public_key():
    """`SUPublicEDKey` del Info.plist: la clave pública en base64 (formato Sparkle)."""
    from base64 import b64encode
    return b64encode(bytes.fromhex(UPDATE_PUBLIC_KEYS[0])).decode("ascii")
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


def signature_url(url=None):
    return (url or manifest_url()) + ".sig"


def verify_manifest_signature(raw, signature, public_keys=None):
    """Verifica la firma Ed25519 (base64) de los bytes exactos de `latest.json`.

    Lanza RuntimeError si no la firma ninguna de `public_keys`.
    """
    keys = UPDATE_PUBLIC_KEYS if public_keys is None else public_keys
    if not keys:
        raise RuntimeError("No hay clave pública configurada para verificar actualizaciones")
    try:
        sig = b64decode(signature.strip(), validate=True)
    except Exception:
        sig = b""
    if len(sig) != 64:
        raise RuntimeError("La firma del manifiesto de actualización no es válida")
    for key in keys:
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(key)).verify(sig, MANIFEST_SIG_CONTEXT + raw)
            return
        except InvalidSignature:
            continue
    raise RuntimeError("La firma del manifiesto de actualización no es válida")


def fetch_manifest():
    url = manifest_url()
    raw = _http_get(url, binary=True)
    try:
        signature = _http_get(signature_url(url))
    except HTTPError as exc:
        # Distinto del 404 del manifiesto ("aún no hay versión publicada").
        raise RuntimeError(f"No se pudo obtener la firma del manifiesto (HTTP {exc.code})") from exc
    verify_manifest_signature(raw, signature)
    manifest = json.loads(raw.decode("utf-8"))
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
# Metadatos AppleDouble de algunos zips de macOS: se ignoran, nunca se extraen.
_ZIP_METADATA_ROOT = "__MACOSX"
# El zip real ronda los 50 MB comprimido; muy por encima de lo descomprimido.
_MAX_UNCOMPRESSED = 2 * 1024 ** 3


def _fs_key(component):
    """Forma canónica de un componente de ruta tal como lo compara APFS.

    APFS (por defecto) no distingue mayúsculas ni formas de normalización
    Unicode: `la`, `LA` y `la` en NFC/NFD son la misma entrada en disco.
    Toda la validación trabaja con esta forma para no ver dos rutas donde
    el disco tiene una sola.
    """
    return unicodedata.normalize("NFD", unicodedata.normalize("NFD", component).casefold())


def _virtual_realpath(parts, links, depth=0):
    """Resuelve `parts` sobre el árbol del zip siguiendo sus symlinks.

    Igual que `os.path.realpath`, pero sin tocar disco: así se sabe a dónde
    apuntaría cada enlace *antes* de crearlo. Devuelve None si la
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
    """Valida el índice del zip antes de extraerlo; devuelve el nombre de la `.app`.

    Solo tiene sentido junto con `_extract_zip`, que extrae con este mismo
    parser y estas mismas rutas: validar con uno y extraer con otro (p. ej.
    `ditto`) deja huecos en cada diferencia de interpretación del formato.
    """
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        raise RuntimeError(f"El paquete de actualización no es un zip válido: {exc}") from exc
    with zf:
        # Todo en forma canónica (`_fs_key`); `seen` rechaza nombres repetidos:
        # las entradas se aplican en orden, así que un mismo nombre dos veces
        # (p. ej. un symlink que sale de la .app, un fichero escrito a través
        # de él y luego otro symlink inocuo encima) haría que el árbol final
        # validado no fuese el que se escribió.
        entries, links, seen = [], {}, set()
        root_name = None
        for info in zf.infolist():
            name = info.filename
            if not name or "\\" in name or any(ord(c) < 32 for c in name):
                raise RuntimeError(f"Entrada no válida en la actualización: {name!r}")
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts:
                raise RuntimeError(f"Ruta fuera del paquete en la actualización: {name!r}")
            raw_parts = [p for p in path.parts if p != "."]
            if not raw_parts:
                continue
            parts = [_fs_key(p) for p in raw_parts]
            key = "/".join(parts)
            if key in seen:
                raise RuntimeError(f"Entrada duplicada en la actualización: {name!r}")
            seen.add(key)
            entries.append(parts)
            if parts[0] != _fs_key(_ZIP_METADATA_ROOT) and root_name is None:
                root_name = raw_parts[0]
            if stat.S_ISLNK(info.external_attr >> 16):
                if parts[0] == _fs_key(_ZIP_METADATA_ROOT):
                    raise RuntimeError(f"Symlink no permitido en la actualización: {name!r}")
                target = zf.read(info).decode("utf-8", "strict")
                if target.startswith("/"):
                    raise RuntimeError(f"Symlink que sale de la .app en la actualización: {name!r} -> {target!r}")
                links[key] = "/".join(_fs_key(c) for c in target.split("/"))
        roots = {parts[0] for parts in entries} - {_fs_key(_ZIP_METADATA_ROOT)}
        if len(roots) != 1 or not next(iter(roots)).endswith(".app"):
            raise RuntimeError("El paquete de actualización debe contener una única .app en la raíz")
        root = next(iter(roots))

        if sum(info.file_size for info in zf.infolist()) > _MAX_UNCOMPRESSED:
            raise RuntimeError("El paquete de actualización es demasiado grande al descomprimir")

        def inside(parts):
            return parts is not None and len(parts) >= 1 and parts[0] == root

        for parts in entries:
            # `_extract_zip` crea los symlinks al final; nada debe colgar de
            # uno (ditto tampoco guarda contenido "a través" de un enlace).
            for i in range(1, len(parts)):
                if "/".join(parts[:i]) in links:
                    raise RuntimeError(f"Entrada bajo un symlink en la actualización: {'/'.join(parts)!r}")

        for link, target in links.items():
            link_parts = link.split("/")
            if not inside(_virtual_realpath(link_parts[:-1] + target.split("/"), links)):
                raise RuntimeError(f"Symlink que sale de la .app en la actualización: {link!r} -> {target!r}")
        for parts in entries:
            # Una entrada se escribe en el directorio real de su padre: si el
            # padre pasa por un symlink, debe seguir dentro de su raíz.
            if parts[0] == _fs_key(_ZIP_METADATA_ROOT):
                continue
            parent = _virtual_realpath(parts[:-1], links)
            if not inside(parent) and parts[:-1]:
                raise RuntimeError(f"Entrada escrita fuera de la .app: {'/'.join(parts)!r}")
    return root_name


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


def _extract_zip(zip_path, dest):
    """Extrae el zip ya validado por `_check_zip_entries`, sin `ditto`.

    Reproduce lo que `ditto -x -k` hacía con el zip de `build_app.sh`
    (`ditto -c -k --keepParent`: ficheros, carpetas, permisos y symlinks como
    `Versions/Current -> 3.12`; sin xattrs ni AppleDouble), pero con el mismo
    parser que la validación. `zipfile.extractall` no sirve: no recrea
    symlinks y descuadra el bundle frente a lo firmado.

    Los ficheros se crean con `O_EXCL|O_NOFOLLOW` y los symlinks al final,
    así ninguna escritura atraviesa un enlace.
    """
    dest = Path(dest)
    links = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            parts = [p for p in PurePosixPath(info.filename).parts if p != "."]
            if not parts or _fs_key(parts[0]) == _fs_key(_ZIP_METADATA_ROOT):
                continue
            out = dest.joinpath(*parts)
            mode = (info.external_attr >> 16) & 0o7777
            kind = stat.S_IFMT(info.external_attr >> 16)
            if kind == stat.S_IFLNK:
                links.append((out, zf.read(info).decode("utf-8", "strict")))
                continue
            if info.is_dir() or kind == stat.S_IFDIR:
                out.mkdir(parents=True, exist_ok=True)
                if mode:
                    os.chmod(out, (mode & 0o777) | 0o700)
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as fh, zf.open(info) as src:
                shutil.copyfileobj(src, fh, 1 << 20)
            # Sin setuid/setgid/sticky: el bundle no los necesita.
            os.chmod(out, (mode & 0o777) or 0o644)
    for out, target in links:
        out.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(target, out)


def _check_not_downgrade(app_path):
    """Rechaza una `.app` que no sea más nueva que la instalada.

    Se lee del `Info.plist` ya extraído, que la firma sella: un Release
    comprometido puede servir una `.app` antigua legítima con un
    `latest.json` que diga otra versión, pero no puede cambiar la que
    lleva dentro sin romper la firma (ADR-013).
    """
    try:
        data = plistlib.loads((app_path / "Contents" / "Info.plist").read_bytes())
        new = str(data["CFBundleShortVersionString"])
    except Exception as exc:
        raise RuntimeError(f"No se pudo leer la versión del paquete: {exc}") from exc
    current = current_version()
    if parse_version(new) <= parse_version(current):
        raise RuntimeError(f"El paquete es v{new} y no es más nuevo que la v{current} instalada")


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
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True)
    _extract_zip(zip_path, extract_dir)
    app_path = extract_dir / app_name
    if app_path.is_symlink() or not app_path.is_dir():
        raise RuntimeError("El paquete de actualización no contiene ninguna .app")
    _check_extracted_links(app_path)
    _verify_app_signature(app_path)
    _check_not_downgrade(app_path)
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
