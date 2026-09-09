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

require() { [ -n "${!1:-}" ] || { echo "Falta la variable de entorno: $1" >&2; exit 1; }; }
require DEV_ID_APP
require AC_PROFILE

echo "==> 1/9  Entorno de build  (PYTHON=${PYTHON})"
"${PYTHON}" -c 'import sysconfig,sys; sys.exit(0 if sysconfig.get_config_var("PYTHONFRAMEWORK") else 1)' \
    || echo "AVISO: ${PYTHON} no parece un framework build; py2app puede fallar. Ver cabecera." >&2
"${PYTHON}" -m venv build-venv
build-venv/bin/python -m pip install --upgrade pip wheel
build-venv/bin/python -m pip install -r requirements.txt -r requirements-macos.txt

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

echo "==> 4/9  Firmar binarios anidados (inside-out, Hardened Runtime + timestamp)"
sign_one() { codesign --force --options runtime --timestamp --sign "${DEV_ID_APP}" "$1"; }
export -f sign_one
export DEV_ID_APP
# .so y .dylib: los más numerosos, se firman todos.
find "${BUNDLE}/Contents" -type f \( -name '*.so' -o -name '*.dylib' \) -print0 \
  | while IFS= read -r -d '' f; do sign_one "$f"; done
# Frameworks embebidos (Python.framework y demás).
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
hdiutil create -volname "${APP_NAME}" -srcfolder "${BUNDLE}" -ov -format UDZO "${DMG}"
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

echo
echo "Listo:"
echo "  ${DMG}            (distribución manual)"
echo "  ${UPDATE_ZIP}     (asset del Release para el auto-updater)"
echo "  dist/latest.json  (asset del Release; el updater lo consulta)"
echo
echo "Publicar la actualización:"
echo "  gh release create v${VERSION} \"${UPDATE_ZIP}\" dist/latest.json \"${DMG}\" --title v${VERSION} --notes '...'"
echo
echo "Verifica en otro Mac:  spctl -a -vvv -t install \"${DMG}\""
echo "                       spctl -a -vvv \"${BUNDLE}\""
