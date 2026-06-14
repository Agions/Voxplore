#!/usr/bin/env python3
"""Generate and validate application resource assets without external packages."""

from __future__ import annotations

import argparse
import binascii
import shutil
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "resources"
ICONS = RESOURCES / "icons"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = hex_color.lstrip("#")
    return (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
        alpha,
    )


def lerp(a: tuple[int, ...], b: tuple[int, ...], t: float) -> tuple[int, ...]:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(4))


def png_chunk(kind: bytes, data: bytes) -> bytes:
    checksum = binascii.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)


def write_png(path: Path, width: int, height: int, pixels: bytes | bytearray) -> None:
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)
        raw.extend(pixels[y * stride : (y + 1) * stride])
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    path.write_bytes(
        b"".join(
            [
                PNG_SIGNATURE,
                png_chunk(b"IHDR", ihdr),
                png_chunk(b"IDAT", zlib.compress(bytes(raw), 9)),
                png_chunk(b"IEND", b""),
            ]
        )
    )


def inside_rounded_rect(
    x: float, y: float, x0: int, y0: int, x1: int, y1: int, radius: int
) -> bool:
    if x < x0 or x > x1 or y < y0 or y > y1:
        return False
    cx = min(max(x, x0 + radius), x1 - radius)
    cy = min(max(y, y0 + radius), y1 - radius)
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius**2


class Canvas:
    def __init__(self, size: int, scale: int):
        self.size = size
        self.scale = scale
        self.n = size * scale
        self.pixels = bytearray(self.n * self.n * 4)

    def blend_px(self, x: int, y: int, color: tuple[int, int, int, int]) -> None:
        if not (0 <= x < self.n and 0 <= y < self.n):
            return
        sr, sg, sb, sa = color
        if sa <= 0:
            return
        offset = (y * self.n + x) * 4
        dr, dg, db, da = self.pixels[offset : offset + 4]
        inv = 255 - sa
        out_a = sa + (da * inv + 127) // 255
        if out_a == 0:
            self.pixels[offset : offset + 4] = b"\x00\x00\x00\x00"
            return
        out_r = (sr * sa + dr * da * inv // 255) // out_a
        out_g = (sg * sa + dg * da * inv // 255) // out_a
        out_b = (sb * sa + db * da * inv // 255) // out_a
        self.pixels[offset : offset + 4] = bytes((out_r, out_g, out_b, out_a))

    def set_px(self, x: int, y: int, color: tuple[int, int, int, int]) -> None:
        if 0 <= x < self.n and 0 <= y < self.n:
            offset = (y * self.n + x) * 4
            self.pixels[offset : offset + 4] = bytes(color)

    def rounded_rect(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        radius: float,
        color: tuple[int, int, int, int],
    ) -> None:
        ix0, iy0, ix1, iy1, ir = map(round, (x0, y0, x1, y1, radius))
        for y in range(iy0, iy1 + 1):
            for x in range(ix0, ix1 + 1):
                if inside_rounded_rect(x + 0.5, y + 0.5, ix0, iy0, ix1, iy1, ir):
                    self.blend_px(x, y, color)

    def rr_gradient(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        radius: float,
        top: tuple[int, int, int, int],
        bottom: tuple[int, int, int, int],
    ) -> None:
        ix0, iy0, ix1, iy1, ir = map(round, (x0, y0, x1, y1, radius))
        for y in range(iy0, iy1 + 1):
            t = 0 if iy1 == iy0 else (y - iy0) / (iy1 - iy0)
            base = lerp(top, bottom, t)
            for x in range(ix0, ix1 + 1):
                if inside_rounded_rect(x + 0.5, y + 0.5, ix0, iy0, ix1, iy1, ir):
                    self.set_px(x, y, base)

    def circle(self, cx: float, cy: float, radius: float, color: tuple[int, int, int, int]) -> None:
        scaled_cx = cx * self.n
        scaled_cy = cy * self.n
        scaled_radius = radius * self.n
        radius_sq = scaled_radius * scaled_radius
        x0 = max(0, int(scaled_cx - scaled_radius))
        x1 = min(self.n - 1, int(scaled_cx + scaled_radius))
        y0 = max(0, int(scaled_cy - scaled_radius))
        y1 = min(self.n - 1, int(scaled_cy + scaled_radius))
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                dx = x + 0.5 - scaled_cx
                dy = y + 0.5 - scaled_cy
                if dx * dx + dy * dy <= radius_sq:
                    self.blend_px(x, y, color)

    def line(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        width: float,
        color: tuple[int, int, int, int],
    ) -> None:
        sx0, sy0, sx1, sy1 = x0 * self.n, y0 * self.n, x1 * self.n, y1 * self.n
        radius = width * self.n / 2
        bx0 = max(0, int(min(sx0, sx1) - radius - 1))
        bx1 = min(self.n - 1, int(max(sx0, sx1) + radius + 1))
        by0 = max(0, int(min(sy0, sy1) - radius - 1))
        by1 = min(self.n - 1, int(max(sy0, sy1) + radius + 1))
        vx = sx1 - sx0
        vy = sy1 - sy0
        length_sq = vx * vx + vy * vy or 1
        radius_sq = radius * radius
        for y in range(by0, by1 + 1):
            for x in range(bx0, bx1 + 1):
                px = x + 0.5
                py = y + 0.5
                t = ((px - sx0) * vx + (py - sy0) * vy) / length_sq
                t = min(1, max(0, t))
                dx = px - (sx0 + t * vx)
                dy = py - (sy0 + t * vy)
                if dx * dx + dy * dy <= radius_sq:
                    self.blend_px(x, y, color)

    def downsample(self) -> bytearray:
        out = bytearray(self.size * self.size * 4)
        sample_count = self.scale * self.scale
        for y in range(self.size):
            for x in range(self.size):
                sum_a = sum_ra = sum_ga = sum_ba = 0
                for sy in range(self.scale):
                    yy = y * self.scale + sy
                    row = yy * self.n * 4
                    for sx in range(self.scale):
                        xx = x * self.scale + sx
                        offset = row + xx * 4
                        r, g, b, a = self.pixels[offset : offset + 4]
                        sum_a += a
                        sum_ra += r * a
                        sum_ga += g * a
                        sum_ba += b * a
                alpha = round(sum_a / sample_count)
                red = round(sum_ra / sum_a) if sum_a else 0
                green = round(sum_ga / sum_a) if sum_a else 0
                blue = round(sum_ba / sum_a) if sum_a else 0
                offset = (y * self.size + x) * 4
                out[offset : offset + 4] = bytes((red, green, blue, alpha))
        return out


def render_icon(size: int) -> bytearray:
    scale = 8 if size <= 64 else 4 if size <= 128 else 3 if size <= 256 else 2
    canvas = Canvas(size, scale)
    n = canvas.n

    cyan = rgba("#22d3ee")
    cyan_soft = rgba("#67e8f9", 210)
    white = rgba("#e5edf6")
    slate = rgba("#0f172a")
    green = rgba("#22c55e")
    rose = rgba("#f43f5e")

    margin = 0.07 * n
    canvas.rr_gradient(margin, margin, n - margin, n - margin, 0.18 * n, rgba("#132033"), rgba("#080f1f"))

    stroke = max(0.032, 2.2 / size)
    canvas.line(0.22, 0.25, 0.38, 0.25, stroke, cyan)
    canvas.line(0.22, 0.25, 0.22, 0.41, stroke, cyan)
    canvas.line(0.78, 0.25, 0.62, 0.25, stroke, cyan)
    canvas.line(0.78, 0.25, 0.78, 0.41, stroke, cyan)
    canvas.line(0.22, 0.60, 0.22, 0.48, stroke, cyan_soft)
    canvas.line(0.78, 0.60, 0.78, 0.48, stroke, cyan_soft)

    canvas.circle(0.50, 0.46, 0.18, white)
    canvas.circle(0.50, 0.46, 0.135, slate)
    canvas.circle(0.50, 0.46, 0.083, cyan)
    canvas.circle(0.53, 0.43, 0.032, rose)

    if size <= 64:
        bars = [(0.42, 0.10, green), (0.50, 0.15, cyan), (0.58, 0.10, rose)]
        bar_w = max(0.035, 2.0 / size)
        center_y = 0.72
    else:
        bars = [
            (0.30, 0.08, green),
            (0.38, 0.15, cyan),
            (0.46, 0.10, green),
            (0.54, 0.19, rose),
            (0.62, 0.12, cyan),
            (0.70, 0.08, green),
        ]
        bar_w = max(0.024, 2.0 / size)
        center_y = 0.70
    for x, height, color in bars:
        canvas.rounded_rect(
            (x - bar_w / 2) * n,
            (center_y - height / 2) * n,
            (x + bar_w / 2) * n,
            (center_y + height / 2) * n,
            bar_w * n / 2,
            color,
        )

    if size >= 64:
        canvas.rounded_rect(0.22 * n, 0.82 * n, 0.78 * n, 0.88 * n, 0.024 * n, rgba("#1f2937", 230))
        for x0, x1, color in [
            (0.25, 0.34, cyan),
            (0.37, 0.52, green),
            (0.55, 0.65, rose),
            (0.68, 0.75, cyan),
        ]:
            canvas.rounded_rect(x0 * n, 0.835 * n, x1 * n, 0.865 * n, 0.012 * n, color)

    return canvas.downsample()


def generate() -> None:
    ICONS.mkdir(parents=True, exist_ok=True)
    pngs = {size: render_icon(size) for size in (16, 32, 64, 128, 256, 512, 1024)}
    for size in (32, 64, 128, 256, 512):
        write_png(ICONS / f"app_icon_{size}.png", size, size, pngs[size])
    write_png(ICONS / "app_icon.png", 512, 512, pngs[512])

    ico_png = (ICONS / "app_icon_256.png").read_bytes()
    ico_header = struct.pack("<HHH", 0, 1, 1)
    ico_entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(ico_png), 22)
    (RESOURCES / "icon.ico").write_bytes(ico_header + ico_entry + ico_png)

    if shutil.which("iconutil"):
        with tempfile.TemporaryDirectory() as tmp:
            iconset = Path(tmp) / "AppIcon.iconset"
            iconset.mkdir()
            for name, size in {
                "icon_16x16.png": 16,
                "icon_16x16@2x.png": 32,
                "icon_32x32.png": 32,
                "icon_32x32@2x.png": 64,
                "icon_128x128.png": 128,
                "icon_128x128@2x.png": 256,
                "icon_256x256.png": 256,
                "icon_256x256@2x.png": 512,
                "icon_512x512.png": 512,
                "icon_512x512@2x.png": 1024,
            }.items():
                write_png(iconset / name, size, size, pngs[size])
            output = Path(tmp) / "icon.icns"
            subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(output)], check=True)
            shutil.copyfile(output, RESOURCES / "icon.icns")


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != PNG_SIGNATURE:
        raise ValueError(f"{path} is not a PNG")
    return struct.unpack(">II", data[16:24])


def check() -> None:
    expected_pngs = {
        ICONS / "app_icon.png": (512, 512),
        ICONS / "app_icon_32.png": (32, 32),
        ICONS / "app_icon_64.png": (64, 64),
        ICONS / "app_icon_128.png": (128, 128),
        ICONS / "app_icon_256.png": (256, 256),
        ICONS / "app_icon_512.png": (512, 512),
    }
    for path, expected in expected_pngs.items():
        actual = png_size(path)
        if actual != expected:
            raise SystemExit(f"{path}: expected {expected}, got {actual}")

    ico = (RESOURCES / "icon.ico").read_bytes()
    if ico[:4] != b"\x00\x00\x01\x00":
        raise SystemExit("resources/icon.ico is not a Windows icon")

    icns = RESOURCES / "icon.icns"
    if icns.exists() and icns.read_bytes()[:4] != b"icns":
        raise SystemExit("resources/icon.icns is not a macOS icon")

    for path in (RESOURCES / "styles").glob("*.qss"):
        text = path.read_text(encoding="utf-8").lower()
        for banned in ("oklch", "voxplore", "ai video narrator", "clipflowcut"):
            if banned in text:
                raise SystemExit(f"{path}: legacy token found: {banned}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["generate", "check"])
    args = parser.parse_args()
    if args.command == "generate":
        generate()
    check()
    print(f"resources {args.command}: ok")


if __name__ == "__main__":
    main()
