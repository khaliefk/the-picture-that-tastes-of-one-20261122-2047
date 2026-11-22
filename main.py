#!/usr/bin/env python3
"""A Bowl of Steaming Ramen.

One steaming bowl of tonkotsu ramen, drawn from scratch with the Python
standard library only. Running it writes a single 1024x1024 PNG to
/output/entry.png, or to $ENTRY_PNG when that is set (handy for local
checks). No network, no files read, nothing random: the same run always
paints the same bowl.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024


def clamp8(v):
    return 0 if v < 0 else 255 if v > 255 else int(v)


def mix(a, b, t):
    """Blend two RGB colours, t=0 gives a, t=1 gives b."""
    return (
        clamp8(a[0] + (b[0] - a[0]) * t),
        clamp8(a[1] + (b[1] - a[1]) * t),
        clamp8(a[2] + (b[2] - a[2]) * t),
    )


class Img:
    """A plain RGB canvas backed by one bytearray."""

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def put(self, x, y, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = rgb[0]
            self.px[i + 1] = rgb[1]
            self.px[i + 2] = rgb[2]

    def blend(self, x, y, rgb, a):
        if 0 <= x < self.w and 0 <= y < self.h and a > 0:
            i = (y * self.w + x) * 3
            if a >= 1:
                self.px[i] = rgb[0]
                self.px[i + 1] = rgb[1]
                self.px[i + 2] = rgb[2]
                return
            self.px[i] = clamp8(self.px[i] + (rgb[0] - self.px[i]) * a)
            self.px[i + 1] = clamp8(self.px[i + 1] + (rgb[1] - self.px[i + 1]) * a)
            self.px[i + 2] = clamp8(self.px[i + 2] + (rgb[2] - self.px[i + 2]) * a)

    def fill_row(self, y, rgb):
        if 0 <= y < self.h:
            s = y * self.w * 3
            self.px[s:s + self.w * 3] = bytes(rgb) * self.w

    def fill_span(self, y, x0, x1, rgb):
        x0 = max(0, x0)
        x1 = min(self.w - 1, x1)
        if x1 < x0 or not 0 <= y < self.h:
            return
        s = (y * self.w + x0) * 3
        self.px[s:s + (x1 - x0 + 1) * 3] = bytes(rgb) * (x1 - x0 + 1)

    def blend_span(self, y, x0, x1, rgb, a):
        x0 = max(0, x0)
        x1 = min(self.w - 1, x1)
        if x1 < x0 or not 0 <= y < self.h or a <= 0:
            return
        for x in range(x0, x1 + 1):
            self.blend(x, y, rgb, a)

    def rect(self, x0, y0, x1, y1, rgb, a=1.0):
        for y in range(y0, y1 + 1):
            if a >= 1:
                self.fill_span(y, x0, x1, rgb)
            else:
                self.blend_span(y, x0, x1, rgb, a)

    def disc(self, cx, cy, r, rgb, a=1.0):
        r = int(r)
        if r < 1:
            self.blend(cx, cy, rgb, a)
            return
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            if a >= 1:
                self.fill_span(cy + dy, cx - dx, cx + dx, rgb)
            else:
                self.blend_span(cy + dy, cx - dx, cx + dx, rgb, a)

    def ellipse(self, cx, cy, rx, ry, rgb, a=1.0):
        for dy in range(-ry, ry + 1):
            t = 1.0 - (dy * dy) / float(ry * ry)
            dx = int(rx * math.sqrt(max(0.0, t)))
            if a >= 1:
                self.fill_span(cy + dy, cx - dx, cx + dx, rgb)
            else:
                self.blend_span(cy + dy, cx - dx, cx + dx, rgb, a)

    def ellipse_arc(self, cx, cy, rx, ry, a0, a1, rgb, wd=3, a=1.0):
        n = 72
        for i in range(n + 1):
            t = a0 + (a1 - a0) * i / n
            x = int(cx + rx * math.cos(t))
            y = int(cy + ry * math.sin(t))
            self.disc(x, y, max(1, wd // 2), rgb, a)

    def thick_line(self, x0, y0, x1, y1, wd, rgb, a=1.0):
        steps = int(max(abs(x1 - x0), abs(y1 - y0)) / 3) + 1
        r = max(1, wd // 2)
        for s in range(steps + 1):
            t = s / float(steps)
            x = int(x0 + (x1 - x0) * t)
            y = int(y0 + (y1 - y0) * t)
            self.disc(x, y, r, rgb, a)

    def strand(self, pts, wd, rgb, clip=None):
        """A wavy line drawn as overlapping discs, optionally clipped to
        an ellipse (cx, cy, rx, ry) so noodles never spill past the broth."""
        r = max(1, wd // 2)
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            steps = max(1, int(max(abs(x1 - x0), abs(y1 - y0)) / 3))
            for s in range(steps + 1):
                t = s / steps
                x = int(x0 + (x1 - x0) * t)
                y = int(y0 + (y1 - y0) * t)
                if clip is not None:
                    cx, cy, rx, ry = clip
                    if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 > 1.0:
                        continue
                self.disc(x, y, r, rgb)


# --- palette -------------------------------------------------------------
INK = (28, 18, 14)
BOWL = (36, 48, 86)
BOWL_DARK = (24, 33, 62)
RIM = (66, 84, 132)
BROTH = (198, 122, 42)
BROTH_LIGHT = (234, 172, 80)
NOODLE = (238, 205, 130)
NOODLE_SHADE = (186, 146, 78)
EGG_WHITE = (246, 241, 226)
YOLK = (235, 145, 45)
YOLK_LIGHT = (252, 192, 92)
CHASHU = (212, 128, 108)
CHASHU_FAT = (240, 216, 198)
NARUTO_PINK = (226, 118, 138)
ONION = (96, 168, 74)
ONION_DARK = (46, 96, 48)
NORI = (26, 44, 32)
CHOP = (122, 72, 36)
CHOP_LIGHT = (164, 108, 58)
CHILI = (198, 60, 30)

BROTH_BOX = (512, 560, 305, 128)


def noodle_wave(img, x0, x1, ybase, amp, freq, phase, wd, rgb):
    pts = []
    for x in range(x0, x1 + 1, 6):
        y = ybase + amp * math.sin(x * freq + phase)
        pts.append((x, int(y)))
    img.strand(pts, wd, rgb, clip=BROTH_BOX)


def draw_scene(img):
    # Warm dark backdrop, darker at the top so the bowl glows.
    for y in range(H):
        img.fill_row(y, mix((30, 20, 16), (68, 44, 27), y / (H - 1)))

    # Wooden table across the bottom third, with plank seams.
    for y in range(700, H):
        img.fill_row(y, mix((88, 56, 34), (56, 35, 21), (y - 700) / 324.0))
    for y in (762, 832, 906, 976):
        img.blend_span(y, 0, W - 1, (30, 18, 10), 0.45)

    # Soft warm light washing down from the top left.
    img.ellipse(400, 360, 430, 270, (255, 190, 110), 0.05)

    # Shadow pooling under the bowl.
    img.ellipse(512, 862, 320, 42, (10, 6, 4), 0.4)
    img.ellipse(512, 856, 260, 30, (10, 6, 4), 0.35)

    # Bowl: deep indigo body, darker belly, pale rim band.
    img.ellipse(512, 640, 340, 210, BOWL)
    img.ellipse(512, 700, 300, 150, BOWL_DARK, 0.55)
    img.ellipse(512, 560, 340, 150, RIM)
    img.ellipse(512, 560, 322, 138, BOWL)

    # Broth: golden, lighter toward the top left where the light hits.
    img.ellipse(512, 560, 305, 128, BROTH)
    img.ellipse(470, 528, 215, 82, BROTH_LIGHT, 0.55)
    img.ellipse(560, 610, 180, 70, (168, 96, 30), 0.35)
    # Oil sheen arcs on the broth.
    img.ellipse_arc(512, 560, 260, 104, 3.6, 5.2, (250, 200, 120), 5, 0.5)
    img.ellipse_arc(512, 560, 210, 82, 0.4, 1.6, (250, 200, 120), 4, 0.4)

    # Nori sheet standing at the back right of the bowl.
    img.rect(706, 384, 764, 500, NORI)
    img.disc(735, 384, 29, NORI)
    # A thin lit edge so the dark sheet reads against the dark backdrop.
    img.rect(706, 392, 712, 496, (74, 112, 82), 0.55)

    # Noodles: three loose bunches of wavy strands across the broth.
    bunches = [
        (280, 740, 505, 12, 0.045, 0.0),
        (290, 750, 565, 14, 0.05, 1.3),
        (300, 745, 625, 12, 0.042, 2.6),
    ]
    for x0, x1, yb, amp, freq, ph in bunches:
        for k in range(9):
            shade = k % 3 == 0
            noodle_wave(
                img, x0, x1, yb + k * 9 - 36, amp, freq, ph + k * 0.35,
                8, NOODLE_SHADE if shade else NOODLE,
            )

    # Narutomaki: white disc with a pink spiral.
    img.disc(520, 470, 42, (250, 246, 238))
    spiral = []
    for i in range(90):
        t = i / 89.0
        ang = t * math.pi * 4.2
        rr = 5 + t * 30
        spiral.append((int(520 + rr * math.cos(ang)), int(470 + rr * math.sin(ang))))
    img.strand(spiral, 7, NARUTO_PINK)
    img.disc(520, 470, 6, NARUTO_PINK)

    # Soft egg halves on the left, yolks facing up.
    for ecx, ecy in ((352, 498), (352, 612)):
        img.ellipse(ecx, ecy, 58, 44, EGG_WHITE)
        img.disc(ecx, ecy, 24, YOLK)
        img.disc(ecx - 7, ecy - 8, 10, YOLK_LIGHT)

    # Chashu slices on the right, overlapping like roof tiles.
    for ccx, ccy, cr in ((648, 498, 56), (694, 572, 60), (632, 640, 54)):
        img.disc(ccx, ccy, cr, CHASHU)
        img.disc(ccx, ccy, cr - 16, CHASHU_FAT)
        img.disc(ccx, ccy, cr - 28, (205, 118, 100))
        img.disc(ccx - 12, ccy - 12, 10, (232, 160, 138), 0.7)

    # Chili oil drops glistening on the broth.
    for dx, dy, dr in ((470, 660, 11), (585, 520, 9), (430, 585, 8),
                       (660, 640, 10), (540, 690, 8)):
        img.disc(dx, dy, dr, CHILI, 0.85)
        img.disc(dx - 3, dy - 3, 3, (255, 120, 80), 0.8)

    # Green onion rings scattered over the noodles.
    onions = [
        (300, 540), (420, 520), (600, 500), (700, 620), (470, 560),
        (560, 640), (380, 660), (640, 560), (500, 600), (330, 600),
        (740, 560), (450, 680), (590, 680), (280, 610), (680, 500),
        (520, 540),
    ]
    for ox, oy in onions:
        img.disc(ox, oy, 9, ONION)
        img.disc(ox, oy, 4, ONION_DARK)
        img.disc(ox - 2, oy - 2, 2, (180, 220, 130))

    # A few sesame seeds for texture.
    for sx, sy in ((400, 545), (620, 610), (480, 640), (700, 590), (360, 560)):
        img.disc(sx, sy, 3, (245, 230, 200))

    # Chopsticks resting across the rim, upper right.
    img.thick_line(560, 428, 902, 500, 15, CHOP)
    img.thick_line(576, 452, 908, 520, 15, CHOP)
    img.thick_line(560, 424, 902, 496, 5, CHOP_LIGHT)
    img.thick_line(576, 448, 908, 516, 5, CHOP_LIGHT)

    # Rim highlight where the light catches the ceramic.
    img.ellipse_arc(512, 560, 332, 144, 3.5, 4.9, (150, 170, 220), 6, 0.55)

    # Steam: three wavy columns rising off the broth, fading as they climb.
    # Small steps and soft alphas keep each column one smooth ribbon
    # instead of a string of beads.
    for cx, phase in ((400, 0.0), (512, 1.8), (625, 3.4)):
        y = 430
        while y > 110:
            sway = 26 * math.sin(y * 0.018 + phase)
            fade = 0.09 * (y - 100) / 330.0 + 0.03
            img.disc(int(cx + sway), y, 17, (255, 250, 240), fade)
            img.disc(int(cx + sway), y, 8, (255, 255, 250), fade + 0.03)
            y -= 6


def write_png(img, path):
    """Encode the canvas as a plain RGB PNG (filter 0, zlib level 9)."""
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += img.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out = os.environ.get("ENTRY_PNG", "/output/entry.png")
    img = Img(W, H)
    draw_scene(img)
    size = write_png(img, out)
    print(f"wrote {out}: {W}x{H}, {size} bytes")


if __name__ == "__main__":
    main()
