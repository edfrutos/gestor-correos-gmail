"""Configuración py2app para la app macOS.

Ejecutar desde la raíz del repositorio, dentro de un venv con
`requirements.txt` + `requirements-macos.txt` instalados:

    python3 macos/setup.py py2app

Produce `dist/Gestor de Correos.app`. La firma, notarización y el DMG los hace
`macos/build_app.sh` a partir de ese `.app`.
"""

import sys
from pathlib import Path

from setuptools import setup

ROOT = Path(__file__).resolve().parent.parent
# Para que modulegraph resuelva server.py y los módulos planos del proyecto.
sys.path.insert(0, str(ROOT))

APP = [str(ROOT / "macos" / "app_main.py")]

DATA_FILES = [
    ("", [str(ROOT / "index.html")]),
    ("static", [str(p) for p in (ROOT / "static").glob("*") if p.is_file()]),
]

# Módulos planos del proyecto (no son paquetes): se fuerzan como includes.
PROJECT_MODULES = [
    "server", "gmail_client", "destructive_gmail", "storage",
    "validators", "classifier", "ai_client", "paths",
]

OPTIONS = {
    "argv_emulation": False,  # incompatible con algunas versiones de macOS/pyobjc
    "includes": PROJECT_MODULES + [
        "webview",
        "google.auth.transport.requests", "google.oauth2.credentials",
        "google_auth_oauthlib.flow", "google_auth_httplib2",
        "googleapiclient.discovery", "googleapiclient.errors",
        "googleapiclient.discovery_cache",
    ],
    # "google" en packages => py2app copia todo el árbol google/ SIN comprimir,
    # así el .so de google._upb queda como archivo suelto y se puede firmar.
    # Requiere que build_app.sh haya creado google/__init__.py en el build-venv
    # (namespace package -> paquete regular), si no py2app no lo encuentra.
    "packages": [
        "google", "googleapiclient", "google_auth_httplib2",
        "google_auth_oauthlib", "httplib2", "webview",
    ],
    "excludes": ["tkinter", "pytest", "setuptools", "pip"],
    "plist": {
        "CFBundleName": "Gestor de Correos",
        "CFBundleDisplayName": "Gestor de Correos",
        "CFBundleIdentifier": "com.edefrutos.gestorcorreos",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "LSMinimumSystemVersion": "12.0",
        "LSUIElement": False,
        "NSHighResolutionCapable": True,
        "NSHumanReadableCopyright": "© EDF Developer",
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "Correo electrónico (.eml)",
                "CFBundleTypeExtensions": ["eml"],
                "CFBundleTypeRole": "Viewer",
                "LSHandlerRank": "Alternate",
            }
        ],
    },
}

setup(
    app=APP,
    name="Gestor de Correos",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
