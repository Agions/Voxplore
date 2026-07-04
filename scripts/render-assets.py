#!/usr/bin/env python3
"""
render-assets.py — SceneFab 品牌资产渲染/同步脚本

核心职责:
  1. SVG 源 → 多尺寸 PNG 衍生品 (assets/, resources/icons/, docs/public/)
  2. 多尺寸 PNG → 单文件 favicon.ico (Windows 兼容)
  3. 跨目录同步 (assets/ = single source of truth)

设计原则 (依据 frame-fab 2026-07-02 实战 + project-brand-redesign skill):
  - SVG 是 single source of truth, PNG 全部由 SVG 生成
  - 一次跑通, 跨 3 个目录同步
  - 失败时给出明确错误 (不静默)

用法:
  python3 scripts/render-assets.py            # 完整渲染 (本地/CI)
  python3 scripts/render-assets.py --check     # 只校验不写文件 (CI gate)
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS_SVG = ROOT / "assets"
RESOURCES_ICONS = ROOT / "resources" / "icons"
DOCS_PUBLIC = ROOT / "docs" / "public"


def render_svg_to_png(svg_path: Path, png_path: Path, size: int) -> None:
    """SVG → 指定尺寸 PNG (保留 alpha 透明)"""
    png_path.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(
        url=str(svg_path),
        write_to=str(png_path),
        output_width=size,
        output_height=size,
    )


def render_master_logo() -> None:
    """assets/logo-mark.svg → 4 尺寸 PNG (主品牌, dark 版)"""
    src = ASSETS_SVG / "logo-mark.svg"
    if not src.exists():
        raise FileNotFoundError(f"missing source: {src}")

    for size in [128, 256, 512, 1024]:
        render_svg_to_png(src, ASSETS_SVG / f"logo-{size}.png", size)
        print(f"  [ok] assets/logo-{size}.png")

    # light 主题变体 (v2.4.0)
    src_light = ASSETS_SVG / "logo-mark-light.svg"
    if src_light.exists():
        for size in [128, 256, 512, 1024]:
            render_svg_to_png(src_light, ASSETS_SVG / f"logo-light-{size}.png", size)
        print(f"  [ok] assets/logo-light-{128,256,512,1024}.png")


def render_app_icon() -> None:
    """resources/app_icon.svg → 6 尺寸 PNG (桌面图标全套)"""
    src = ROOT / "resources" / "app_icon.svg"
    if not src.exists():
        raise FileNotFoundError(f"missing source: {src}")

    sizes = [32, 64, 128, 256, 512, 1024]
    for size in sizes:
        render_svg_to_png(src, RESOURCES_ICONS / f"app_icon_{size}.png", size)
        print(f"  [ok] resources/icons/app_icon_{size}.png")

    # 默认名 (512) - resources/icons/app_icon.png (向后兼容)
    render_svg_to_png(src, RESOURCES_ICONS / "app_icon.png", 512)
    print(f"  [ok] resources/icons/app_icon.png")


def render_favicon() -> None:
    """docs/public/favicon.svg → favicon.png (256) + favicon.ico (多尺寸)"""
    src = DOCS_PUBLIC / "favicon.svg"
    if not src.exists():
        raise FileNotFoundError(f"missing source: {src}")

    # 主 favicon (PNG, 256)
    render_svg_to_png(src, DOCS_PUBLIC / "favicon.png", 256)
    print(f"  [ok] docs/public/favicon.png")

    # 多尺寸 favicon.ico (浏览器/Windows 兼容)
    tmp = DOCS_PUBLIC / "_tmp_favicon.png"
    cairosvg.svg2png(url=str(src), write_to=str(tmp), output_width=512, output_height=512)
    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    Image.open(tmp).save(DOCS_PUBLIC / "favicon.ico", format="ICO", sizes=ico_sizes)
    tmp.unlink()
    print(f"  [ok] docs/public/favicon.ico (sizes={ico_sizes})")


def render_og_image() -> None:
    """生成 OG image (1280×640, 用于社交媒体卡片)"""
    # OG image 是临时合成的: 用 logo-horizontal 作为核心 + 大背景
    src = ASSETS_SVG / "logo-horizontal.svg"
    if not src.exists():
        raise FileNotFoundError(f"missing source: {src}")

    # 渲染 logo-horizontal 大图
    tmp = DOCS_PUBLIC / "_tmp_og.png"
    cairosvg.svg2png(url=str(src), write_to=str(tmp), output_width=1024, output_height=320)

    # 拼接到 OG 画布 (1280×640)
    canvas = Image.new("RGB", (1280, 640), (5, 8, 22))  # 深空黑底
    logo_img = Image.open(tmp).convert("RGBA")
    # 居中
    x = (canvas.width - logo_img.width) // 2
    y = (canvas.height - logo_img.height) // 2 - 20
    canvas.paste(logo_img, (x, y), logo_img)
    logo_img.close()

    # 加 subtle gradient overlay (左上 → 右下, cyan → violet)
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    for i in range(canvas.width):
        alpha = int(40 * (1 - i / canvas.width))  # 左侧更亮
        for j in range(canvas.height):
            beta = int(60 * (j / canvas.height))
            overlay.putpixel((i, j), (34, 211, 238, max(0, alpha - beta // 3)))
    canvas.paste(overlay, (0, 0), overlay)

    # 加 tagline (用大字体)
    try:
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(canvas)
        # 找字体
        font_paths = [
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        ]
        font_path = next((f for f in font_paths if Path(f).exists()), None)
        if font_path:
            big = ImageFont.truetype(font_path, 32)
            small = ImageFont.truetype(font_path, 18)
        else:
            big = ImageFont.load_default()
            small = ImageFont.load_default()

        # 顶部小字
        tag1 = "AI VIDEO NARRATION · FIRST-PERSON MONOLOGUE"
        draw.text((640, 80), tag1, anchor="mm", fill=(165, 180, 200), font=small)
        # 底部小字
        tag2 = "github.com/Agions/scene-fab"
        draw.text((640, 560), tag2, anchor="mm", fill=(165, 180, 200), font=small)
    except Exception:
        pass

    canvas.save(DOCS_PUBLIC / "og-image.png", "PNG", optimize=True)
    print(f"  [ok] docs/public/og-image.png (1280x640)")

    tmp.unlink(missing_ok=True)


def sync_to_docs_public() -> None:
    """跨目录同步: assets/ → docs/public/ (VitePress 服务)"""
    DOCS_PUBLIC.mkdir(parents=True, exist_ok=True)

    # 同步 logo-mark.svg → logo.svg (dark 主题默认)
    if (ASSETS_SVG / "logo-mark.svg").exists():
        shutil.copy(ASSETS_SVG / "logo-mark.svg", DOCS_PUBLIC / "logo.svg")
        print(f"  [sync] docs/public/logo.svg ← assets/logo-mark.svg")

    # 同步 logo-mark-light.svg → logo-light.svg (light 主题变体)
    if (ASSETS_SVG / "logo-mark-light.svg").exists():
        shutil.copy(ASSETS_SVG / "logo-mark-light.svg", DOCS_PUBLIC / "logo-light.svg")
        print(f"  [sync] docs/public/logo-light.svg ← assets/logo-mark-light.svg")

    # 同步 logo-horizontal.svg
    if (ASSETS_SVG / "logo-horizontal.svg").exists():
        shutil.copy(ASSETS_SVG / "logo-horizontal.svg", DOCS_PUBLIC / "logo-horizontal.svg")
        print(f"  [sync] docs/public/logo-horizontal.svg ← assets/logo-horizontal.svg")

    # 同步 logo-horizontal-light.svg
    if (ASSETS_SVG / "logo-horizontal-light.svg").exists():
        shutil.copy(ASSETS_SVG / "logo-horizontal-light.svg", DOCS_PUBLIC / "logo-horizontal-light.svg")
        print(f"  [sync] docs/public/logo-horizontal-light.svg ← assets/logo-horizontal-light.svg")


def verify_png_files() -> int:
    """校验所有 PNG 不是空白"""
    print("\n=== 验证 PNG 文件 ===")
    errors = 0
    png_dirs = [ASSETS_SVG, RESOURCES_ICONS, DOCS_PUBLIC]
    for d in png_dirs:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.png")):
            try:
                img = Image.open(f).convert("RGB")
                # Use numpy-style iteration via getdata() for speed
                # (Pillow 14 deprecates getdata; we use it here for Pillow 11 compat)
                pixels = list(img.getdata())
                avg = sum(p[0] for p in pixels) / len(pixels)
                nonblack = sum(1 for p in pixels if max(p) > 30) / len(pixels)
                if not (5 < avg < 250):
                    print(f"  [FAIL] {f}: blank (avg={avg:.0f})")
                    errors += 1
                elif nonblack < 0.3:
                    print(f"  [WARN] {f}: mostly blank ({nonblack*100:.0f}%)")
                else:
                    print(f"  [ok] {f.name}: {img.size}, nonblack={nonblack*100:.0f}%")
            except Exception as e:
                print(f"  [FAIL] {f}: {e}")
                errors += 1
    return errors


def main(check_only: bool = False) -> int:
    print(f"=== SceneFab Brand Assets Renderer ===")
    print(f"ROOT: {ROOT}")
    print()

    if check_only:
        print("[check-only mode] 仅校验, 不写文件")
        return verify_png_files()

    print("[1/5] 渲染主 logo-mark.svg → 4 尺寸 PNG")
    render_master_logo()
    print()
    print("[2/5] 渲染 resources/app_icon.svg → 6 尺寸 PNG")
    render_app_icon()
    print()
    print("[3/5] 渲染 docs/public/favicon.svg → favicon.png + favicon.ico")
    render_favicon()
    print()
    print("[4/5] 生成 og-image.png (1280x640, 社交卡片)")
    render_og_image()
    print()
    print("[5/5] 跨目录同步 (assets/ → docs/public/)")
    sync_to_docs_public()
    print()

    errors = verify_png_files()
    if errors:
        print(f"\n[FAIL] {errors} errors found")
        return 1

    print("\n[OK] 所有品牌资产已生成")
    return 0


if __name__ == "__main__":
    check_only = "--check" in sys.argv
    sys.exit(main(check_only=check_only))