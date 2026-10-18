"""Clave Ed25519 que firma `latest.json` (ADR-013, addendum firma del manifiesto).

  build-venv/bin/python macos/sign_manifest.py keygen  RUTA.pem   # una vez; imprime la clave pública
  build-venv/bin/python macos/sign_manifest.py check   RUTA.pem   # ¿coincide con updater.UPDATE_PUBLIC_KEYS?
  build-venv/bin/python macos/sign_manifest.py sign    RUTA.pem dist/latest.json   # -> dist/latest.json.sig

`build-venv` lo crea `build_app.sh` (lleva `cryptography`, como la app).
La clave privada es un PEM PKCS#8 sin cifrar con permisos 600, fuera del repo.
Guárdala con copia de seguridad: sin ella, las versiones que ya verifican la
firma no pueden recibir más actualizaciones (habría que reinstalar a mano).
"""

import base64
import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
except ImportError:
    raise SystemExit("Falta 'cryptography'. Usa el Python del entorno de build:\n"
                     "  build-venv/bin/python macos/sign_manifest.py …\n"
                     "(o: python3 -m pip install -r requirements.txt)")

import updater  # noqa: E402


def _public_hex(private_key):
    raw = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return raw.hex()


def load_key(path):
    path = Path(path).expanduser()
    mode = path.stat().st_mode
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise SystemExit(f"{path}: la clave privada no debe ser legible por otros (chmod 600)")
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise SystemExit(f"{path}: no es una clave Ed25519")
    return key


def keygen(path):
    path = Path(path).expanduser()
    if path.exists():
        raise SystemExit(f"{path} ya existe; no se sobrescribe")
    path.parent.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(pem)
    print(f"Clave privada: {path}")
    print("Clave pública (va en updater.UPDATE_PUBLIC_KEYS):")
    print(_public_hex(key))


def check(path):
    public = _public_hex(load_key(path))
    if public not in updater.UPDATE_PUBLIC_KEYS:
        raise SystemExit(
            f"La clave de {path} ({public}) no está en updater.UPDATE_PUBLIC_KEYS: "
            "la app no aceptaría el manifiesto firmado con ella.")
    print(f"    OK, clave pública {public[:16]}…")


def sign(path, manifest):
    key = load_key(path)
    manifest = Path(manifest)
    raw = manifest.read_bytes()
    signature = base64.b64encode(key.sign(updater.MANIFEST_SIG_CONTEXT + raw)).decode("ascii")
    # Misma verificación que hará la app instalada.
    updater.verify_manifest_signature(raw, signature)
    out = manifest.with_name(manifest.name + ".sig")
    out.write_text(signature + "\n", encoding="ascii")
    print(f"    OK, {out}")


def main(argv):
    commands = {"keygen": (keygen, 1), "check": (check, 1), "sign": (sign, 2)}
    if len(argv) < 2 or argv[1] not in commands or len(argv) - 2 != commands[argv[1]][1]:
        raise SystemExit(__doc__)
    func, _ = commands[argv[1]]
    func(*argv[2:])


if __name__ == "__main__":
    main(sys.argv)
