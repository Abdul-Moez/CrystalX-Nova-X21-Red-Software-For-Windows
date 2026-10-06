# CrystalX Nova X21 mouse for Windows
# Copyright (C) 2026 Abdul Moez (https://github.com/Abdul-Moez)
# SPDX-License-Identifier: GPL-3.0-or-later -- see the LICENSE file.
"""Draw assets/crystalx-nova.ico: a red mouse, seen from above.

Run it again after changing the design; the .ico is committed so builds do
not need to regenerate it. It needs Pillow, which nothing else here does:
    pip install pillow
"""
import os

from PIL import Image, ImageDraw

SIZE = 256
SCALE = 4       # drawn this much larger, then shrunk, for smooth edges
HERE = os.path.dirname(os.path.abspath(__file__))
DARK = (20, 22, 32, 255)


def draw():
    big = SIZE * SCALE
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))

    def box(x0, y0, x1, y1):
        return tuple(v * SCALE for v in (x0, y0, x1, y1))

    # The body: a tall rounded shape, bright red at the top to deep red below.
    body = box(62, 14, 194, 242)
    shade = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    lines = ImageDraw.Draw(shade)
    for y in range(body[1], body[3]):
        t = (y - body[1]) / (body[3] - body[1])
        lines.line([(body[0], y), (body[2], y)],
                   fill=(int(238 - 78 * t), int(52 - 30 * t), int(58 - 26 * t), 255))
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle(body, 66 * SCALE, fill=255)
    img.paste(shade, (0, 0), mask)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(body, 66 * SCALE, outline=DARK, width=8 * SCALE)
    # The two buttons: a line down the middle, and one across below them.
    d.line(box(128, 18, 128, 112), fill=DARK, width=6 * SCALE)
    d.arc(box(62, 80, 194, 144), 20, 160, fill=DARK, width=6 * SCALE)
    # The wheel.
    d.rounded_rectangle(box(113, 44, 143, 98), 15 * SCALE, fill=(245, 245, 248, 255),
                        outline=DARK, width=6 * SCALE)
    return img.resize((SIZE, SIZE), Image.LANCZOS)


if __name__ == "__main__":
    path = os.path.join(HERE, "crystalx-nova.ico")
    draw().save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                             (128, 128), (256, 256)])
    print("wrote", path)
