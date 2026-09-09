#!/usr/bin/env python3
"""Punto de entrada de la app macOS.

Arranca `server.py` en un hilo sobre 127.0.0.1 con un puerto libre (para no
chocar con una instancia web/CLI ya en marcha) y muestra la UI local en una
ventana WKWebView vía pywebview. Al cerrar la ventana, detiene el servidor.

La app web y la CLI siguen funcionando exactamente igual: este módulo no las
toca, solo reutiliza el mismo backend.

Prueba en el Mac sin empaquetar:
    python3 -m pip install -r requirements.txt -r requirements-macos.txt
    python3 macos/app_main.py [ruta/opcional/al/archivo.eml]
"""

import os
import socket
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

# La carpeta del proyecto (padre de macos/) debe estar en sys.path para importar
# server.py y compañía tanto desde fuente como desde el .app (py2app la incluye).
_PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(_PROJECT_DIR))

APP_TITLE = "Gestor de Correos"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until_ready(url: str, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1) as r:
                if r.status == 200:
                    return True
        except OSError:
            time.sleep(0.15)
    return False


def _eml_from_argv() -> str:
    for arg in sys.argv[1:]:
        if arg.lower().endswith(".eml") and os.path.exists(arg):
            return os.path.abspath(arg)
    return ""


def main() -> int:
    host = "127.0.0.1"
    port = _free_port()
    os.environ.setdefault("HOST", host)
    os.environ["PORT"] = str(port)
    os.environ["HEADLESS"] = "1"  # nunca abrir el navegador del sistema

    # Importar DESPUÉS de fijar el entorno: server.py lee HOST/PORT al importarse.
    import server  # noqa: E402

    httpd = ThreadingHTTPServer((host, port), server.H)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    base_url = f"http://{host}:{port}"
    if not _wait_until_ready(f"{base_url}/api/status"):
        print("El servidor local no respondió a tiempo.", file=sys.stderr)
        httpd.shutdown()
        return 1

    start_url = base_url
    eml = _eml_from_argv()
    if eml:
        start_url = f"{base_url}/?view={eml}"

    try:
        import webview  # noqa: E402
    except ImportError:
        print("Falta pywebview: pip install -r requirements-macos.txt", file=sys.stderr)
        httpd.shutdown()
        return 1

    webview.create_window(APP_TITLE, start_url, width=1180, height=820, min_size=(900, 600))
    try:
        webview.start()  # bloquea hasta que se cierran todas las ventanas
    finally:
        httpd.shutdown()
        server_thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
