#!/usr/bin/env python3
"""Genera el icono de la app a partir de macos/appicon-source.png.

Produce:
  macos/appicon-1024.png     master cuadrado 1024x1024
  macos/AppIcon.iconset/     todos los tamaños que pide macOS
  macos/AppIcon.icns         icono final (lo usa macos/setup.py)

Detecta el recuadro oscuro del logo sobre el fondo claro y recorta un
cuadrado centrado en él con un pequeño margen. Requiere Pillow.

    python3 macos/make_icon.py

En el Mac, build_app.sh regenera AppIcon.icns con `iconutil` (mejor calidad)
si está disponible; este script es el fallback multiplataforma.
"""

import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "appicon-source.png")
ICONSET = os.path.join(HERE, "AppIcon.iconset")
DARK_THRESHOLD = 120
MARGIN = 1.06
ICONSET_SPECS = [(16, 1), (16, 2), (32, 1), (32, 2), (128, 1),
                 (128, 2), (256, 1), (256, 2), (512, 1), (512, 2)]


def dark_bbox(img, thr=DARK_THRESHOLD, step=2):
    g = img.convert("L")
    px = g.load()
    w, h = g.size
    minx, miny, maxx, maxy = w, h, 0, 0
    for y in range(0, h, step):
        for x in range(0, w, step):
            if px[x, y] < thr:
                minx, maxx = min(minx, x), max(maxx, x)
                miny, maxy = min(miny, y), max(maxy, y)
    if maxx <= minx or maxy <= miny:
        return (0, 0, w, h)
    return (minx, miny, maxx, maxy)


def main():
    if not os.path.exists(SRC):
        sys.exit(f"No existe {SRC}")
    im = Image.open(SRC).convert("RGBA")
    w, h = im.size

    minx, miny, maxx, maxy = dark_bbox(im)
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    side = min(int(max(maxx - minx, maxy - miny) * MARGIN), min(w, h))
    left = max(0, min(int(cx - side / 2), w - side))
    top = max(0, min(int(cy - side / 2), h - side))
    master = im.crop((left, top, left + side, top + side)).resize((1024, 1024), Image.LANCZOS)
    master.save(os.path.join(HERE, "appicon-1024.png"))

    os.makedirs(ICONSET, exist_ok=True)
    for base, scale in ICONSET_SPECS:
        name = f"icon_{base}x{base}{'@2x' if scale == 2 else ''}.png"
        master.resize((base * scale, base * scale), Image.LANCZOS).save(os.path.join(ICONSET, name))

    try:
        master.save(os.path.join(HERE, "AppIcon.icns"), format="ICNS")
    except Exception as e:  # pragma: no cover
        print(f"AVISO: no se pudo escribir AppIcon.icns con Pillow ({e}).")
        print("En el Mac: iconutil -c icns macos/AppIcon.iconset -o macos/AppIcon.icns")

    print("Icono generado en macos/AppIcon.icns")


if __name__ == "__main__":
    main()
