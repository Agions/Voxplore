# Resources

This directory contains the visual resource layer for the first-person video
narration production app. Resources should stay behavior-free: Python modules
own runtime logic, while this directory owns icons, platform app assets, and Qt
style sheets.

## Design Direction

- Use product-neutral naming. Resource files should not include legacy project
  names or internal package names.
- Keep the app icon text-free so it remains readable at dock, taskbar, tray, and
  installer sizes.
- Use a visual language tied to the workflow: first-person lens, narration
  waveform, and editing timeline.
- Keep both light and dark themes dense, quiet, and production-oriented for
  repeated script, audio, video, and export work.
- Prefer Qt-compatible HEX colors and stable QSS selectors over experimental CSS
  color functions.

## File Responsibilities

```text
resources/
├── icon.icns                 # macOS application bundle icon
├── icon.ico                  # Windows installer/application icon
├── app_icon.svg              # 主源 SVG (无文字, 符合 text-free 设计原则)
├── icons/
│   ├── app_icon.png          # 512 px Linux/default application icon
│   ├── app_icon_32.png       # small toolbar/tray/title icon
│   ├── app_icon_64.png       # medium toolbar/window icon
│   ├── app_icon_128.png      # launcher icon
│   ├── app_icon_256.png      # high-density launcher icon
│   ├── app_icon_512.png      # source-size application icon
│   └── app_icon_1024.png     # ultra-high-density (1024 px)
```

> Note: legacy `light_theme.qss` / `dark_theme.qss` (Python v2.4 PySide6 主题)
> 在 v2.5.0 收官清理中已移除 — 当前主题系统使用 `apps/desktop/src/styles/globals.css`
> 的 Tailwind 4 设计令牌（`@theme` blocks + CSS variables），运行时通过
> `useThemeStore` 切换。

## Brand Identity (v2.5.0 重设计)

SceneFab 品牌识别系统由以下 SVG 资产构成（详见 `assets/logo-mark.svg` /
`assets/logo-horizontal.svg` / `docs/public/favicon.svg`）：

| 资产                         | 用途                                    | viewBox  |
| ---------------------------- | --------------------------------------- | -------- |
| `assets/logo-mark.svg`       | 方形主标识符 · 应用图标 · OG image 核心 | 256×256  |
| `assets/logo-horizontal.svg` | README 头部 · VitePress nav · 横版卡片  | 512×128  |
| `docs/public/favicon.svg`    | 浏览器标签 · 极简化（32×32 优化）       | 32×32    |
| `docs/public/og-image.png`   | 社交媒体卡片（GitHub/Twitter/微博）     | 1280×640 |
| `docs/public/icons/*.svg`    | docs 站 6 个 24×24 功能图标（双色调）   | 24×24    |

**核心识别符**：Play 三角（视频）+ 双环轨道（流水线）+ AI 弧线（AI 处理）

**品牌色系**：

- 主色 cyan：`#22d3ee → #06b6d4`（深空蓝青渐变）
- 强调 violet：`#a855f7`（AI 模块 / 重点步骤）
- 高光：`#67e8f9`（顶部亮线 / 点缀）
- 底色：`#050816 → #0f172a`（深空黑，深色主题优先）

**6 个功能图标**（docs/public/icons/）：cyan 主结构 + violet AI 模块强调（双色调，
1.75 stroke, round caps）。

**渲染 / 同步 pipeline**：`scripts/render-assets.py` 一键端到端生成所有品牌资产
（SVG → 多尺寸 PNG → 多尺寸 ICO → OG image → 跨目录同步）。

## Runtime Scope

Resources here are loaded by the desktop app and packaging targets only. Keep
workflow media, screenshots, temporary exports, and draft experiments outside
this directory unless they are part of a shipped screen.
