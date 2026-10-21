"""macos/thin_bundle.py: deja el .app solo con arm64 (cryptography no trae x86_64)."""

import importlib.util
import struct
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "macos" / "thin_bundle.py"
spec = importlib.util.spec_from_file_location("thin_bundle", SCRIPT)
thin_bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thin_bundle)

ARM64, X86_64 = 0x0100000C, 0x01000007


def _thin(cputype, body):
    return struct.pack("<II", 0xFEEDFACF, cputype) + body


def _fat(*slices):
    """Binario universal con fat_arch de 32 bits, slices alineados a 16."""
    header = struct.pack(">II", 0xCAFEBABE, len(slices))
    offset = len(header) + 20 * len(slices)
    entries, blobs = b"", b""
    for cputype, data in slices:
        pad = (-(offset + len(blobs))) % 16
        blobs += b"\0" * pad
        entries += struct.pack(">iiIII", cputype, 0, offset + len(blobs), len(data), 4)
        blobs += data
    return header + entries + blobs


def test_extracts_arm64_slice(tmp_path):
    arm = _thin(ARM64, b"ARM" * 10)
    f = tmp_path / "lib.so"
    f.write_bytes(_fat((X86_64, _thin(X86_64, b"X86" * 7)), (ARM64, arm)))
    f.chmod(0o755)
    assert thin_bundle.thin_file(str(f)) == "thinned"
    assert f.read_bytes() == arm
    assert f.stat().st_mode & 0o777 == 0o755


def test_already_arm64_and_non_macho_untouched(tmp_path):
    arm = tmp_path / "a.so"
    arm.write_bytes(_thin(ARM64, b"x"))
    txt = tmp_path / "a.py"
    txt.write_text("print('hola')\n")
    assert thin_bundle.thin_file(str(arm)) == "ok"
    assert thin_bundle.thin_file(str(txt)) is None


def test_java_class_is_not_fat(tmp_path):
    cls = tmp_path / "A.class"
    cls.write_bytes(struct.pack(">II", 0xCAFEBABE, 52) + b"\0" * 16)  # versión 52 = Java 8
    assert thin_bundle.thin_file(str(cls)) is None


def test_errors_without_arm64(tmp_path):
    f = tmp_path / "x.so"
    f.write_bytes(_fat((X86_64, _thin(X86_64, b"x"))))
    with pytest.raises(ValueError, match="sin arm64"):
        thin_bundle.thin_file(str(f))
    g = tmp_path / "y.so"
    g.write_bytes(_thin(X86_64, b"x"))
    with pytest.raises(ValueError, match="solo x86_64"):
        thin_bundle.thin_file(str(g))


def test_cli_walks_bundle_and_fails_on_x86_only(tmp_path):
    app = tmp_path / "X.app" / "Contents"
    (app / "MacOS").mkdir(parents=True)
    (app / "MacOS" / "X").write_bytes(_fat((X86_64, _thin(X86_64, b"a")), (ARM64, _thin(ARM64, b"b"))))
    (app / "Frameworks").mkdir()
    (app / "Frameworks" / "link.dylib").symlink_to("../MacOS/X")
    ok = subprocess.run([sys.executable, str(SCRIPT), str(tmp_path / "X.app")], capture_output=True, text=True)
    assert ok.returncode == 0, ok.stderr
    assert "1 binarios adelgazados" in ok.stdout
    (app / "MacOS" / "intel.so").write_bytes(_thin(X86_64, b"c"))
    bad = subprocess.run([sys.executable, str(SCRIPT), str(tmp_path / "X.app")], capture_output=True, text=True)
    assert bad.returncode == 1
    assert "intel.so" in bad.stderr


def test_build_scripts_thin_after_check_bundle():
    for script, bundle in (("build_app.sh", '"dist/${APP_NAME}.app"'), ("build_mas.sh", '"${BUNDLE}"')):
        text = (ROOT / "macos" / script).read_text(encoding="utf-8")
        check = text.index(f"bash macos/check_bundle.sh {bundle}")
        thin = text.index(f"build-venv/bin/python macos/thin_bundle.py {bundle}")
        assert check < thin
    app = (ROOT / "macos" / "build_app.sh").read_text(encoding="utf-8")
    assert app.index("macos/thin_bundle.py") < app.index("==> 3b/9 Sparkle")  # Sparkle queda como viene
