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

import json
import os
import socket
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote
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
        if _is_eml(arg):
            return os.path.abspath(arg)
    return ""


def _is_eml(path: str) -> bool:
    return path.lower().endswith(".eml") and os.path.isfile(path)


class EmlOpener:
    """Abre en el visor los .eml que llegan por AppleEvent `odoc` (Finder).

    Con la app ya abierta, inyecta `openEmlReader` en la página sin recargarla.
    Si la página aún no ha cargado (arranque en frío desde el Finder), los
    encola y los abre al dispararse `loaded`.
    """

    def __init__(self, window, run_async=None):
        self.window = window
        self.ready = False
        self.pending = []
        self._lock = threading.Lock()
        # evaluate_js bloquea esperando al hilo principal de Cocoa, y `odoc`
        # llega precisamente en ese hilo: hay que llamarlo desde otro.
        self._run_async = run_async or (lambda fn: threading.Thread(target=fn, daemon=True).start())

    def open(self, path: str) -> None:
        if not _is_eml(path):
            return
        path = os.path.abspath(path)
        with self._lock:
            if not self.ready:
                self.pending.append(path)
                return
        self._show(path)

    def on_loaded(self) -> None:
        with self._lock:
            self.ready = True
            pending, self.pending = self.pending, []
        for path in pending:
            self._show(path)

    def _show(self, path: str) -> None:
        js = f"openEmlReader('', {json.dumps(path)})"
        self._run_async(lambda: self.window.evaluate_js(js))


def _install_open_files_handler(opener: EmlOpener) -> bool:
    """Añade `application:openFiles:` al AppDelegate de pywebview (Cocoa).

    NSApplication entrega ahí los `odoc` tanto en el arranque en frío (los
    encola hasta terminar de lanzar) como con la app ya abierta. Si el backend
    no es Cocoa o pywebview cambia su clase interna, se ignora sin romper.
    """
    try:
        import objc
        from webview.platforms.cocoa import BrowserView
    except Exception:
        return False

    def application_openFiles_(self, app, filenames):
        for name in filenames:
            opener.open(str(name))
        app.replyToOpenOrPrint_(0)  # NSApplicationDelegateReplySuccess

    try:
        objc.classAddMethods(BrowserView.AppDelegate, [
            objc.selector(application_openFiles_, selector=b"application:openFiles:", signature=b"v@:@@"),
        ])
    except Exception as exc:  # noqa: BLE001
        print(f"[odoc] No se pudo registrar el manejador: {exc}", file=sys.stderr)
        return False
    return True


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
        start_url = f"{base_url}/?view={quote(eml)}"

    try:
        import webview  # noqa: E402
    except ImportError:
        print("Falta pywebview: pip install -r requirements-macos.txt", file=sys.stderr)
        httpd.shutdown()
        return 1

    window = webview.create_window(APP_TITLE, start_url, width=1180, height=820, min_size=(900, 600))
    opener = EmlOpener(window)
    window.events.loaded += opener.on_loaded
    _install_open_files_handler(opener)
    try:
        webview.start(menu=_build_menu(webview, window))
    finally:
        httpd.shutdown()
        server_thread.join(timeout=5)
    return 0


def _toast(window, msg: str, kind: str = "ok") -> None:
    """Aviso informativo en la propia página: el único diálogo nativo de
    pywebview es de confirmación y mostraría un 'Cancelar' sin sentido."""
    window.evaluate_js(f"toast({json.dumps(msg)}, {json.dumps(kind)})")


def _build_menu(webview, window):
    """Menú nativo con 'Buscar actualizaciones…'."""
    try:
        from webview.menu import Menu, MenuAction
    except Exception:
        return []

    def on_check_updates():
        import updater  # noqa: E402
        info = updater.check_for_update()
        if info.get("error"):
            _toast(window, info["error"], "ok" if info.get("no_feed") else "err")
            return
        if not info.get("update_available"):
            _toast(window, f"Estás en la última versión (v{info['current']})")
            return
        msg = (f"Versión {info['latest']} disponible (tienes v{info['current']}).\n\n"
               "¿Descargar e instalar ahora? La app se cerrará y volverá a abrirse.")
        if not window.create_confirmation_dialog("Actualización disponible", msg):
            return
        try:
            app_path = updater.download_and_stage(info["url"], info["sha256"])
            updater.install_and_relaunch(app_path)
        except Exception as exc:  # noqa: BLE001
            window.create_confirmation_dialog("Error", f"No se pudo instalar la actualización:\n{exc}")
            return
        os._exit(0)

    return [Menu("Actualizaciones", [MenuAction("Buscar actualizaciones…", on_check_updates)])]


if __name__ == "__main__":
    raise SystemExit(main())
