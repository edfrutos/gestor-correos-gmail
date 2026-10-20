#!/usr/bin/env bash
# Build + firma + notarización + DMG de la app macOS.
# Ejecutar en un Mac, desde la raíz del repositorio:
#
#   export DEV_ID_APP="Developer ID Application: Nombre Apellidos (TEAMID)"
#   export AC_PROFILE="gestor-notary"      # perfil guardado con notarytool store-credentials
#   PYTHON=/usr/local/bin/python3.12 bash macos/build_app.sh
#
# Requisitos: Xcode Command Line Tools, cuenta Apple Developer, certificado
# Developer ID Application en el llavero, y un perfil de notarytool:
#   xcrun notarytool store-credentials "gestor-notary" \
#       --apple-id "TU_APPLE_ID" --team-id "TEAMID" --password "APP-SPECIFIC-PASSWORD"
#
# PYTHON: py2app necesita un "framework build" de Python. El de Homebrew NO lo es
# y suele producir un .app que no arranca. Usa el instalador oficial de
# python.org o pyenv con PYTHON_CONFIGURE_OPTS="--enable-framework".

set -euo pipefail

APP_NAME="Gestor de Correos"
BUNDLE="dist/${APP_NAME}.app"
DMG="dist/GestorDeCorreos.dmg"
ENTITLEMENTS="macos/entitlements.plist"
PYTHON="${PYTHON:-python3}"
VERSION="$(cat VERSION)"
GH_REPO="${GH_REPO:-edfrutos/gestor-correos-gmail}"   # para las URLs de latest.json
UPDATE_ZIP="dist/GestorDeCorreos-${VERSION}.zip"
# Sparkle (ADR-014): versión fijada y verificada por sha256 del tarball oficial.
SPARKLE_VERSION="2.9.6"
SPARKLE_SHA256="52bf9e88cdd972fc0c81501377a880e90d47031bd8ca5462488f843e2609e192"
SPARKLE_CACHE="macos/.cache/sparkle-${SPARKLE_VERSION}"
BINARY_DELTA="${SPARKLE_CACHE}/bin/BinaryDelta"   # del mismo tarball (Fase 38)

# Credenciales: variables de entorno, o un macos/build.env local (gitignoreado)
#   DEV_ID_APP="Developer ID Application: Nombre (TEAMID)"
#   AC_PROFILE="gestor-notary"
#   UPDATE_SIGNING_KEY="$HOME/.config/gestor-correos/update_signing.pem"
#     (clave Ed25519 que firma latest.json; se crea una vez con
#      build-venv/bin/python macos/sign_manifest.py keygen <ruta>)
[ -f macos/build.env ] && . macos/build.env

require() { [ -n "${!1:-}" ] || { echo "Falta la variable: $1 (exporta o ponla en macos/build.env)" >&2; exit 1; }; }
require DEV_ID_APP
require AC_PROFILE
require UPDATE_SIGNING_KEY

# El tag del Release debe apuntar al commit que se compila (v1.2.0/v1.2.1 se
# crearon sin --target y quedaron sobre otro commit de main).
BUILD_COMMIT="$(git rev-parse HEAD)"
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "AVISO: hay cambios sin commitear; el build no corresponderá a ${BUILD_COMMIT:0:7}." >&2
fi

echo "==> 1/9  Entorno de build  (PYTHON=${PYTHON})"
"${PYTHON}" -c 'import sysconfig,sys; sys.exit(0 if sysconfig.get_config_var("PYTHONFRAMEWORK") else 1)' \
    || echo "AVISO: ${PYTHON} no parece un framework build; py2app puede fallar. Ver cabecera." >&2
"${PYTHON}" -m venv build-venv
build-venv/bin/python -m pip install --upgrade pip wheel
build-venv/bin/python -m pip install -r requirements.txt -r requirements-macos.txt
# Antes de compilar nada: la clave que firmará latest.json debe ser la que
# la app lleva embebida (updater.UPDATE_PUBLIC_KEYS).
build-venv/bin/python macos/sign_manifest.py check "${UPDATE_SIGNING_KEY}"

echo "==> 2/9  Convertir 'google' en paquete regular (para que no acabe en el zip)"
# protobuf/google-* usan namespace packages (sin __init__.py). py2app deja el .so
# de google._upb dentro de python3XX.zip y ahí no se puede firmar -> notarización
# falla. Añadiendo __init__.py, py2app lo trata como paquete y lo copia suelto.
find build-venv -type d -path '*/site-packages/google' -print0 2>/dev/null \
  | while IFS= read -r -d '' d; do
      [ -f "$d/__init__.py" ] || : > "$d/__init__.py"
    done

# Icono: regenera AppIcon.icns con iconutil (mejor que el fallback de Pillow) si
# está el iconset. Si no, se usa el macos/AppIcon.icns ya versionado.
if [ -d macos/AppIcon.iconset ] && command -v iconutil >/dev/null 2>&1; then
  iconutil -c icns macos/AppIcon.iconset -o macos/AppIcon.icns
  echo "    icono regenerado con iconutil"
fi

echo "==> 3/9  py2app"
rm -rf build dist
build-venv/bin/python macos/setup.py py2app
bash macos/check_bundle.sh "dist/${APP_NAME}.app"

echo "==> 3b/9 Sparkle.framework ${SPARKLE_VERSION} -> Contents/Frameworks"
if [ ! -d "${SPARKLE_CACHE}/Sparkle.framework" ] || [ ! -x "${BINARY_DELTA}" ]; then
  rm -rf "${SPARKLE_CACHE}"
  mkdir -p "${SPARKLE_CACHE}"
  TARBALL="${SPARKLE_CACHE}/Sparkle-${SPARKLE_VERSION}.tar.xz"
  curl -fsSL -o "${TARBALL}" \
    "https://github.com/sparkle-project/Sparkle/releases/download/${SPARKLE_VERSION}/Sparkle-${SPARKLE_VERSION}.tar.xz"
  echo "${SPARKLE_SHA256}  ${TARBALL}" | shasum -a 256 -c -
  tar -xJf "${TARBALL}" -C "${SPARKLE_CACHE}" ./Sparkle.framework ./bin/BinaryDelta
  rm -f "${TARBALL}"
fi
SPARKLE_FW="${BUNDLE}/Contents/Frameworks/Sparkle.framework"
mkdir -p "${BUNDLE}/Contents/Frameworks"
ditto "${SPARKLE_CACHE}/Sparkle.framework" "${SPARKLE_FW}"
# Los XPC services solo los usa una app con App Sandbox; esta no lo tiene.
rm -rf "${SPARKLE_FW}/Versions/B/XPCServices" "${SPARKLE_FW}/XPCServices"

echo "==> 4/9  Firmar binarios anidados (inside-out, Hardened Runtime + timestamp)"
sign_one() { codesign --force --options runtime --timestamp --sign "${DEV_ID_APP}" "$1"; }
export -f sign_one
export DEV_ID_APP
# .so y .dylib: los más numerosos, se firman todos.
find "${BUNDLE}/Contents" -type f \( -name '*.so' -o -name '*.dylib' \) -print0 \
  | while IFS= read -r -d '' f; do sign_one "$f"; done
# Sparkle: sus ejecutables internos antes que el framework (inside-out).
sign_one "${SPARKLE_FW}/Versions/B/Autoupdate"
sign_one "${SPARKLE_FW}/Versions/B/Updater.app"
# Frameworks embebidos (Python.framework, Sparkle.framework y demás).
find "${BUNDLE}/Contents" -type d -name '*.framework' -print0 \
  | while IFS= read -r -d '' fw; do sign_one "$fw"; done
# Otros ejecutables Mach-O sueltos bajo MacOS/ (el principal se firma en 5/9).
MAIN_EXE="$(basename "${BUNDLE%.app}")"
find "${BUNDLE}/Contents/MacOS" -type f -print0 \
  | while IFS= read -r -d '' f; do
      if [ "$(basename "$f")" = "${MAIN_EXE}" ]; then continue; fi
      if file "$f" | grep -q 'Mach-O'; then sign_one "$f"; fi
    done

echo "==> 5/9  Firmar el bundle (con entitlements)"
codesign --force --options runtime --timestamp \
    --entitlements "${ENTITLEMENTS}" \
    --sign "${DEV_ID_APP}" "${BUNDLE}"
codesign --verify --deep --strict --verbose=2 "${BUNDLE}"

echo "==> 6/9  Empaquetar para notarización"
ditto -c -k --keepParent "${BUNDLE}" "dist/app.zip"

echo "==> 7/9  Notarizar (espera al resultado)"
xcrun notarytool submit "dist/app.zip" --keychain-profile "${AC_PROFILE}" --wait

echo "==> 8/9  Staple del .app"
xcrun stapler staple "${BUNDLE}"
xcrun stapler validate "${BUNDLE}"

echo "==> 9/9  DMG + artefactos de actualización (v${VERSION})"
rm -f "${DMG}"
DMG_STAGING="dist/dmg-staging"
rm -rf "${DMG_STAGING}"
mkdir -p "${DMG_STAGING}"
ditto "${BUNDLE}" "${DMG_STAGING}/${APP_NAME}.app"
ln -s /Applications "${DMG_STAGING}/Applications"
hdiutil create -volname "${APP_NAME}" -srcfolder "${DMG_STAGING}" -ov -format UDZO "${DMG}"
rm -rf "${DMG_STAGING}"
codesign --force --sign "${DEV_ID_APP}" --timestamp "${DMG}"
xcrun notarytool submit "${DMG}" --keychain-profile "${AC_PROFILE}" --wait
xcrun stapler staple "${DMG}"

# ZIP versionado del .app YA stapleado (lo que descarga el auto-updater) + latest.json
rm -f "${UPDATE_ZIP}"
ditto -c -k --keepParent "${BUNDLE}" "${UPDATE_ZIP}"
SHA="$(shasum -a 256 "${UPDATE_ZIP}" | awk '{print $1}')"
cat > dist/latest.json <<JSON
{
  "version": "${VERSION}",
  "url": "https://github.com/${GH_REPO}/releases/download/v${VERSION}/GestorDeCorreos-${VERSION}.zip",
  "sha256": "${SHA}",
  "notes_url": "https://github.com/${GH_REPO}/releases/tag/v${VERSION}"
}
JSON
build-venv/bin/python macos/sign_manifest.py sign "${UPDATE_SIGNING_KEY}" dist/latest.json

echo "==> Delta de Sparkle desde la versión publicada (opcional)"
# Base = el zip del último Release, verificado con su firma del appcast
# (macos/delta_base.py). Quien tenga exactamente esa versión descarga solo el
# delta; los demás, el zip completo. Si no se puede, se publica sin delta.
DELTA_WORK="dist/delta-base"
DELTA_FILE=""
DELTA_ARGS=()
cdhash() { codesign -dvvv "$1" 2>&1 | awk -F= '/^CDHash=/{print $2}'; }
make_delta() {
  local old_app="${DELTA_WORK}/old/${APP_NAME}.app" applied="${DELTA_WORK}/applied.app" want
  ditto -x -k "${DELTA_WORK}/base.zip" "${DELTA_WORK}/old" || return 1
  [ -d "${old_app}" ] || { echo "    el zip publicado no contiene ${APP_NAME}.app" >&2; return 1; }
  "${BINARY_DELTA}" create "${old_app}" "${BUNDLE}" "${DELTA_FILE}" || return 1
  # Aplicar el delta a la versión publicada debe reproducir esta .app firmada.
  "${BINARY_DELTA}" apply "${old_app}" "${applied}" "${DELTA_FILE}" || return 1
  codesign --verify --deep --strict "${applied}" || return 1
  want="$(cdhash "${BUNDLE}")"
  [ -n "${want}" ] && [ "$(cdhash "${applied}")" = "${want}" ] \
    || { echo "    el delta aplicado no coincide con ${BUNDLE}" >&2; return 1; }
}
rm -rf "${DELTA_WORK}"
mkdir -p "${DELTA_WORK}"
DELTA_RC=0
PREV_VERSION="$(build-venv/bin/python macos/delta_base.py "${VERSION}" "${DELTA_WORK}/base.zip")" || DELTA_RC=$?
if [ "${DELTA_RC}" -eq 0 ]; then
  DELTA_FILE="dist/GestorDeCorreos-${VERSION}-from-${PREV_VERSION}.delta"
  if make_delta; then
    DELTA_ARGS=("${DELTA_FILE}" "${PREV_VERSION}")
    echo "    OK, ${DELTA_FILE} ($(stat -f%z "${DELTA_FILE}") bytes)"
  else
    echo "AVISO: no se pudo crear o verificar el delta; se publica solo el zip completo." >&2
    rm -f "${DELTA_FILE}"
    DELTA_FILE=""
  fi
elif [ "${DELTA_RC}" -ne 2 ]; then
  echo "ERROR: el Release publicado no pasa su verificación; revísalo antes de publicar." >&2
  exit "${DELTA_RC}"
fi
rm -rf "${DELTA_WORK}"

# Feed de Sparkle (v1.3.0+). latest.json se sigue publicando para las 1.2.x,
# que solo conocen el updater en Python: así pueden llegar a la 1.3.0.
build-venv/bin/python macos/make_appcast.py "${UPDATE_SIGNING_KEY}" "${UPDATE_ZIP}" "${VERSION}" dist/appcast.xml \
    ${DELTA_ARGS[@]+"${DELTA_ARGS[@]}"}

echo "==> Autocomprobación: el zip pasa la validación del auto-updater"
# Mismo código que ejecutará la app instalada antes de extraer la actualización
# (updater._check_zip_entries): si no pasa aquí, fallaría en los Macs.
build-venv/bin/python -c 'import sys, updater; print("    OK, raíz:", updater._check_zip_entries(sys.argv[1]))' "${UPDATE_ZIP}"

echo
echo "Listo:"
echo "  ${DMG}            (distribución manual)"
echo "  ${UPDATE_ZIP}     (asset del Release para el auto-updater)"
echo "  dist/latest.json  (asset del Release; el updater lo consulta)"
echo "  dist/latest.json.sig  (su firma Ed25519; sin ella la app rechaza el manifiesto)"
echo "  dist/appcast.xml  (feed de Sparkle, v1.3.0+; firma Ed25519 del zip dentro)"
[ -n "${DELTA_FILE}" ] && echo "  ${DELTA_FILE}  (delta de Sparkle desde v${PREV_VERSION})"
echo
echo "Publicar la actualización:"
echo "  git push origin HEAD   # el commit ${BUILD_COMMIT:0:7} debe estar en GitHub"
echo "  gh release create v${VERSION} \"${UPDATE_ZIP}\" dist/latest.json dist/latest.json.sig dist/appcast.xml ${DELTA_FILE:+\"${DELTA_FILE}\" }\"${DMG}\" --target ${BUILD_COMMIT} --title v${VERSION} --notes '...'"
echo
echo "Verifica en otro Mac:  spctl -a -vvv -t install \"${DMG}\""
echo "                       spctl -a -vvv \"${BUNDLE}\""
