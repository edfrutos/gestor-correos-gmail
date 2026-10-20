#!/usr/bin/env bash
# Comprueba que py2app ha metido en el .app los módulos nativos que se cargan
# de forma dinámica (modulegraph no los ve). Sin ellos la app solo arranca si
# el usuario tiene esos paquetes en su propio Python. Uso:
#   bash macos/check_bundle.sh "dist/Gestor de Correos.app"
set -euo pipefail

BUNDLE="$1"
DYNLOAD="$(ls -d "${BUNDLE}"/Contents/Resources/lib/python3.*/lib-dynload 2>/dev/null | head -1 || true)"
[ -n "${DYNLOAD}" ] || { echo "No encuentro lib-dynload en ${BUNDLE}" >&2; exit 1; }
REQUIRED=(
  "_cffi_backend.so"                          # cryptography -> updater
  "cryptography/hazmat/bindings/_rust.so"
)
missing=0
for mod in "${REQUIRED[@]}"; do
  if [ ! -f "${DYNLOAD}/${mod}" ]; then
    echo "Falta en el bundle: lib-dynload/${mod}" >&2
    missing=1
  fi
done
[ "${missing}" -eq 0 ] || { echo "Revisa los includes de macos/setup.py." >&2; exit 1; }
echo "    bundle OK: módulos nativos dinámicos presentes"
