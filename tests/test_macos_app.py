import importlib.util
from pathlib import Path


APP_MAIN = Path(__file__).parents[1] / 'macos' / 'app_main.py'
spec = importlib.util.spec_from_file_location('app_main', APP_MAIN)
app_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_main)


class FakeWindow:
    def __init__(self):
        self.calls = []

    def evaluate_js(self, js):
        self.calls.append(js)


def make_opener():
    window = FakeWindow()
    return window, app_main.EmlOpener(window, run_async=lambda fn: fn())


def test_eml_opened_before_page_load_is_queued_until_loaded(tmp_path):
    eml = tmp_path / 'aviso.eml'
    eml.write_text('Subject: x\n\ny')
    window, opener = make_opener()

    opener.open(str(eml))
    assert window.calls == []
    assert opener.pending == [str(eml)]

    opener.on_loaded()
    assert window.calls == [f'openEmlReader(\'\', "{eml}")']
    assert opener.pending == []


def test_eml_opened_with_app_already_loaded_shows_immediately(tmp_path):
    eml = tmp_path / 'con "comillas" y espacios.eml'
    eml.write_text('Subject: x\n\ny')
    window, opener = make_opener()
    opener.on_loaded()

    opener.open(str(eml))
    # json.dumps escapa la ruta: no se puede romper el JS inyectado.
    assert window.calls == ['openEmlReader(\'\', "' + str(eml).replace('"', '\\"') + '")']


def test_non_eml_or_missing_files_are_ignored(tmp_path):
    other = tmp_path / 'nota.txt'
    other.write_text('x')
    window, opener = make_opener()
    opener.on_loaded()

    opener.open(str(other))
    opener.open(str(tmp_path / 'no-existe.eml'))
    assert window.calls == []


def test_later_loaded_events_do_not_reopen_flushed_files(tmp_path):
    eml = tmp_path / 'a.eml'
    eml.write_text('Subject: x\n\ny')
    window, opener = make_opener()
    opener.open(str(eml))
    opener.on_loaded()
    opener.on_loaded()  # p. ej. tras una navegación interna
    assert len(window.calls) == 1


def test_handler_install_is_a_noop_without_cocoa_backend():
    # En Linux/CI no hay pyobjc ni backend Cocoa: no debe lanzar.
    _, opener = make_opener()
    assert app_main._install_open_files_handler(opener) is False
