#!/usr/bin/env python3
"""Make the program's icon: a picture (PNG, JPEG...) into a Windows .ico of every size Windows asks for.

    python3 tools/icon/make_icon.py <picture> <out.ico> [--white-to-alpha] [--preview <png>]

--white-to-alpha takes a white background out. The subject's body (its saturated pixels, and everything they enclose:
eyes, highlights) stays opaque as drawn; outside it, each pixel gets the smallest alpha that reproduces it over white
("colour to alpha"), so a soft edge or glow fades out instead of ending in a white square. The
picture is cropped to what is left, centred on a transparent square, and written at 16, 20, 24, 32, 40, 48, 64, 96, 128
and 256 px (Lanczos). Needs Pillow.
"""
import argparse
from pathlib import Path

from collections import deque

import numpy as np
from PIL import Image

SIZES = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]


def body_mask(rgb, saturation=60):
    """The subject: saturated pixels, with every region they enclose (not reachable from the border without crossing
    them) filled in."""
    body = (rgb.max(axis=2).astype(int) - rgb.min(axis=2).astype(int)) > saturation
    h, w = body.shape
    outside = np.zeros_like(body)
    queue = deque((y, x) for y in range(h) for x in (0, w - 1)) + deque((y, x) for x in range(w) for y in (0, h - 1))
    while queue:
        y, x = queue.popleft()
        if outside[y, x] or body[y, x]:
            continue
        outside[y, x] = True
        for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= ny < h and 0 <= nx < w and not outside[ny, nx] and not body[ny, nx]:
                queue.append((ny, nx))
    return ~outside


def white_to_alpha(img):
    rgba = np.asarray(img.convert("RGBA")).astype(np.float64)
    rgb = rgba[..., :3]
    inside = body_mask(rgba[..., :3].astype(np.uint8))
    alpha = (255.0 - rgb).max(axis=2)
    f = np.clip(alpha / 255.0, 1e-6, 1.0)
    colour = np.clip((rgb - 255.0 * (1.0 - f)[..., None]) / f[..., None], 0, 255)
    out = np.empty_like(rgba)
    out[..., :3] = np.where(inside[..., None], rgb, colour)
    out[..., 3] = np.where(inside, rgba[..., 3], alpha * rgba[..., 3] / 255.0)
    return Image.fromarray(np.round(out).astype(np.uint8), "RGBA")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("picture", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--white-to-alpha", action="store_true")
    ap.add_argument("--preview", type=Path)
    a = ap.parse_args()
    img = Image.open(a.picture)
    img = white_to_alpha(img) if a.white_to_alpha else img.convert("RGBA")
    # Crop to what is not (nearly) transparent, then centre on a square with a small margin.
    box = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox() or (0, 0, img.width, img.height)
    img = img.crop(box)
    side = round(max(img.size) * 1.04)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
    big = square.resize((256, 256), Image.LANCZOS)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    big.save(a.out, format="ICO", sizes=[(s, s) for s in SIZES])
    if a.preview:
        sheet = Image.new("RGBA", (sum(SIZES) + 10 * len(SIZES) + 10, 276), (32, 32, 40, 255))
        x = 10
        for s in SIZES:
            sheet.paste(square.resize((s, s), Image.LANCZOS), (x, 266 - s), square.resize((s, s), Image.LANCZOS))
            x += s + 10
        sheet.save(a.preview)
    print(f"{a.out}: {', '.join(map(str, SIZES))} px")


if __name__ == "__main__":
    main()
