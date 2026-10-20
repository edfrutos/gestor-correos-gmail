#!/usr/bin/env bash
# Build de la Mac App Store (Fase 35, ADR-015): App Sandbox, sin Sparkle ni
# updater propio, firmada para la tienda y empaquetada como .pkg para subirla
# a App Store Connect. Ejecutar en un Mac, desde la raíz del repositorio:
#
#   PYTHON=/usr/local/bin/python3.12 bash macos/build_mas.sh
#
# Variables (entorno o macos/build.env, gitignoreado). Pasos para obtener cada
# una en docs/MAC_APP_STORE.md:
#   MAS_APP_IDENTITY="Apple Distribution: Nombre (V29BTBRY6G)"
#   MAS_INSTALLER_IDENTITY="3rd Party Mac Developer Installer: Nombre (V29BTBRY6G)"
#   MAS_PROFILE="$HOME/.config/gestor-correos/GestorDeCorreos_MAS.provisionprofile"
#   MAS_OAUTH_CLIENT=".../credentials.json"   # opcional: cliente OAuth que lleva la app
#   MAS_BUILD_NUMBER=2                         # opcional: CFBundleVersion (por defecto VERSION)
#
# Prueba local del sandbox, sin perfil ni App Store Connect (firma con tu
# Developer ID, sin .pkg; la .app resultante se abre con doble clic):
#
#   MAS_LOCAL=1 PYTHON=/usr/local/bin/python3.12 bash macos/build_mas.sh

set -euo pipefail

APP_NAME="Gestor de Correos"
BUNDLE_ID="com.edefrutos.gestorcorreos"
TEAM_ID="V29BTBRY6G"
DIST="dist-mas"
BUNDLE="${DIST}/${APP_NAME}.app"
ENTITLEMENTS="macos/entitlements-mas.plist"
ENTITLEMENTS_INHERIT="macos/entitlements-mas-inherit.plist"
PYTHON="${PYTHON:-python3}"
VERSION="$(cat VERSION)"
MAS_LOCAL="${MAS_LOCAL:-}"

[ -f macos/build.env ] && . macos/build.env

require() { [ -n "${!1:-}" ] || { echo "Falta la variable: $1 (exporta o ponla en macos/build.env)" >&2; exit 1; }; }
if [ -n "${MAS_LOCAL}" ]; then
  require DEV_ID_APP
  SIGN_IDENTITY="${DEV_ID_APP}"
else
  require MAS_APP_IDENTITY
  require MAS_INSTALLER_IDENTITY
  require MAS_PROFILE
  SIGN_IDENTITY="${MAS_APP_IDENTITY}"
  [ -f "${MAS_PROFILE}" ] || { echo "No existe MAS_PROFILE: ${MAS_PROFILE}" >&2; exit 1; }
fi
BUNDLE_VERSION="${MAS_BUILD_NUMBER:-${VERSION}}"
PKG="${DIST}/GestorDeCorreos-${VERSION}-${BUNDLE_VERSION}.pkg"

BUILD_COMMIT="$(git rev-parse HEAD)"
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "AVISO: hay cambios sin commitear; el build no corresponderá a ${BUILD_COMMIT:0:7}." >&2
fi

WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

echo "==> 1/8  Entorno de build  (PYTHON=${PYTHON})"
# Igual que build_app.sh 1/9 y 2/9 (mismo build-venv).
"${PYTHON}" -c 'import sysconfig,sys; sys.exit(0 if sysconfig.get_config_var("PYTHONFRAMEWORK") else 1)' \
    || echo "AVISO: ${PYTHON} no parece un framework build; py2app puede fallar." >&2
"${PYTHON}" -m venv build-venv
build-venv/bin/python -m pip install --upgrade pip wheel
build-venv/bin/python -m pip install -r requirements.txt -r requirements-macos.txt
find build-venv -type d -path '*/site-packages/google' -print0 2>/dev/null \
  | while IFS= read -r -d '' d; do
      [ -f "$d/__init__.py" ] || : > "$d/__init__.py"
    done
if [ -d macos/AppIcon.iconset ] && command -v iconutil >/dev/null 2>&1; then
  iconutil -c icns macos/AppIcon.iconset -o macos/AppIcon.icns
fi

echo "==> 2/8  Perfil de aprovisionamiento y entitlements"
if [ -n "${MAS_LOCAL}" ]; then
  # Sin perfil, macOS no deja lanzar una app con application-identifier: se quitan.
  cp "${ENTITLEMENTS}" "${WORK}/entitlements.plist"
  /usr/libexec/PlistBuddy -c "Delete :com.apple.application-identifier" "${WORK}/entitlements.plist"
  /usr/libexec/PlistBuddy -c "Delete :com.apple.developer.team-identifier" "${WORK}/entitlements.plist"
  ENTITLEMENTS="${WORK}/entitlements.plist"
  echo "    MAS_LOCAL: sandbox con tu Developer ID, sin perfil"
else
  security cms -D -i "${MAS_PROFILE}" > "${WORK}/profile.plist"
  PROFILE_APP_ID="$(/usr/libexec/PlistBuddy -c 'Print :Entitlements:com.apple.application-identifier' "${WORK}/profile.plist")"
  [ "${PROFILE_APP_ID}" = "${TEAM_ID}.${BUNDLE_ID}" ] \
    || { echo "El perfil es para ${PROFILE_APP_ID}, no para ${TEAM_ID}.${BUNDLE_ID}" >&2; exit 1; }
  if /usr/libexec/PlistBuddy -c 'Print :ProvisionedDevices' "${WORK}/profile.plist" >/dev/null 2>&1; then
    echo "El perfil es de desarrollo (lista dispositivos); hace falta uno de distribución «Mac App Store Connect»." >&2
    exit 1
  fi
  echo "    perfil OK: ${PROFILE_APP_ID}"
fi

echo "==> 3/8  py2app (variante Mac App Store, CFBundleVersion ${BUNDLE_VERSION})"
rm -rf build "${DIST}"
GESTOR_DISTRIBUTION=mas GESTOR_BUNDLE_VERSION="${BUNDLE_VERSION}" \
    build-venv/bin/python macos/setup.py py2app --dist-dir "${DIST}"

echo "==> 4/8  Recursos de la variante"
RES="${BUNDLE}/Contents/Resources"
echo "mas" > "${RES}/DISTRIBUTION"   # paths.is_app_store()
if [ -n "${MAS_OAUTH_CLIENT:-}" ]; then
  build-venv/bin/python - "${MAS_OAUTH_CLIENT}" <<'PY'
import json, sys
client = json.load(open(sys.argv[1], encoding="utf-8")).get("installed") or {}
if not (client.get("client_id") and client.get("client_secret")):
    sys.exit("MAS_OAUTH_CLIENT no es un cliente OAuth de tipo «App de escritorio»")
PY
  cp "${MAS_OAUTH_CLIENT}" "${RES}/oauth_client.json"
  echo "    cliente OAuth incluido (app_main.install_bundled_oauth_client)"
else
  echo "    AVISO: sin MAS_OAUTH_CLIENT; cada usuario tendrá que importar su credentials.json." >&2
fi
# Bundles .app anidados (Python.app de Python.framework): py2app no los usa y
# la tienda exige firmar con sandbox todo ejecutable que haya en la app.
find "${BUNDLE}/Contents/Frameworks" -type d -name '*.app' -prune -print0 2>/dev/null \
  | while IFS= read -r -d '' nested; do echo "    fuera: ${nested#"${BUNDLE}"/}"; rm -rf "${nested}"; done
if [ -z "${MAS_LOCAL}" ]; then
  cp "${MAS_PROFILE}" "${BUNDLE}/Contents/embedded.provisionprofile"
fi

echo "==> 5/8  Firmar binarios anidados (inside-out)"
sign_plain() { codesign --force --timestamp --sign "${SIGN_IDENTITY}" "$1"; }
sign_inherit() { codesign --force --timestamp --entitlements "${ENTITLEMENTS_INHERIT}" --sign "${SIGN_IDENTITY}" "$1"; }
find "${BUNDLE}/Contents" -type f \( -name '*.so' -o -name '*.dylib' \) -print0 \
  | while IFS= read -r -d '' f; do sign_plain "$f"; done
find "${BUNDLE}/Contents" -type d -name '*.framework' -print0 \
  | while IFS= read -r -d '' fw; do sign_plain "$fw"; done
MAIN_EXE="$(basename "${BUNDLE%.app}")"
find "${BUNDLE}/Contents/MacOS" -type f -print0 \
  | while IFS= read -r -d '' f; do
      if [ "$(basename "$f")" = "${MAIN_EXE}" ]; then continue; fi
      if file "$f" | grep -q 'Mach-O'; then sign_inherit "$f"; fi
    done

echo "==> 6/8  Firmar el bundle (App Sandbox)"
codesign --force --timestamp --entitlements "${ENTITLEMENTS}" --sign "${SIGN_IDENTITY}" "${BUNDLE}"
codesign --verify --deep --strict --verbose=2 "${BUNDLE}"
codesign -d --entitlements - "${BUNDLE}" 2>/dev/null | grep -q 'com.apple.security.app-sandbox' \
  || { echo "La .app firmada no lleva com.apple.security.app-sandbox" >&2; exit 1; }
if [ -d "${BUNDLE}/Contents/Frameworks/Sparkle.framework" ]; then
  echo "La variante de la Mac App Store no puede llevar Sparkle" >&2; exit 1
fi

if [ -n "${MAS_LOCAL}" ]; then
  echo
  echo "Listo (prueba local del sandbox): ${BUNDLE}"
  echo "  open \"${BUNDLE}\""
  echo "  Datos en ~/Library/Containers/${BUNDLE_ID}/Data/Library/Application Support/GestorDeCorreos/"
  exit 0
fi

echo "==> 7/8  .pkg firmado para App Store Connect"
productbuild --component "${BUNDLE}" /Applications --sign "${MAS_INSTALLER_IDENTITY}" "${PKG}"
pkgutil --check-signature "${PKG}"

echo "==> 8/8  Validación con App Store Connect (opcional)"
if [ -n "${MAS_API_KEY:-}" ] && [ -n "${MAS_API_ISSUER:-}" ]; then
  xcrun altool --validate-app -f "${PKG}" -t macos --apiKey "${MAS_API_KEY}" --apiIssuer "${MAS_API_ISSUER}"
else
  echo "    (sin MAS_API_KEY/MAS_API_ISSUER: valida al subirlo con Transporter)"
fi

echo
echo "Listo: ${PKG}  (v${VERSION}, build ${BUNDLE_VERSION}, commit ${BUILD_COMMIT:0:7})"
echo
echo "Subir a App Store Connect:"
echo "  - Transporter (Mac App Store): arrastra el .pkg y pulsa Entregar, o"
echo "  - xcrun altool --upload-app -f \"${PKG}\" -t macos --apiKey <KEY_ID> --apiIssuer <ISSUER_ID>"
echo "Después: App Store Connect → TestFlight para probarla, y Enviar a revisión."
