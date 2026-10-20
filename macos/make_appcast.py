"""Genera `dist/appcast.xml`, el feed de Sparkle (ADR-014).

  build-venv/bin/python macos/make_appcast.py RUTA.pem dist/GestorDeCorreos-<VERSION>.zip <VERSION> dist/appcast.xml

Firma el .zip con la misma clave Ed25519 que `latest.json` (`sparkle:edSignature`
= Ed25519 sobre los bytes del archivo, en base64, como `sign_update` de Sparkle)
y lo verifica con `updater.sparkle_public_key()`, que es el `SUPublicEDKey` que
lleva la app. Un solo `<item>`: Sparkle solo necesita la última versión.
"""

import base64
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey  # noqa: E402

import updater  # noqa: E402
from sign_manifest import load_key  # noqa: E402

REPO_URL = "https://github.com/edfrutos/gestor-correos-gmail"
MIN_SYSTEM_VERSION = "12.0"  # = LSMinimumSystemVersion de macos/setup.py


def sign_archive(key, archive_bytes):
    signature = key.sign(archive_bytes)
    # Misma verificación que hará Sparkle con el SUPublicEDKey embebido.
    public = Ed25519PublicKey.from_public_bytes(base64.b64decode(updater.sparkle_public_key()))
    public.verify(signature, archive_bytes)
    return base64.b64encode(signature).decode("ascii")


def build_appcast(version, archive_name, length, signature, pub_date=None):
    pub_date = pub_date or datetime.now(timezone.utc)
    url = f"{REPO_URL}/releases/download/v{version}/{archive_name}"
    notes = f"{REPO_URL}/releases/tag/v{version}"
    return f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle">
  <channel>
    <title>Gestor de Correos</title>
    <link>{escape(REPO_URL)}</link>
    <item>
      <title>{escape(version)}</title>
      <pubDate>{format_datetime(pub_date)}</pubDate>
      <sparkle:version>{escape(version)}</sparkle:version>
      <sparkle:shortVersionString>{escape(version)}</sparkle:shortVersionString>
      <sparkle:minimumSystemVersion>{MIN_SYSTEM_VERSION}</sparkle:minimumSystemVersion>
      <sparkle:releaseNotesLink>{escape(notes)}</sparkle:releaseNotesLink>
      <enclosure url={quoteattr(url)} length="{length}" type="application/octet-stream" sparkle:edSignature={quoteattr(signature)}/>
    </item>
  </channel>
</rss>
"""


def main(argv):
    if len(argv) != 5:
        raise SystemExit(__doc__)
    key_path, archive, version, out = argv[1:]
    archive = Path(archive)
    data = archive.read_bytes()
    xml = build_appcast(version, archive.name, len(data), sign_archive(load_key(key_path), data))
    Path(out).write_text(xml, encoding="utf-8")
    print(f"    OK, {out}")


if __name__ == "__main__":
    main(sys.argv)
