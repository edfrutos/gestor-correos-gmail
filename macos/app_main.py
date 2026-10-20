#!/usr/bin/env python3
"""Punto de entrada de la app macOS.

Arranca `server.py` en un hilo sobre 127.0.0.1 con un puerto libre (para no
chocar con una instancia web/CLI ya en marcha) y muestra la UI local en una
ventana WKWebView vía pywebview. Al cerrar la ventana, detiene el servidor.

La app web y la CLI siguen funcionando exactamente igual: este módulo no las
toca, solo reutiliza el mismo backend.

En la build de la Mac App Store (`paths.is_app_store()`, Fase 35) corre en App
Sandbox: sin Sparkle ni menú de actualizaciones, el login OAuth abre el
navegador con NSWorkspace y la carpeta de respaldo se recuerda con un
*security-scoped bookmark*.

Prueba en el Mac sin empaquetar:
    python3 -m pip install -r requirements.txt -r requirements-macos.txt
    python3 macos/app_main.py [ruta/opcional/al/archivo.eml]
"""

import base64
import json
import os
import socket
import sys
import threading
import time
import webbrowser
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
OAUTH_BROWSER = "gestor-nsworkspace"
BUNDLED_OAUTH_CLIENT = "oauth_client.json"  # lo añade build_mas.sh (MAS_OAUTH_CLIENT)
BUNDLED_MARK = "gestor_bundled"
BOOKMARKS_FILE = "bookmarks.json"
# NSURLBookmarkCreationWithSecurityScope / NSURLBookmarkResolutionWithSecurityScope
_BOOKMARK_CREATE_SECURITY_SCOPE = 1 << 11
_BOOKMARK_RESOLVE_SECURITY_SCOPE = 1 << 10


class WorkspaceBrowser(webbrowser.BaseBrowser):
    """Abre URLs con NSWorkspace. El controlador por defecto de `webbrowser`
    en macOS lanza `osascript`, que App Sandbox no deja enviar AppleEvents."""

    def open(self, url, new=0, autoraise=True):
        from AppKit import NSWorkspace  # noqa: E402
        from Foundation import NSURL  # noqa: E402
        return bool(NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(url)))


def register_oauth_browser() -> bool:
    """`gmail_client.run_oauth_flow` abre el login de Google con este
    controlador (también con HEADLESS=1, que solo evita abrir la UI fuera)."""
    try:
        import AppKit  # noqa: F401,E402
    except ImportError:
        return False
    webbrowser.register(OAUTH_BROWSER, None, WorkspaceBrowser(OAUTH_BROWSER))
    os.environ["GESTOR_OAUTH_BROWSER"] = OAUTH_BROWSER
    return True


def install_bundled_oauth_client(resource_dir: Path, creds_path: Path) -> bool:
    """Copia el cliente OAuth que lleva la build de la Mac App Store a la
    carpeta de datos si el usuario no ha importado uno propio.

    La copia lleva `gestor_bundled: true`: así una versión nueva puede
    sustituirla, y un `credentials.json` del usuario (sin la marca) nunca se toca.
    """
    src = Path(resource_dir) / BUNDLED_OAUTH_CLIENT
    if not src.is_file():
        return False
    if creds_path.exists():
        try:
            current = json.loads(creds_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        if not (isinstance(current, dict) and current.get(BUNDLED_MARK)):
            return False
    data = json.loads(src.read_text(encoding="utf-8"))
    data[BUNDLED_MARK] = True
    text = json.dumps(data, indent=2) + "\n"
    if creds_path.exists() and creds_path.read_text(encoding="utf-8") == text:
        return False
    tmp = creds_path.with_name(creds_path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.chmod(0o600)
    tmp.replace(creds_path)
    return True


class FolderBookmarks:
    """Carpetas elegidas por el usuario que siguen accesibles tras reiniciar.

    En App Sandbox, lo elegido en un NSOpenPanel solo es accesible durante esa
    sesión; para la carpeta de respaldo se guarda un *security-scoped
    bookmark* (`bookmarks.json`, ruta → bookmark en base64) y al arrancar se
    resuelve y se activa con `startAccessingSecurityScopedResource`.
    """

    def __init__(self, store_path: Path):
        self.store_path = Path(store_path)
        self._active = []  # NSURL con acceso abierto: viven lo que el proceso

    def _load(self):
        try:
            data = json.loads(self.store_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save(self, data):
        tmp = self.store_path.with_name(self.store_path.name + ".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        tmp.chmod(0o600)
        tmp.replace(self.store_path)

    def remember(self, path: str) -> bool:
        from Foundation import NSURL  # noqa: E402
        url = NSURL.fileURLWithPath_(path)
        bookmark, error = url.bookmarkDataWithOptions_includingResourceValuesForKeys_relativeToURL_error_(
            _BOOKMARK_CREATE_SECURITY_SCOPE, None, None, None)
        if bookmark is None:
            print(f"[bookmarks] No se pudo guardar el acceso a {path}: {error}", file=sys.stderr)
            return False
        data = self._load()
        data[path] = base64.b64encode(bytes(bookmark)).decode("ascii")
        self._save(data)
        return True

    def restore(self) -> list:
        """Activa el acceso a cada carpeta guardada; devuelve las rutas activas."""
        from Foundation import NSURL, NSData  # noqa: E402
        data, restored, changed = self._load(), [], False
        for path, encoded in list(data.items()):
            try:
                raw = base64.b64decode(encoded)
            except ValueError:
                raw = b""
            url, stale, error = NSURL.URLByResolvingBookmarkData_options_relativeToURL_bookmarkDataIsStale_error_(
                NSData.dataWithBytes_length_(raw, len(raw)), _BOOKMARK_RESOLVE_SECURITY_SCOPE, None, None, None)
            if url is None or not url.startAccessingSecurityScopedResource():
                print(f"[bookmarks] Sin acceso a {path}: {error}", file=sys.stderr)
                data.pop(path)
                changed = True
                continue
            self._active.append(url)
            restored.append(str(url.path()))
            if stale:  # la carpeta se movió o renombró: se regenera el bookmark
                bookmark, _ = url.bookmarkDataWithOptions_includingResourceValuesForKeys_relativeToURL_error_(
                    _BOOKMARK_CREATE_SECURITY_SCOPE, None, None, None)
                if bookmark is not None:
                    data.pop(path)
                    data[str(url.path())] = base64.b64encode(bytes(bookmark)).decode("ascii")
                    changed = True
        if changed:
            self._save(data)
        return restored


class SparkleUpdater:
    """Sparkle 2 (`Contents/Frameworks/Sparkle.framework`) vía PyObjC (ADR-014).

    Sparkle lee `SUFeedURL`/`SUPublicEDKey` del Info.plist, programa las
    comprobaciones automáticas y muestra su propio diálogo estándar. Todo lo
    de AppKit va al hilo principal (`callAfter`). Si el framework no está
    (desde fuente) o no carga, `available` queda en False y la app usa el
    updater en Python (`updater.py`), como hasta la 1.2.x.
    """

    def __init__(self, framework_path=None, call_after=None):
        self.controller = None
        self.error = None
        self._framework_path = framework_path
        self._call_after = call_after

    @property
    def available(self) -> bool:
        return self.controller is not None

    def _default_framework_path(self):
        from Foundation import NSBundle  # noqa: E402
        frameworks = NSBundle.mainBundle().privateFrameworksPath()
        return os.path.join(str(frameworks), "Sparkle.framework") if frameworks else ""

    def start(self) -> bool:
        """Carga el framework y arranca el updater. Llamar en el hilo principal."""
        try:
            import objc  # noqa: E402
            from Foundation import NSBundle  # noqa: E402
            path = self._framework_path or self._default_framework_path()
            if not path or not os.path.isdir(path):
                self.error = "Sparkle.framework no está en el bundle"
                return False
            bundle = NSBundle.bundleWithPath_(path)
            if bundle is None or not bundle.load():
                self.error = f"No se pudo cargar {path}"
                return False
            controller_cls = objc.lookUpClass("SPUStandardUpdaterController")
            self.controller = controller_cls.alloc().initWithStartingUpdater_updaterDelegate_userDriverDelegate_(
                True, None, None)
        except Exception as exc:  # noqa: BLE001
            self.controller = None
            self.error = str(exc)
            print(f"[Sparkle] No disponible, se usa el updater en Python: {exc}", file=sys.stderr)
            return False
        return True

    def check_for_updates(self) -> bool:
        """Abre el diálogo de Sparkle (busca, muestra notas, pide permiso, instala)."""
        if self.controller is None:
            return False
        call_after = self._call_after
        if call_after is None:
            from PyObjCTools.AppHelper import callAfter as call_after  # noqa: E402
        call_after(self.controller.checkForUpdates_, None)
        return True


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


class JsApi:
    """Funciones nativas expuestas a la página como `window.pywebview.api`.

    La ventana va en un atributo privado: pywebview recorre los atributos
    públicos del objeto para exponerlos a JS.
    """

    def __init__(self, sparkle=None, bookmarks=None):
        self._window = None
        self._sparkle = sparkle
        self._bookmarks = bookmarks

    def check_updates(self):
        """Botón de la UI: con Sparkle abre su diálogo y devuelve True; si no,
        False y la página sigue con su flujo vía /api/update/*."""
        return bool(self._sparkle and self._sparkle.check_for_updates())

    def pick_folder(self):
        """Selector de carpeta nativo (panel Configuración → respaldo)."""
        if self._window is None:
            return None
        import webview  # noqa: E402
        folder_dialog = getattr(getattr(webview, "FileDialog", None), "FOLDER", None)
        if folder_dialog is None:
            folder_dialog = webview.FOLDER_DIALOG
        result = self._window.create_file_dialog(folder_dialog)
        folder = result[0] if result else None
        if folder and self._bookmarks is not None:
            self._bookmarks.remember(folder)
        return folder

    def import_credentials(self):
        """Botón «Importar credentials.json…»: selector nativo + validación.
        En App Sandbox es la única forma de que el usuario aporte su cliente."""
        if self._window is None:
            return {"ok": False, "error": "La ventana aún no está lista"}
        import webview  # noqa: E402
        open_dialog = getattr(getattr(webview, "FileDialog", None), "OPEN", None)
        if open_dialog is None:
            open_dialog = webview.OPEN_DIALOG
        result = self._window.create_file_dialog(open_dialog, file_types=("JSON (*.json)",))
        if not result:
            return {"ok": False, "cancelled": True}
        path = result[0] if isinstance(result, (list, tuple)) else result
        import gmail_client  # noqa: E402
        try:
            client_id = gmail_client.import_client_secrets(path)
        except (OSError, ValueError) as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "client_id": client_id}


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

    register_oauth_browser()

    # Importar DESPUÉS de fijar el entorno: server.py lee HOST/PORT al importarse.
    import server  # noqa: E402
    import gmail_client  # noqa: E402
    import paths  # noqa: E402

    app_store = paths.is_app_store()
    try:
        if install_bundled_oauth_client(paths.resource_dir(), gmail_client.CREDS):
            print("[OAuth] Cliente OAuth de la app instalado en la carpeta de datos", file=sys.stderr)
    except (OSError, ValueError) as exc:
        print(f"[OAuth] No se pudo instalar el cliente OAuth de la app: {exc}", file=sys.stderr)
    bookmarks = FolderBookmarks(paths.data_path(BOOKMARKS_FILE)) if app_store else None
    if bookmarks is not None:
        bookmarks.restore()

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

    # Mac App Store: sin Sparkle (no va en el bundle) ni updater propio.
    sparkle = None if app_store else SparkleUpdater()
    js_api = JsApi(sparkle, bookmarks)
    window = webview.create_window(APP_TITLE, start_url, width=1180, height=820, min_size=(900, 600), js_api=js_api)
    js_api._window = window
    opener = EmlOpener(window)
    window.events.loaded += opener.on_loaded
    _install_open_files_handler(opener)

    def on_started():
        # webview.start(func) ejecuta func en otro hilo: Sparkle, en el principal.
        if sparkle is None:
            return
        try:
            from PyObjCTools.AppHelper import callAfter
        except Exception:  # noqa: BLE001
            return
        callAfter(sparkle.start)

    try:
        webview.start(on_started, menu=[] if app_store else _build_menu(webview, window, sparkle))
    finally:
        httpd.shutdown()
        server_thread.join(timeout=5)
    return 0


def _toast(window, msg: str, kind: str = "ok") -> None:
    """Aviso informativo en la propia página: el único diálogo nativo de
    pywebview es de confirmación y mostraría un 'Cancelar' sin sentido."""
    window.evaluate_js(f"toast({json.dumps(msg)}, {json.dumps(kind)})")


def _build_menu(webview, window, sparkle=None):
    """Menú nativo con 'Buscar actualizaciones…' (Sparkle o, si no carga, updater.py)."""
    try:
        from webview.menu import Menu, MenuAction
    except Exception:
        return []

    def on_check_updates():
        if sparkle is not None and sparkle.check_for_updates():
            return
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
