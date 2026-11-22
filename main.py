#!/usr/bin/env python3
"""A bowl of steaming ramen, drawn pixel by pixel with the standard library.

Run it and it writes a 1024x1024 PNG. No third party packages, no network,
just math, a byte buffer, and a small PNG encoder built on zlib and struct.
"""
import math
import os
import struct
import zlib

W = 1024
H = 1024


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def mix(a, b, t):
    return int(round(a + (b - a) * t))


class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)

    def _idx(self, x, y):
        return (y * self.w + x) * 3

    def put(self, x, y, rgb, alpha=255):
        x = int(x)
        y = int(y)
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return
        i = self._idx(x, y)
        if alpha >= 255:
            self.buf[i] = rgb[0]
            self.buf[i + 1] = rgb[1]
            self.buf[i + 2] = rgb[2]
            return
        if alpha <= 0:
            return
        inv = 255 - alpha
        self.buf[i] = (rgb[0] * alpha + self.buf[i] * inv) // 255
        self.buf[i + 1] = (rgb[1] * alpha + self.buf[i + 1] * inv) // 255
        self.buf[i + 2] = (rgb[2] * alpha + self.buf[i + 2] * inv) // 255

    def row(self, y, rgb):
        if y < 0 or y >= self.h:
            return
        i = y * self.w * 3
        self.buf[i:i + self.w * 3] = bytes(rgb) * self.w

    def disc(self, cx, cy, r, rgb, alpha=255):
        r = int(r)
        cx = int(cx)
        cy = int(cy)
        if r <= 0:
            return
        for y in range(cy - r, cy + r + 1):
            dy = y - cy
            half = int(math.sqrt(max(0, r * r - dy * dy)))
            for x in range(cx - half, cx + half + 1):
                self.put(x, y, rgb, alpha)

    def ellipse(self, cx, cy, rx, ry, rgb, alpha=255):
        rx = int(rx)
        ry = int(ry)
        cx = int(cx)
        cy = int(cy)
        if rx <= 0 or ry <= 0:
            return
        for y in range(cy - ry, cy + ry + 1):
            dy = (y - cy) / ry
            half = int(rx * math.sqrt(max(0.0, 1.0 - dy * dy)))
            for x in range(cx - half, cx + half + 1):
                self.put(x, y, rgb, alpha)

    def ring(self, cx, cy, r, thick, rgb, alpha=255):
        steps = max(48, int(r * 2.4))
        for s in range(steps):
            a = 2.0 * math.pi * s / steps
            self.disc(cx + r * math.cos(a), cy + r * math.sin(a),
                      thick / 2.0, rgb, alpha)

    def thick_line(self, x0, y0, x1, y1, width, rgb, alpha=255):
        dist = math.hypot(x1 - x0, y1 - y0)
        steps = max(2, int(dist * 1.5))
        for s in range(steps + 1):
            t = s / steps
            self.disc(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t,
                      width / 2.0, rgb, alpha)

    def rect(self, x0, y0, x1, y1, rgb, alpha=255):
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                self.put(x, y, rgb, alpha)


# ---------------------------------------------------------------- PNG output

def _chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data +
            struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def save_png(path, cv):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.buf[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    blob = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) +
            _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
            _chunk(b"IEND", b""))
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "wb") as f:
        f.write(blob)
    return len(blob)


# ------------------------------------------------------------------- scene

CREAM = (232, 220, 192)
NOODLE_LIGHT = (246, 214, 138)
NOODLE_DARK = (214, 164, 79)


def background(cv):
    top = (46, 30, 22)
    bottom = (18, 12, 9)
    for y in range(H):
        t = y / (H - 1)
        cv.row(y, (mix(top[0], bottom[0], t),
                   mix(top[1], bottom[1], t),
                   mix(top[2], bottom[2], t)))
    # warm glow behind the bowl
    for k in range(46, 0, -1):
        a = int(5 + 60 * (1 - k / 46) ** 2)
        cv.ellipse(512, 560, 330 + k * 9, 300 + k * 8,
                   (214, 140, 62), a)
    # table edge near the bottom
    cv.rect(0, 892, W, 900, (88, 58, 36), 110)
    # soft shadow under the bowl
    cv.ellipse(512, 940, 330, 42, (0, 0, 0), 90)


def bowl(cv):
    cx, cy = 512, 622
    cv.disc(cx, cy, 332, (24, 30, 66))
    cv.disc(cx, cy, 322, (34, 44, 96))
    # cream rim ring
    cv.ring(cx, cy, 306, 15, CREAM, 255)
    cv.ring(cx, cy, 306, 15, (120, 90, 60), 60)
    # thin red band just inside the rim
    cv.ring(cx, cy, 288, 7, (168, 50, 38), 255)
    # faint vertical sheen on the ceramic
    for k in range(20):
        cv.ellipse(300 + k * 2, 700, 26 - k, 130, (120, 140, 210), 4)


def broth(cv):
    cx, cy, rx, ry = 512, 592, 282, 170
    for y in range(cy - ry, cy + ry + 1):
        dy = (y - cy) / ry
        half = int(rx * math.sqrt(max(0.0, 1.0 - dy * dy)))
        t = (y - (cy - ry)) / (2 * ry)
        col = (mix(238, 158, t), mix(168, 88, t), mix(60, 18, t))
        for x in range(cx - half, cx + half + 1):
            cv.put(x, y, col)
    # glossy highlight near the top of the broth
    cv.ellipse(430, 500, 150, 34, (255, 214, 130), 46)
    cv.ellipse(430, 498, 90, 18, (255, 232, 170), 60)
    # oil droplets catching the light
    for (ox, oy, orad) in [(610, 540, 16), (660, 600, 11), (380, 620, 13),
                           (560, 660, 9), (700, 545, 8), (330, 545, 9)]:
        cv.disc(ox, oy, orad, (255, 196, 90), 70)
        cv.disc(ox - 3, oy - 3, max(2, orad // 3), (255, 240, 190), 110)


def noodles(cv):
    cx, cy, rx, ry = 512, 592, 282, 170
    for n in range(36):
        y0 = cy - 118 + n * 7
        amp = 9 + (n % 5) * 3
        freq = 0.045 + (n % 4) * 0.008
        phase = n * 1.7
        col = NOODLE_LIGHT if n % 3 else NOODLE_DARK
        x = cx - rx + 18
        while x < cx + rx - 18:
            y = y0 + amp * math.sin(x * freq + phase)
            inside = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if inside < 0.9:
                cv.disc(x, y, 4.5, col, 235)
            x += 3


def egg(cv, cx, cy):
    cv.ellipse(cx, cy + 6, 66, 46, (90, 50, 20), 110)
    cv.ellipse(cx, cy, 64, 44, (250, 244, 228))
    cv.ellipse(cx, cy, 58, 38, (246, 238, 220))
    cv.disc(cx, cy, 27, (242, 158, 8))
    cv.disc(cx, cy, 22, (250, 178, 32))
    cv.disc(cx - 7, cy - 8, 7, (255, 224, 130), 200)


def narutomaki(cv, cx, cy):
    cv.disc(cx, cy, 48, (250, 246, 236))
    cv.disc(cx, cy, 48, (250, 246, 236))
    for s in range(120):
        t = s / 119
        a = t * math.pi * 4.4
        r = 4 + t * 34
        cv.disc(cx + r * math.cos(a), cy + r * math.sin(a), 5,
                (238, 110, 140), 255)
    cv.disc(cx, cy, 7, (238, 110, 140))


def chashu(cv, cx, cy):
    cv.ellipse(cx, cy + 5, 78, 58, (90, 48, 26), 110)
    cv.ellipse(cx, cy, 76, 56, (198, 132, 100))
    cv.ellipse(cx, cy, 58, 40, (224, 168, 132))
    cv.ellipse(cx, cy, 34, 22, (240, 196, 158))
    cv.ellipse(cx - 6, cy - 4, 12, 8, (176, 108, 76), 160)


def green_onions(cv):
    spots = [(430, 660, 11), (470, 690, 9), (600, 680, 10), (640, 640, 9),
             (350, 600, 9), (690, 590, 8), (520, 700, 9), (560, 540, 8),
             (400, 560, 8), (680, 660, 9), (480, 620, 8), (600, 560, 8)]
    for (x, y, r) in spots:
        cv.ring(x, y, r, 5, (74, 158, 60), 255)
        cv.disc(x, y, max(2, r - 5), (168, 214, 110), 220)


def nori(cv):
    cv.rect(742, 512, 826, 636, (26, 44, 24))
    cv.rect(748, 518, 820, 630, (34, 58, 30))
    cv.thick_line(756, 526, 756, 622, 3, (74, 104, 60), 120)


def chopsticks(cv):
    cv.thick_line(648, 330, 968, 262, 13, (138, 90, 46))
    cv.thick_line(660, 356, 972, 292, 13, (122, 78, 40))
    cv.thick_line(648, 330, 968, 262, 13, (196, 150, 96), 70)
    cv.thick_line(660, 356, 972, 292, 13, (182, 138, 88), 60)


def steam(cv):
    for base, phase in [(428, 0.0), (512, 2.1), (596, 4.2)]:
        y = 470
        while y > 140:
            sway = 30 * math.sin(y * 0.018 + phase)
            width = 24 + 14 * math.sin(y * 0.03 + phase)
            alpha = int(9 + 13 * (0.5 + 0.5 * math.sin(y * 0.05 + phase)))
            cv.ellipse(int(base + sway), y, int(width), 15,
                       (255, 244, 226), alpha)
            y -= 5


def build():
    cv = Canvas(W, H)
    background(cv)
    bowl(cv)
    broth(cv)
    noodles(cv)
    egg(cv, 388, 528)
    egg(cv, 636, 512)
    narutomaki(cv, 512, 652)
    chashu(cv, 300, 640)
    chashu(cv, 716, 640)
    green_onions(cv)
    nori(cv)
    chopsticks(cv)
    steam(cv)
    return cv


def main():
    out = os.environ.get("ENTRY_PNG", "/output/entry.png")
    cv = build()
    size = save_png(out, cv)
    print(f"wrote {out} ({size} bytes, {W}x{H})")


if __name__ == "__main__":
    main()
