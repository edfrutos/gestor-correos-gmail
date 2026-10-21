"""Deja el .app solo con la arquitectura arm64 (como `lipo -thin arm64`).

cryptography (que usa updater) ya solo publica ruedas arm64 para macOS, así
que su _rust.so y el _cffi_backend.so van sin x86_64. Con el ejecutable
principal universal, un Mac Intel abría la app y fallaba al importar
cryptography; en arm64 puro macOS dice de entrada que la app no es compatible
y la Mac App Store no la ofrece en Intel. Uso, justo después de py2app:

    python3 macos/thin_bundle.py "dist/Gestor de Correos.app"

Falla si algún binario no incluye arm64. Invalida las firmas ad hoc de py2app;
los scripts de build vuelven a firmar todo después.
"""

import os
import struct
import sys

ARCH = "arm64"
CPU_TYPES = {0x01000007: "x86_64", 0x0100000C: "arm64", 7: "i386", 18: "ppc"}
FAT_MAGIC = 0xCAFEBABE      # fat_arch de 32 bits
FAT_MAGIC_64 = 0xCAFEBABF   # fat_arch_64
THIN_MAGICS_LE = (0xFEEDFACF, 0xFEEDFACE)  # Mach-O de 64/32 bits (little endian)


def _arch(cputype):
    return CPU_TYPES.get(cputype, hex(cputype))


def thin_file(path, arch=ARCH):
    """Devuelve "thinned", "ok" (ya era `arch`) o None (no es Mach-O).

    Lanza ValueError si el binario no tiene `arch`.
    """
    with open(path, "rb") as f:
        head = f.read(8)
        if len(head) < 8:
            return None
        magic = struct.unpack(">I", head[:4])[0]
        if magic in (FAT_MAGIC, FAT_MAGIC_64):
            nfat = struct.unpack(">I", head[4:8])[0]
            # Los .class de Java comparten 0xCAFEBABE; ahí este campo es la versión (>= 45).
            if magic == FAT_MAGIC and nfat > 20:
                return None
            entry = 32 if magic == FAT_MAGIC_64 else 20
            fmt = ">iiQQI" if magic == FAT_MAGIC_64 else ">iiIII"
            slices = []
            for _ in range(nfat):
                cputype, _sub, offset, size, _align = struct.unpack(fmt, f.read(entry)[: struct.calcsize(fmt)])
                slices.append((_arch(cputype & 0xFFFFFFFF), offset, size))
            for name, offset, size in slices:
                if name == arch:
                    f.seek(offset)
                    data = f.read(size)
                    break
            else:
                raise ValueError(f"{path}: sin {arch} ({', '.join(s[0] for s in slices)})")
        else:
            le = struct.unpack("<I", head[:4])[0]
            if le not in THIN_MAGICS_LE:
                return None
            name = _arch(struct.unpack("<I", head[4:8])[0])
            if name != arch:
                raise ValueError(f"{path}: solo {name}, sin {arch}")
            return "ok"
    mode = os.stat(path).st_mode
    tmp = path + ".thin"
    with open(tmp, "wb") as out:
        out.write(data)
    os.chmod(tmp, mode)
    os.replace(tmp, path)
    return "thinned"


def thin_bundle(bundle, arch=ARCH):
    counts = {"thinned": 0, "ok": 0}
    errors = []
    for root, _dirs, files in os.walk(bundle):
        for name in files:
            path = os.path.join(root, name)
            if os.path.islink(path):
                continue
            try:
                result = thin_file(path, arch)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if result:
                counts[result] += 1
    return counts, errors


def main(argv):
    if len(argv) != 2 or not os.path.isdir(argv[1]):
        sys.exit("Uso: thin_bundle.py <ruta del .app>")
    counts, errors = thin_bundle(argv[1])
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(f"{len(errors)} binario(s) sin {ARCH}")
    print(f"    {ARCH}: {counts['thinned']} binarios adelgazados, {counts['ok']} ya lo eran")


if __name__ == "__main__":
    main(sys.argv)
