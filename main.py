#!/usr/bin/env python3
"""Steaming bowl of ramen, drawn procedurally. Pure stdlib, no network.

Writes one 1024x1024 PNG to /output/entry.png (or $ENTRY_PNG when set).
PNG encoder written by hand with zlib + struct.
"""

import math
import os
import random
import struct
import zlib

W = 1024
H = 1024


def clamp(v, lo=0, hi=255):
    return lo if v < lo else hi if v > hi else v


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def put(self, x, y, rgb, alpha=1.0):
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return
        i = (y * self.w + x) * 3
        if alpha >= 1.0:
            self.px[i] = rgb[0]
            self.px[i + 1] = rgb[1]
            self.px[i + 2] = rgb[2]
        else:
            ia = 1.0 - alpha
            self.px[i] = int(self.px[i] * ia + rgb[0] * alpha)
            self.px[i + 1] = int(self.px[i + 1] * ia + rgb[1] * alpha)
            self.px[i + 2] = int(self.px[i + 2] * ia + rgb[2] * alpha)

    def hline(self, x0, x1, y, rgb, alpha=1.0):
        if y < 0 or y >= self.h:
            return
        x0 = max(0, int(x0))
        x1 = min(self.w - 1, int(x1))
        if x1 < x0:
            return
        i = (y * self.w + x0) * 3
        if alpha >= 1.0:
            for _ in range(x0, x1 + 1):
                self.px[i] = rgb[0]
                self.px[i + 1] = rgb[1]
                self.px[i + 2] = rgb[2]
                i += 3
        else:
            ia = 1.0 - alpha
            for _ in range(x0, x1 + 1):
                self.px[i] = int(self.px[i] * ia + rgb[0] * alpha)
                self.px[i + 1] = int(self.px[i + 1] * ia + rgb[1] * alpha)
                self.px[i + 2] = int(self.px[i + 2] * ia + rgb[2] * alpha)
                i += 3

    def ellipse(self, cx, cy, rx, ry, rgb, alpha=1.0):
        for y in range(int(cy - ry), int(cy + ry) + 1):
            dy = (y - cy) / ry
            if abs(dy) > 1.0:
                continue
            dx = rx * math.sqrt(1.0 - dy * dy)
            self.hline(cx - dx, cx + dx, y, rgb, alpha)

    def circle(self, cx, cy, r, rgb, alpha=1.0):
        self.ellipse(cx, cy, r, r, rgb, alpha)

    def ring(self, cx, cy, r_out, r_in, rgb, alpha=1.0):
        for y in range(int(cy - r_out), int(cy + r_out) + 1):
            dy = y - cy
            for x in range(int(cx - r_out), int(cx + r_out) + 1):
                dx = x - cx
                d = math.sqrt(dx * dx + dy * dy)
                if r_in <= d <= r_out:
                    self.put(x, y, rgb, alpha)

    def thick_line(self, x0, y0, x1, y1, width, rgb, alpha=1.0):
        r = width / 2.0
        xlo = int(min(x0, x1) - r - 1)
        xhi = int(max(x0, x1) + r + 1)
        ylo = int(min(y0, y1) - r - 1)
        yhi = int(max(y0, y1) + r + 1)
        dx = x1 - x0
        dy = y1 - y0
        ln2 = dx * dx + dy * dy
        for y in range(ylo, yhi + 1):
            for x in range(xlo, xhi + 1):
                if ln2 == 0:
                    d = math.hypot(x - x0, y - y0)
                else:
                    t = ((x - x0) * dx + (y - y0) * dy) / ln2
                    t = 0.0 if t < 0 else 1.0 if t > 1 else t
                    d = math.hypot(x - (x0 + t * dx), y - (y0 + t * dy))
                if d <= r:
                    # soft edge
                    a = alpha if d <= r - 1.0 else alpha * max(0.0, r - d)
                    self.put(x, y, rgb, a)

    def polyline(self, pts, width, rgb, alpha=1.0):
        for i in range(len(pts) - 1):
            self.thick_line(pts[i][0], pts[i][1], pts[i + 1][0],
                            pts[i + 1][1], width, rgb, alpha)

    def arc_points(self, cx, cy, rx, ry, a0, a1, steps=40):
        pts = []
        for i in range(steps + 1):
            a = a0 + (a1 - a0) * i / steps
            pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
        return pts

    def save_png(self, path):
        raw = bytearray()
        stride = self.w * 3
        for y in range(self.h):
            row = self.px[y * stride:(y + 1) * stride]
            # filter 1 (Sub): each byte minus the byte 3 positions back
            raw.append(1)
            for i in range(stride):
                prev = row[i - 3] if i >= 3 else 0
                raw.append((row[i] - prev) & 0xFF)
        comp = zlib.compress(bytes(raw), 6)
        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)

        def chunk(tag, data):
            c = struct.pack(">I", len(data)) + tag + data
            c += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
            return c

        png = b"\x89PNG\r\n\x1a\n"
        png += chunk(b"IHDR", ihdr)
        png += chunk(b"IDAT", comp)
        png += chunk(b"IEND", b"")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(png)
        return len(png)


def draw():
    c = Canvas(W, H)
    rnd = random.Random(20261123)

    # --- warm dark background, vertical gradient + warm glow ---
    top = (46, 24, 14)
    bot = (20, 10, 7)
    for y in range(H):
        t = y / (H - 1)
        c.hline(0, W - 1, y, mix(top, bot, t))
    # warm radial glow behind the bowl
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            d = math.hypot(x - 512, y - 430) / 620.0
            if d < 1.0:
                a = (1.0 - d) * 0.34
                c.put(x, y, (214, 120, 40), a)
                c.put(x + 1, y, (214, 120, 40), a)
                c.put(x, y + 1, (214, 120, 40), a)
                c.put(x + 1, y + 1, (214, 120, 40), a)

    # --- table shadow under the bowl ---
    c.ellipse(512, 872, 400, 62, (8, 4, 3), 0.55)

    # --- bowl: dark lacquered ceramic, wide rim ---
    c.ellipse(512, 560, 392, 312, (58, 26, 18))
    c.ellipse(512, 548, 392, 312, (74, 34, 22))
    # rim highlight, upper left
    pts = c.arc_points(512, 548, 372, 292, math.pi * 1.12, math.pi * 1.62, 60)
    c.polyline(pts, 9, (196, 110, 58), 0.8)
    # bowl body shading: darker lower half
    c.ellipse(512, 640, 380, 220, (40, 18, 12), 0.45)
    # foot ring so the bowl sits flat instead of looking like a ball
    c.ellipse(512, 858, 168, 30, (46, 20, 14))
    c.ellipse(512, 852, 168, 30, (88, 42, 26))
    c.ellipse(512, 850, 140, 22, (58, 26, 18))
    # inner rim ring
    c.ring(512, 540, 352, 338, (150, 76, 34), 0.9)

    # --- broth: rich golden surface ---
    for y in range(540 - 232, 540 + 232):
        dy = (y - 540) / 232.0
        if abs(dy) > 1.0:
            continue
        dx = 336 * math.sqrt(1.0 - dy * dy)
        t = (y - (540 - 232)) / 464.0
        col = mix((232, 158, 52), (176, 84, 22), t)
        c.hline(512 - dx, 512 + dx, y, col)
    # broth gloss: bright sweep upper left
    c.ellipse(400, 452, 190, 74, (255, 214, 130), 0.30)
    c.ellipse(430, 470, 120, 44, (255, 232, 170), 0.28)
    # chili oil dots
    for _ in range(26):
        ang = rnd.uniform(0, math.tau)
        rr = rnd.uniform(0.15, 0.92)
        x = 512 + 336 * rr * math.cos(ang) * 0.98
        y = 540 + 232 * rr * math.sin(ang) * 0.96
        r = rnd.uniform(4, 11)
        c.circle(x, y, r, (198, 52, 18), 0.75)

    # --- nori sheet, tucked at the back right ---
    for i in range(4):
        c.thick_line(688 + i * 3, 330, 700 + i * 3, 470, 26,
                     (24, 42, 26), 0.95)
    c.thick_line(700, 330, 712, 470, 6, (52, 84, 52), 0.5)

    # --- chashu slices: two glossy pork rounds ---
    for (cx, cy, r) in ((648, 512, 82), (560, 596, 74)):
        c.circle(cx, cy, r, (196, 116, 78))
        c.circle(cx, cy, r - 10, (214, 140, 96))
        c.circle(cx, cy, r - 34, (178, 96, 62))
        c.circle(cx, cy, r - 52, (206, 128, 86))
        c.ellipse(cx - 22, cy - 26, 34, 16, (255, 196, 150), 0.5)

    # --- noodle swirls: wavy cream strands across the broth ---
    noodle_cols = [(242, 211, 138), (232, 192, 110), (248, 224, 160)]
    # a lifted noodle mound in the middle, so the strands read as a heap
    for k in range(14):
        cx = 470 + (k % 5) * 22 - 40
        cy = 585 + (k // 5) * 20 - 18
        pts = c.arc_points(cx, cy, 52 - k, 20 - k * 0.6,
                           math.pi * 0.9, math.pi * 2.1, 22)
        pts = [(x, y) for (x, y) in pts
               if ((x - 512) / 330) ** 2 + ((y - 540) / 228) ** 2 < 0.98]
        if len(pts) > 3:
            c.polyline(pts, 9, noodle_cols[k % 3], 0.95)
    for k in range(52):
        cx = 512 + rnd.uniform(-240, 240)
        cy = 540 + rnd.uniform(-160, 150)
        rx = rnd.uniform(28, 95)
        ry = rx * rnd.uniform(0.28, 0.5)
        a0 = rnd.uniform(0, math.tau)
        span = rnd.uniform(1.2, 3.4)
        pts = c.arc_points(cx, cy, rx, ry, a0, a0 + span, 26)
        # keep strands inside the broth ellipse
        pts = [(x, y) for (x, y) in pts
               if ((x - 512) / 330) ** 2 + ((y - 540) / 228) ** 2 < 0.98]
        if len(pts) > 3:
            c.polyline(pts, rnd.uniform(7, 11),
                       noodle_cols[k % 3], 0.95)

    # --- soft egg: white half + glossy orange yolk ---
    c.ellipse(392, 470, 92, 66, (250, 244, 230))
    c.ellipse(392, 470, 92, 66, (238, 228, 208), 0.0)
    c.ellipse(398, 482, 74, 50, (244, 234, 214))
    c.circle(392, 470, 44, (246, 158, 26))
    c.circle(392, 470, 34, (252, 176, 44))
    c.ellipse(378, 452, 18, 10, (255, 226, 140), 0.9)
    c.ellipse(392, 470, 92, 66, (0, 0, 0), 0.0)  # no-op keeps shape crisp
    # egg edge shading
    pts = c.arc_points(392, 470, 90, 64, math.pi * 0.15, math.pi * 0.85, 30)
    c.polyline(pts, 5, (214, 200, 178), 0.8)

    # --- spring onion rings, scattered ---
    for _ in range(34):
        ang = rnd.uniform(0, math.tau)
        rr = rnd.uniform(0.2, 0.9)
        x = 512 + 330 * rr * math.cos(ang)
        y = 540 + 226 * rr * math.sin(ang)
        r = rnd.uniform(6, 12)
        col = rnd.choice([(74, 160, 74), (96, 190, 90), (52, 132, 60)])
        c.ring(x, y, r, r * 0.45, col, 0.95)
        c.circle(x, y, r * 0.45, (30, 80, 34), 0.9)

    # --- chopsticks resting on the rim, top right ---
    c.thick_line(742, 128, 566, 372, 20, (139, 90, 43))
    c.thick_line(772, 168, 596, 402, 20, (120, 76, 36))
    c.thick_line(742, 128, 700, 188, 20, (178, 128, 72))
    c.thick_line(772, 168, 730, 228, 20, (160, 112, 62))

    # --- steam: faint soft ribbons above the bowl ---
    for k in range(5):
        bx = 330 + k * 92 + rnd.uniform(-14, 14)
        pts = []
        for i in range(24):
            t = i / 23.0
            y = 345 - t * 200
            x = bx + math.sin(t * 4.4 + k * 1.7) * (14 + t * 20)
            pts.append((x, y))
        c.polyline(pts, 16, (255, 244, 228), 0.045)
        c.polyline(pts, 8, (255, 250, 240), 0.04)

    # --- vignette to pull the eye to the bowl ---
    for y in range(0, H, 3):
        for x in range(0, W, 3):
            d = math.hypot((x - 512) / 512.0, (y - 512) / 512.0)
            if d > 0.72:
                a = min(0.42, (d - 0.72) * 1.1)
                c.put(x, y, (10, 5, 3), a)
                c.put(x + 1, y, (10, 5, 3), a)
                c.put(x, y + 1, (10, 5, 3), a)
                c.put(x + 1, y + 1, (10, 5, 3), a)
                c.put(x + 2, y, (10, 5, 3), a)
                c.put(x, y + 2, (10, 5, 3), a)

    return c


def main():
    out = os.environ.get("ENTRY_PNG", "/output/entry.png")
    canvas = draw()
    size = canvas.save_png(out)
    print(f"wrote {out}: {size} bytes, {W}x{H}")


if __name__ == "__main__":
    main()
