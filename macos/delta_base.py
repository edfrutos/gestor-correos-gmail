"""Descarga y verifica la versión publicada, base del delta de Sparkle (Fase 38).

  build-venv/bin/python macos/delta_base.py <VERSION_NUEVA> dist/delta-base/base.zip

Lee el `appcast.xml` del último Release (`updater.SPARKLE_FEED_URL`), descarga
el `.zip` al que apunta y comprueba su longitud y su `sparkle:edSignature` con
`updater.sparkle_public_key()`: el delta solo se construye sobre lo que Sparkle
aceptaría como esa versión. Escribe el zip en la ruta indicada e imprime la
versión anterior en stdout.

Salida: 0 = base lista · 2 = sin base (no hay Release anterior, la publicada no
es menor o falla la red), `build_app.sh` sigue sin delta · 1 = el Release
publicado no casa con su firma: hay que mirarlo antes de publicar nada.
"""

import base64
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cryptography.exceptions import InvalidSignature  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey  # noqa: E402

import updater  # noqa: E402
from make_appcast import REPO_URL  # noqa: E402

SPARKLE_NS = "{http://www.andymatuschak.org/xml-namespaces/sparkle}"
NO_BASE = 2


class NoBase(Exception):
    """No hay versión anterior utilizable; el build sigue sin delta."""


def parse_feed(raw):
    """(versión, url, longitud, firma) del primer `<item>` del appcast."""
    try:
        item = ET.fromstring(raw).find("channel/item")
    except ET.ParseError as exc:
        raise NoBase(f"appcast.xml publicado no es XML válido: {exc}")
    if item is None or item.find("enclosure") is None:
        raise NoBase("appcast.xml publicado no tiene <item> con <enclosure>")
    enclosure = item.find("enclosure")
    version = (item.findtext(f"{SPARKLE_NS}version") or "").strip()
    try:
        length = int(enclosure.get("length", ""))
    except ValueError:
        raise NoBase("appcast.xml publicado sin longitud válida")
    return version, enclosure.get("url", ""), length, enclosure.get(f"{SPARKLE_NS}edSignature", "")


def check_base(feed_raw, new_version):
    """Valida el feed publicado frente a la versión que se compila; devuelve sus datos."""
    version, url, length, signature = parse_feed(feed_raw)
    if not version or updater.parse_version(version) >= updater.parse_version(new_version):
        raise NoBase(f"la versión publicada ({version or '?'}) no es anterior a {new_version}")
    # Solo assets del propio repo y de su tag: el feed no decide de dónde se descarga.
    if not url.startswith(f"{REPO_URL}/releases/download/v{version}/"):
        raise SystemExit(f"URL inesperada en el appcast publicado: {url}")
    return version, url, length, signature


def verify_archive(data, length, signature):
    """Misma comprobación que hace Sparkle antes de aceptar el zip."""
    if len(data) != length:
        raise SystemExit(f"El zip publicado mide {len(data)} bytes y el appcast dice {length}")
    public = Ed25519PublicKey.from_public_bytes(base64.b64decode(updater.sparkle_public_key()))
    try:
        public.verify(base64.b64decode(signature, validate=True), data)
    except (InvalidSignature, ValueError):
        raise SystemExit("La firma del zip publicado no es válida: no se construye el delta")


def main(argv, http_get=updater._http_get):
    if len(argv) != 3:
        raise SystemExit(__doc__)
    new_version, out = argv[1:]
    try:
        try:
            feed = http_get(updater.SPARKLE_FEED_URL, binary=True)
        except OSError as exc:
            raise NoBase(f"no se pudo leer el appcast publicado: {exc}")
        version, url, length, signature = check_base(feed, new_version)
        try:
            data = http_get(url, binary=True)
        except OSError as exc:
            raise NoBase(f"no se pudo descargar {url}: {exc}")
    except NoBase as exc:
        print(f"    sin delta: {exc}", file=sys.stderr)
        return NO_BASE
    verify_archive(data, length, signature)
    Path(out).write_bytes(data)
    print(f"    base del delta: v{version} ({length} bytes, firma OK)", file=sys.stderr)
    print(version)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
