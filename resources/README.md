# Resources

本目录是 Monoloop 桌面端的**视觉资源层**,存放图标、应用资产和品牌素材。资源层
不承担运行时逻辑——Rust 后端 (monoloop-core / monoloop-assets) 与 React 前端
(apps/desktop) 负责行为,本目录只提供可加载的资产。

## 设计方向

- 采用**产品中立**的命名。资源文件不应携带旧项目名或内部包名。
- 应用图标保持**无文字**,以保证 dock / 任务栏 / 托盘 / 安装器尺寸下都清晰可辨。
- 视觉语言紧扣工作流:第一人称镜头、解说波形、剪辑时间线。
- 浅色 / 深色双主题保持**密度、克制、生产导向**,适应长时间脚本、配音、剪辑、导出作业。
- 色彩与排版优先使用 **CSS 现代特性** (oklch / color-mix / 容器查询),避免过时的
  Qt QSS 选择器语义。

## 文件职责

```text
resources/
├── icon.icns                 # macOS 应用包图标
├── icon.ico                  # Windows 安装包/应用图标
├── app_icon.svg              # 主源 SVG (无文字, 符合 text-free 设计原则)
├── icons/
│   ├── app_icon.png          # 512 px Linux / 默认应用图标
│   ├── app_icon_32.png       # 小尺寸工具栏 / 托盘 / 窗口图标
│   ├── app_icon_64.png       # 中尺寸工具栏 / 窗口图标
│   ├── app_icon_128.png      # 启动器图标
│   ├── app_icon_256.png      # 高密度启动器图标
│   ├── app_icon_512.png      # 源尺寸应用图标
│   └── app_icon_1024.png     # 超高密度 (1024 px)
```

> Note: v2.4 PySide6 时代的 `light_theme.qss` / `dark_theme.qss` 已在 v1.0.0 
> 收官清理中删除。当前主题系统使用 `apps/desktop/src/styles/globals.css` 的
> Tailwind 4 设计令牌 (`@theme` blocks + CSS 变量),运行时通过
> `useThemeStore` 切换。

## 品牌识别 (v1.0.0  重设计)

Monoloop 品牌识别系统由以下 SVG 资产构成 (详见 `assets/logo-mark.svg` /
`assets/logo-horizontal.svg` / `docs/public/favicon.svg`):

| 资产                         | 用途                                    | viewBox  |
| ---------------------------- | --------------------------------------- | -------- |
| `assets/logo-mark.svg`       | 方形主标识符 · 应用图标 · OG image 核心 | 256×256  |
| `assets/logo-horizontal.svg` | README 头部 · VitePress nav · 横版卡片  | 512×128  |
| `docs/public/favicon.svg`    | 浏览器标签 · 极简化 (32×32 优化)        | 32×32    |
| `docs/public/og-image.png`   | 社交媒体卡片 (GitHub / Twitter / 微博)  | 1280×640 |
| `docs/public/icons/*.svg`    | docs 站 6 个 24×24 功能图标 (双色调)    | 24×24    |

**核心识别符**:Play 三角 (视频) + 双环轨道 (流水线) + AI 弧线 (AI 处理)

**品牌色系**:

- 主色 cyan:`#22d3ee → #06b6d4` (深空蓝青渐变)
- 强调 violet:`#a855f7` (AI 模块 / 重点步骤)
- 高光:`#67e8f9` (顶部亮线 / 点缀)
- 底色:`#050816 → #0f172a` (深空黑,深色主题优先)

**6 个功能图标** (docs/public/icons/):cyan 主结构 + violet AI 模块强调 (双色调,
1.75 stroke, round caps)。

**资产同步**:设计稿直接落地为 SVG 源文件 (存放于 `assets/`),PNG/ICO 多尺寸
通过各平台打包工具 (Tauri bundler) 在构建时生成;设计师在 Figma 调整后,SVG
由人工或脚本同步到 `assets/` 目录,不需要额外的 Python 渲染脚本。

## 运行时范围

本目录资源仅供桌面应用与打包目标加载。**工作流媒体、截图、临时导出、草稿实验
**应放在本目录之外,除非它们是已发布的某个屏幕的一部分。
