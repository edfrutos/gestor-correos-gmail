"""macos/check_bundle.sh: el .app lleva los módulos nativos que modulegraph no ve."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "macos" / "check_bundle.sh"


def _bundle(tmp_path, files):
    dynload = tmp_path / "X.app" / "Contents" / "Resources" / "lib" / "python3.12" / "lib-dynload"
    for rel in files:
        f = dynload / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.touch()
    return tmp_path / "X.app"


def _run(bundle):
    return subprocess.run(["bash", str(SCRIPT), str(bundle)], capture_output=True, text=True)


def test_ok_with_cffi_backend(tmp_path):
    app = _bundle(tmp_path, ["_cffi_backend.so", "cryptography/hazmat/bindings/_rust.so"])
    assert _run(app).returncode == 0


def test_fails_without_cffi_backend(tmp_path):
    r = _run(_bundle(tmp_path, ["cryptography/hazmat/bindings/_rust.so"]))
    assert r.returncode == 1
    assert "_cffi_backend.so" in r.stderr


def test_fails_without_lib_dynload(tmp_path):
    assert _run(tmp_path / "nada.app").returncode == 1


def test_setup_includes_cffi_backend_and_builds_check():
    assert '"_cffi_backend"' in (ROOT / "macos" / "setup.py").read_text(encoding="utf-8")
    for script in ("build_app.sh", "build_mas.sh"):
        assert "macos/check_bundle.sh" in (ROOT / "macos" / script).read_text(encoding="utf-8")
