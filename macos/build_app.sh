#!/usr/bin/env bash
# Build + firma + notarización + DMG de la app macOS.
# Ejecutar en un Mac, desde la raíz del repositorio:
#
#   export DEV_ID_APP="Developer ID Application: Nombre Apellidos (TEAMID)"
#   export AC_PROFILE="gestor-notary"      # perfil guardado con notarytool store-credentials
#   bash macos/build_app.sh
#
# Requisitos: Xcode Command Line Tools, Python 3.11+, cuenta Apple Developer,
# certificado Developer ID Application en el llavero, y un perfil de notarytool:
#   xcrun notarytool store-credentials "gestor-notary" \
#       --apple-id "TU_APPLE_ID" --team-id "TEAMID" --password "APP-SPECIFIC-PASSWORD"

set -euo pipefail

APP_NAME="Gestor de Correos"
BUNDLE="dist/${APP_NAME}.app"
DMG="dist/GestorDeCorreos.dmg"
ENTITLEMENTS="macos/entitlements.plist"

require() { [ -n "${!1:-}" ] || { echo "Falta la variable de entorno: $1" >&2; exit 1; }; }
require DEV_ID_APP
require AC_PROFILE

echo "==> 1/8  Entorno de build"
python3 -m venv build-venv
build-venv/bin/python -m pip install --upgrade pip wheel
build-venv/bin/python -m pip install -r requirements.txt -r requirements-macos.txt

echo "==> 2/8  py2app"
rm -rf build dist
build-venv/bin/python macos/setup.py py2app

echo "==> 3/8  Firma (Hardened Runtime + entitlements)"
codesign --deep --force --options runtime --timestamp \
    --entitlements "${ENTITLEMENTS}" \
    --sign "${DEV_ID_APP}" "${BUNDLE}"
codesign --verify --strict --verbose=2 "${BUNDLE}"

echo "==> 4/8  Empaquetar para notarización"
ditto -c -k --keepParent "${BUNDLE}" "dist/app.zip"

echo "==> 5/8  Notarizar (espera al resultado)"
xcrun notarytool submit "dist/app.zip" --keychain-profile "${AC_PROFILE}" --wait

echo "==> 6/8  Staple del .app"
xcrun stapler staple "${BUNDLE}"
xcrun stapler validate "${BUNDLE}"

echo "==> 7/8  DMG"
rm -f "${DMG}"
hdiutil create -volname "${APP_NAME}" -srcfolder "${BUNDLE}" -ov -format UDZO "${DMG}"
codesign --force --sign "${DEV_ID_APP}" --timestamp "${DMG}"

echo "==> 8/8  Notarizar y staple del DMG"
xcrun notarytool submit "${DMG}" --keychain-profile "${AC_PROFILE}" --wait
xcrun stapler staple "${DMG}"

echo
echo "Listo: ${DMG}"
echo "Verifica en otro Mac:  spctl -a -vvv -t open --context context:primary-signature \"${BUNDLE}\""
