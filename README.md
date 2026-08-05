<!-- markdownlint-disable MD060 MD040 MD041 MD047 -->

<div align="center">

<img src="assets/logo-horizontal.svg" alt="SceneFab" width="480"/>

# SceneFab · AI 影视解说视频创作工具

> **5 步流水线 · 智能拆条 → AI 解说 → TTS 配音 → 字幕合成 → 多平台导出**
> 把影视素材交给 AI,自动产出横转竖的短视频解说。

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=for-the-badge)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.5.0-success.svg?style=for-the-badge)](https://github.com/scenefab/scenefab/releases)
[![Rust](https://img.shields.io/badge/rust-1.85%2B-orange.svg?style=for-the-badge&logo=rust)](https://www.rust-lang.org)
[![Tauri](https://img.shields.io/badge/tauri-2-blueviolet.svg?style=for-the-badge&logo=tauri)](https://tauri.app)
[![React](https://img.shields.io/badge/react-19-149eca.svg?style=for-the-badge&logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/typescript-5.8-3178c6.svg?style=for-the-badge&logo=typescript)](https://www.typescriptlang.org)

</div>

---

## 🎬 项目定位

SceneFab 是一款基于 AI 的**第一人称视频叙事编辑器**,通过 5 步流水线自动将影视素材转换为适配
竖屏平台（B站 / 抖音 / 微信视频号 / YouTube Shorts 等）的完整解说视频。

从「原始素材」到「成品视频」,你只需要：

1. 📥 **导入**素材（视频 / 音频）
2. ✂️ **智能拆条**（情绪峰值 + 视角切换 + 关键帧识别）
3. 🤖 **AI 解说**（11 个 LLM Provider · 风格 / 桥段 / 集数自适应）
4. 🎙️ **TTS 配音**（Edge-TTS / OpenAI-TTS / GPT-SoVITS）+ 字幕合成
5. 📤 **多平台导出**（MP4 / MOV / 剪映草稿 + 8 平台预设）

---

## ✨ 核心能力矩阵

| 模块              | 能力                                        | 技术亮点                                            |
| ----------------- | ------------------------------------------- | --------------------------------------------------- |
| 🧠 **AI 解说**    | 短剧解说 / 影评 / 教学 / 故事化 4 种风格    | 11 LLM Provider · 5 维加权评估 · 流式 token 输出    |
| ✂️ **智能拆条**   | 关键帧 / 情绪峰值 / 视角切换 / 集数扫描     | FFmpeg 6.x 探测 · DAG 并行流水线 · 断点续传         |
| 🎙️ **TTS 配音**   | 中英日韩 4 语言 · 30+ 音色                  | Edge-TTS / OpenAI-TTS / GPT-SoVITS 三引擎           |
| 📝 **字幕合成**   | SRT / VTT / ASS · 中英双语 · 时间轴自动对齐 | 基于语音端点检测（VAD）+ 句子边界识别               |
| 🎨 **多平台导出** | 8 平台智能裁剪 + 平台专属封面               | MP4 / MOV / GIF / 剪映草稿(.draft) · 1080×1920 竖屏 |
| 🔌 **插件体系**   | WASM 插件运行时 · Provider 热插拔           | Provider 抽象 · 异步 retry · JSON 契约              |

---

## 🏗️ 架构总览

```
                ┌─────────────────────────────────────────────────┐
                │         SceneFab v2.5.0 (Tauri 2)               │
                │  ┌──────────────┐         ┌─────────────────┐   │
                │  │  React 19    │   IPC   │   Rust 13 crate │   │
                │  │  TanStack    │ ◄─────► │   Tauri 2.0     │   │
                │  │  Router/Query│  invoke │   + Capability  │   │
                │  │  Zustand     │  events │      ACL        │   │
                │  └──────┬───────┘         └────────┬────────┘   │
                │         │                          │            │
                │         ▼                          ▼            │
                │  ┌──────────────┐         ┌─────────────────┐   │
                │  │  Vite 7 SPA  │         │  LLM / TTS /    │   │
                │  │  shadcn/ui   │         │  FFmpeg /       │   │
                │  │  + Tailwind 4│         │  Export / …     │   │
                │  └──────────────┘         └─────────────────┘   │
                └─────────────────────────────────────────────────┘
```

### 后端 · Rust Workspace（13 crate）

```
crates/
├── scenefab-core          核心抽象 · 错误类型 · 跨 crate trait
├── scenefab-domain        业务模型 · DTO · 事件 schema
├── scenefab-ffmpeg        FFmpeg 6.x 安全封装 · 参数白名单
├── scenefab-llm           11 LLM Provider · 流式输出 · retry
├── scenefab-tts           3 TTS 引擎 · 语音端点检测
├── scenefab-video         视频元数据 · 缩略图 · 探测
├── scenefab-export        多平台导出 · 剪映草稿生成
├── scenefab-pipeline      5 步流水线状态机 · DAG 并行
├── scenefab-plugin        WASM 插件运行时 · Provider 热插拔
├── scenefab-update        auto-update 引擎 · 版本检查
├── scenefab-help          帮助文档 · FAQ · 快捷键索引
├── scenefab-i18n          多语言 · i18next 资源生成
└── scenefab-assets        素材管理 · 缩略图缓存 · 导入队列
```

### 前端 · React 19 单页应用

```
apps/desktop/src/
├── routes/                TanStack Router 文件式路由（6 页面）
├── components/            12 类组件(layout/home/production/assets/…)
├── hooks/                 useTauri{Command,Event,Query} + 业务 hook
├── stores/                7 个 Zustand store(theme/project/pipeline/…)
├── ipc/                   38 类型 + commands/events/errors/schema/client
├── lib/                   i18n / tokens / format / log 工具集
├── styles/                globals.css + Tailwind 4 设计令牌
└── workers/               Web Worker · pipeline ETA / dashboard 采样
```

---

## 🧰 技术栈

### 前端

| 类别 | 选型                                                           |
| ---- | -------------------------------------------------------------- |
| 框架 | React 19 · TypeScript 5.8（strict + noUncheckedIndexedAccess） |
| 路由 | TanStack Router v1.95（文件式路由 + devtools）                 |
| 数据 | TanStack Query v5.62 · Zustand v5 · XState v5                  |
| UI   | shadcn/ui · Tailwind CSS 4 · Radix Primitives · cmdk           |
| 构建 | Vite 7 · `@tauri-apps/cli` 2                                   |
| 测试 | Vitest 3.2 · Testing Library · Playwright 1.49                 |
| i18n | react-i18next 15 · i18next 24                                  |
| 通知 | Sonner toast · 系统原生 Notification（plugin）                 |

### 后端

| 类别       | 选型                                               |
| ---------- | -------------------------------------------------- |
| 运行时     | Rust 1.85+ · edition 2021 · unsafe_code = forbid   |
| 桌面壳     | Tauri 2.0 · 10 个 domain command + Capability ACL  |
| 序列化     | serde 1 · ts-rs 10（Rust→TS 自动类型生成）         |
| 异步       | tokio 1（full）· async-trait · futures             |
| HTTP       | reqwest 0.12（rustls-tls）· tokio-tungstenite 0.24 |
| 持久化     | sqlx 0.8（sqlite/postgres）· sled 0.34             |
| 插件运行时 | wasmtime 29 · wasmtime-wasi 29                     |
| 测试       | 内置测试 112 个 · mockall · proptest · rstest      |

### 构建 / 发布

| 类别     | 选型                                                  |
| -------- | ----------------------------------------------------- |
| 包管理   | pnpm 9（workspace）· Cargo workspace 14 member        |
| 类型生成 | `pnpm gen:ipc` 从 Rust `specta` 生成 TS 类型（38 个） |
| 桌面打包 | Tauri bundler（dmg / msi / AppImage / deb）           |
| 文档     | VitePress 1.6 + markdownlint-cli2 + cspell + lychee   |

---

## 🚀 快速开始

### 环境要求

| 工具           | 版本                                                 | 说明                                                           |
| -------------- | ---------------------------------------------------- | -------------------------------------------------------------- |
| Node.js        | ≥ 20.19                                              | LTS 推荐                                                       |
| pnpm           | ≥ 9.x                                                | `corepack enable && corepack prepare pnpm@latest --activate`   |
| Rust           | ≥ 1.85                                               | `rustup default stable && rustup update`                       |
| Tauri 系统依赖 | 见[官方文档](https://tauri.app/start/prerequisites/) | macOS: Xcode CLT · Windows: VS Build Tools · Linux: webkit2gtk |

### 安装与开发

```bash
# 1. 克隆仓库
git clone https://github.com/scenefab/scenefab.git
cd scenefab

# 2. 安装前端依赖
pnpm install

# 3. 启动 Tauri 开发模式（桌面窗口 + 前端 HMR）
cd apps/desktop
pnpm tauri:dev
```

### 常用命令（apps/desktop）

| 命令                 | 作用                                |
| -------------------- | ----------------------------------- |
| `pnpm dev`           | 启动 Vite dev server（仅前端）      |
| `pnpm tauri:dev`     | 启动完整 Tauri 开发模式             |
| `pnpm build`         | 前端生产构建（tsc + vite build）    |
| `pnpm tauri:build`   | 桌面端三平台打包                    |
| `pnpm typecheck`     | TypeScript 严格模式类型检查         |
| `pnpm lint`          | ESLint（`--max-warnings 0`）        |
| `pnpm format`        | Prettier 自动格式化                 |
| `pnpm test`          | Vitest 单次执行                     |
| `pnpm test:watch`    | Vitest 监听模式                     |
| `pnpm test:coverage` | Vitest + v8 覆盖率                  |
| `pnpm test:e2e`      | Playwright 端到端                   |
| `pnpm gen:ipc`       | 从 Rust specta 生成 TS 类型契约     |
| `pnpm gen:ipc:check` | 校验生成的 TS 类型是否最新（CI 用） |

### 常用命令（crates/）

```bash
# 工作区级
cargo check --workspace             # 编译检查（增量 < 1s）
cargo clippy --workspace --all-targets -- -D warnings   # 严格 lint
cargo test --workspace              # 运行全部 112 个 Rust 测试
cargo metadata --no-deps --format-version 1 | jq '.packages | length'   # 14 个 crate
```

### 文档站（docs/）

```bash
cd docs
npm install         # 首次
npm run docs:dev    # 本地预览 http://localhost:5173
npm run docs:build  # 生产构建 → docs/.vitepress/dist/
```

---

## 📁 项目结构（顶层）

```
scene-fab/
├── apps/desktop/                  Tauri 2 桌面应用
│   ├── src/                       React 19 前端
│   ├── src-tauri/                 Rust 入口 + Capability ACL
│   ├── e2e/                       Playwright 端到端
│   ├── scripts/gen-ipc.mjs        Rust→TS 类型生成
│   ├── vite.config.ts
│   └── package.json
├── crates/                        13 个 Rust 领域 crate
├── assets/                        Logo 与品牌资源（SVG + PNG 多尺寸）
├── resources/                     应用图标（icons/）+ 安装包素材
├── docs/                          VitePress 官方文档站（guide/ + index）
├── scripts/                       Cargo + pnpm + docs 工具脚本（coverage.sh / docs-check-*）
├── config/                        app_config.yaml / llm.yaml / logging.conf
├── Cargo.toml                     Rust workspace 根配置（14 member）
├── pnpm-workspace.yaml            前端 workspace
├── CHANGELOG.md                   完整变更日志（v1.0 → v2.4 → 2.5.0）
└── Makefile                       顶层构建入口（help / build / test / coverage）
```

---

## 🧪 测试与质量保障

SceneFab 严格遵守 **3 轨验证** 原则 — 任一失败则不能合并。

| 轨道     | 命令                                                    | 当前状态                               |
| -------- | ------------------------------------------------------- | -------------------------------------- |
| **Rust** | `cargo check --workspace`                               | ✅ 0 errors                            |
|          | `cargo clippy --workspace --all-targets -- -D warnings` | ✅ 0 warnings                          |
|          | `cargo test --workspace`                                | ✅ **112 / 112** PASS                  |
| **前端** | `pnpm exec tsc --noEmit`                                | ✅ EXIT=0                              |
|          | `pnpm exec vitest run`                                  | ✅ **157 / 157** PASS（11 test files） |
|          | `pnpm exec eslint . --ext ts,tsx --max-warnings 0`      | ✅ 0 warnings                          |
| **构建** | `pnpm build`（tsc + vite build）                        | ✅ 270 modules · 1.18s                 |
|          | `pnpm gen:ipc`（Rust→TS 类型同步）                      | ✅ 38 types generated                  |

> 全部命令在 commit 后立即复跑于本地,任何红灯都会阻断 PR 合并。

---

## 📦 发布流程

1. **更新版本号** — 同步修改 `Cargo.toml` / `apps/desktop/package.json` / `apps/desktop/src-tauri/tauri.conf.json` / `apps/desktop/src-tauri/Cargo.toml`
2. **三轨验证全绿** — `cargo check/test/clippy` + `pnpm tsc/vitest/build`
3. **打 tag** — `git tag -a vX.Y.Z -m "release: vX.Y.Z"`（遵循 [SemVer 2.0](https://semver.org/lang/zh-CN/)）
4. **Tauri 三平台构建** — `pnpm tauri:build` 产出 `.dmg` / `.msi` / `.AppImage` / `.deb`
5. **更新 CHANGELOG.md** — 新增版本段,记录 feature / fix / breaking

详见：[docs/guide/release-process.md](docs/guide/release-process.md)

---

## 🛣️ 路线图

| 版本       | 状态      | 主题                                                             |
| ---------- | --------- | ---------------------------------------------------------------- |
| **v2.4.x** | 🧊 仅维护 | Python v2.4 主线（仅修关键阻塞性 bug,详见 CHANGELOG [2.5.0] 段） |
| **v2.5.0** | ✅ 当前   | **Tauri 2 + Rust + React 主线正式启用** · 5 步流水线 · 11 LLM    |
| v2.5.x     | 📋 进行中 | WASM 插件市场 · 多 TTS 引擎并行 · 字幕双语 · 剪映草稿导出        |
| v3.0       | 🔮 规划   | 全功能 GA · Python 主线删除 · WASM 插件 API 稳定                 |

> **方向**：以 Tauri 为主线持续演进,Python v2.4 主线仅做冻结维护。

---

## 🤝 贡献指南

我们欢迎所有形式的贡献 — 修 bug、写文档、提 feature、反馈问题。

### Commit 规范

严格遵循 [Conventional Commits 1.0](https://www.conventionalcommits.org/zh-hans/)：

```
<type>(<scope>): <subject>

type ∈ {feat, fix, docs, style, refactor, test, chore, build, ci, perf, revert}
scope ∈ {rust, desktop, tauri, ipc, hooks, stores, ui, i18n, theme, pipeline, ...}
```

示例：

```
feat(pipeline): 接入 XState v5 状态机替换 reducer
fix(ipc): 修复 specta 生成的 TS 类型在 nullable 字段上的不一致
docs(readme): 重写根 README · 反映 v2.5.0 真实工程状态
chore(rust): 移除 scenefab-cli crate（纯桌面端，无需终端入口）
```

### 提交前自检

```bash
cargo check --workspace
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
cd apps/desktop && pnpm exec tsc --noEmit && pnpm exec vitest run && pnpm build
```

### Issue / PR 模板

仓库已提供 `.github/ISSUE_TEMPLATE/` 与 `.github/pull_request_template.md`,提单前请先阅读。

---

## 📚 文档导航

| 主题                 | 链接                                                             |
| -------------------- | ---------------------------------------------------------------- |
| 官方文档站 VitePress | [docs/index.md](docs/index.md)                                   |
| 快速开始             | [docs/guide/quick-start.md](docs/guide/quick-start.md)           |
| 安装指南             | [docs/guide/installation.md](docs/guide/installation.md)         |
| AI 模型配置          | [docs/guide/ai-configuration.md](docs/guide/ai-configuration.md) |
| AI 视频生成指南      | [docs/guide/ai-video-guide.md](docs/guide/ai-video-guide.md)     |
| 界面说明             | [docs/guide/interface.md](docs/guide/interface.md)               |
| 解说规格             | [docs/guide/narration-spec.md](docs/guide/narration-spec.md)     |
| 导出                 | [docs/guide/exporting.md](docs/guide/exporting.md)               |
| 发布流程             | [docs/guide/release-process.md](docs/guide/release-process.md)   |
| 故障排查             | [docs/guide/troubleshooting.md](docs/guide/troubleshooting.md)   |

### 历史与归档

- v2.4 Python 主线退役公告与维护政策：见 [CHANGELOG.md](CHANGELOG.md) [2.5.0] 段「chore(governance): Python v2.4 主线退役存档」

| 文件 | 说明 |
| ---- | ---- |

---

## 📄 License

本项目基于 [MIT License](LICENSE) 开源。

```text
MIT License

Copyright (c) 2026  Agions

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND...
```

---

## 🙏 致谢

- 桌面壳：[Tauri 2](https://tauri.app) — Rust + WebView 的现代桌面应用范式
- 前端框架：[React 19](https://react.dev) · [TanStack Router](https://tanstack.com/router) · [TanStack Query](https://tanstack.com/query)
- UI 系统：[shadcn/ui](https://ui.shadcn.com) · [Radix UI](https://www.radix-ui.com) · [Tailwind CSS 4](https://tailwindcss.com)
- LLM / TTS：[11 个 Provider](apps/desktop/src/) · [Edge-TTS](https://github.com/rany2/edge-tts)
- 视频处理：[FFmpeg 6.x](https://ffmpeg.org)
- 设计参考：[brands/](assets/) · 浅色 / 深色双主题 Logo

---

<div align="center">

**[⭐ Star us on GitHub](https://github.com/scenefab/scenefab)** · **[📖 Read the docs](docs/index.md)** · **[🐛 Report a bug](https://github.com/scenefab/scenefab/issues)**

<sub>Built with ❤️ by Agions · 2026</sub>

</div>
