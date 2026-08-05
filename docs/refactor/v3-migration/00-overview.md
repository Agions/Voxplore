# 00 · 整体重构方案总览（v3.0）

> 📌 本文档是 v3.0 迁移方案的总入口，所有关键决策（ADR）、目标架构、路线图、风险的总览。

## 1. 摘要

本方案把 SceneFab 从 **PySide6 + FastAPI + Python 3.10** 的传统桌面应用，彻底迁移到 **Tauri 2.0 + Rust 1.85+ + React 18 + TypeScript 5** 的现代 WebView 桌面应用架构。

### 1.1 范围

| 范围       | 包含                                                                        |
| ---------- | --------------------------------------------------------------------------- |
| **包含**   | 后端 Rust 重写、前端 React 重写、Tauri 集成、配置 / 插件 / 更新器迁移、文档 |
| **包含**   | `.scenefab` 数据格式完全兼容 · 5 步流水线接口保持 · 4 种多视频策略保留      |
| **不包含** | LLM Provider 实现细节修改（仅迁移到 Rust，调用协议不变）                    |
| **不包含** | FFmpeg 算法优化（仅迁移，FFmpeg 子进程调用方式不变）                        |
| **不包含** | Edge-TTS 调用方式变更（仅迁移，仍走 HTTPS）                                 |

### 1.2 不做的（Non-Goals）

- ❌ **不重写 LLM 协议**：OpenAI、DeepSeek、Qwen、Gemini、Claude 等 11 个 Provider 的 API 形态完全保留
- ❌ **不修改 .scenefab JSON Schema**：仅迁移序列化层，字段不变
- ❌ **不引入新功能**：v3.0 仅做"等价迁移 + 性能提升"，新功能推 v3.1+
- ❌ **不破坏旧格式**：保留 `.narrafilm` 兼容读取
- ❌ **不引入 WASM 沙箱到主流程**：插件沙箱用 `wasmtime` 但仅作用于第三方插件

## 2. 现状速览（基线 2026-08-04）

| 指标         | 值                                                            |
| ------------ | ------------------------------------------------------------- |
| Python 源码  | **57,050 行** / **249 个文件**                                |
| 测试代码     | 14,972 行 / 73 测试文件                                       |
| 测试覆盖     | 估算 30-40%（核心 70%+，UI 较低）                             |
| 最大单文件   | `ui/main/main_window/__init__.py` **1,329 行**                |
| i18n 键      | zh-CN 488 + en-US 474                                         |
| 流水线步骤   | 5 步（导入 / 拆分 / 脚本 / 配音字幕 / 导出）                  |
| 上传策略     | **4 种**（single / concat / batch / series）                  |
| LLM Provider | **11 个**（Qwen/Kimi/GLM5/Claude/Gemini/DeepSeek/Doubao/...） |
| 主要技术栈   | PySide6 6.9+, FFmpeg, Edge-TTS, Pydantic 2.5+, FastAPI        |
| 部署形态     | PyInstaller 二进制（macOS 80MB / Windows 90MB / Linux 75MB）  |

### 2.1 Python 子系统分布

| 子系统                                                                          | 文件数  | 代码行数   | 关键文件                                           |
| ------------------------------------------------------------------------------- | ------- | ---------- | -------------------------------------------------- |
| `app/core/`                                                                     | 15      | ~4,800     | di_container, unified_event_bus, task_store, audit |
| `app/services/ai/`                                                              | 22      | ~8,500     | llm_manager, script_generator, 11 providers        |
| `app/services/video/`                                                           | 18      | ~11,000    | monologue_maker, pipeline_integrator, analyzer     |
| `app/services/export/`                                                          | 8       | ~3,000     | video_exporter, jianying_exporter, batch_export    |
| `app/pipeline/`                                                                 | 7       | ~6,800     | narration/, fp_workflow, short_drama, assembly     |
| `app/models/`                                                                   | 9       | ~906       | project, narration, video, project_models          |
| `app/api/`                                                                      | 7       | ~1,200     | main, 5 routers, 2 middleware, schemas             |
| `app/ui/`                                                                       | ~40     | ~18,000    | viewmodels, theme, main, widgets, i18n, commands   |
| `app/plugins/`                                                                  | 6       | ~1,500     | registry, loader, interfaces, 2 examples           |
| `app/updater/`                                                                  | 6       | ~1,616     | service, downloader, installer, verifier, manifest |
| `app/project/`                                                                  | 4       | ~900       | manager, template_mgr, template_models             |
| `app/config/`                                                                   | 5       | ~1,200     | config, manager, definitions, types, settings_data |
| 其他（utils/help/templates/services/monitor/orchestration/video_understanding） | 100+    | ~8,000     | 业务支撑模块                                       |
| **合计**                                                                        | **249** | **57,050** | —                                                  |

## 3. 关键决策（ADR）

### ADR-101 彻底重写而非渐进式迁移

**背景**：现有 Python 实现已经过 2.5 轮重构，遗留债务大量存在（main_window 1329 行、4 个 Phase 命名耦合、PySide6 强绑定 UI 逻辑）。

**决策**：采用"双分支并行 + 截止日切换"策略：

- 2026-08-04 ~ 2027-02：建立 `refactor/v3-tauri` 分支，Rust+React 全量开发
- 2026-08-04 ~ 2027-03：保留 `main` 分支，Python 实现仅修 P0 Bug
- 2027-04：v3.0.0-rc 发布，Python 实现进入 freeze
- 2027-05：v3.0.0 GA，删除 `src/app/` 全部 Python 代码

**理由**：

1. 渐进式迁移（先迁 API 再迁 UI）会导致 Rust/React 端被迫兼容 Python 数据格式 6+ 个月
2. 双栈并行维护成本高于一次性切换
3. Tauri/Rust 的并发模型（tokio）天然不适合逐步替换 Python asyncio 热点

**影响**：

- 团队需在 4 个月内同时维护两套系统 → 需要 2+ 名全职工程师
- v3.0 发布前不能向 Python 端添加任何新功能
- 旧版本用户必须升级到 v3.0（无 v2.6 计划）

### ADR-102 Workspace 多 crate 而非单体 crate

**背景**：v2.5 refactor 文档中讨论过 6 领域 crate 拆分方案。

**决策**：采用 Cargo workspace 拆分：

```
scenefab/
├── crates/
│   ├── scenefab-core/              # 核心基础设施（错误、配置、事件、日志）
│   ├── scenefab-domain/            # 领域模型（Project、Pipeline、Config、Plugin）
│   ├── scenefab-ffmpeg/            # FFmpeg 包装层
│   ├── scenefab-llm/               # 11 个 LLM Provider + Manager
│   ├── scenefab-tts/               # TTS 抽象 + Edge-TTS 实现
│   ├── scenefab-video/             # 视频处理（MonologueMaker、PipelineIntegrator）
│   ├── scenefab-export/            # 导出器（VideoExporter、JianyingExporter）
│   ├── scenefab-plugin/            # 插件系统（注册表、加载器、wasmtime 沙箱）
│   ├── scenefab-update/            # 自动更新
│   └── scenefab-i18n/              # 国际化资源
└── apps/desktop/
  ├── src/                           # React + TS 前端
  └── src-tauri/                     # Tauri 入口 + Command 注册 (apps/desktop 下以满足工作区约束)
```

**理由**：

- 单体 crate 编译时间不可接受（57k 行等价 Rust 约 80k 行，编译>5min）
- 领域 crate 可独立版本化（未来 v3.1+ 单独发包）
- 编译时强制边界（防止 AI 领域依赖 UI 领域）
- 测试隔离（领域 crate 不依赖 WebView，可在 CI 跑快测试）

**影响**：

- Cargo.toml 维护成本↑
- 但编译时间 ↓ 60%（增量编译友好）
- 团队可并行开发不同 crate

### ADR-103 IPC 用 Tauri Command 而非 HTTP

**背景**：v2.5 方案中，FastAPI 暴露 REST API 给前端调用（HTTP 走 localhost:8000）。

**决策**：**完全废弃 HTTP 层**，所有前后端通信走 Tauri Command（基于 FFI 的 JSON-RPC）：

```rust
// Rust 端
#[tauri::command]
async fn create_project(
    state: State<'_, AppState>,
    name: String,
    description: Option<String>,
) -> Result<ProjectDto, SceneFabError> { ... }
```

```typescript
// 前端 (TS)
const project = await invoke<ProjectDto>("create_project", {
  name: "我的解说",
  description: "AI 第一人称独白",
});
```

**理由**：

- Tauri Command 比 localhost HTTP 快 10-50x（无 TCP 栈开销）
- 天然类型安全（specta 自动生成 TS 类型）
- 简化部署（无需绑定端口，无 CORS 问题）
- 安全性更好（自动应用 Capability ACL）

**影响**：

- `apps/desktop/src/lib/api.ts` 是唯一的 IPC 入口（禁止 fetch）
- specta 生成的类型需纳入 git 管理
- 现有 FastAPI 端点全部废弃（v2.5 引入的 `/api/v1/*` 不再对外暴露）

### ADR-104 UI 框架选 shadcn/ui + Tailwind v4

**背景**：v2.5 文档提到过 "shadcn/ui + Tailwind v4 + Zustand + TanStack Query"。

**决策**：前端 UI 库采用：

- **shadcn/ui**（Radix UI + Tailwind，copy-paste 风格）
- **Tailwind CSS v4**（零配置 CSS-first）
- **Zustand**（全局状态，~1KB）
- **TanStack Query v5**（服务端状态，自动缓存/失效）
- **react-i18next**（i18n）
- **react-hook-form + zod**（表单 + 验证）
- **@tanstack/react-router**（类型安全路由）

**理由**：

- shadcn/ui 适合复杂桌面应用（可定制，符合 macOS HIG）
- TanStack Query 与 Tauri Command 完美契合（自动 invalidate）
- Zustand 替代 Redux（避免 5KB+ 模板）
- react-router 替代 React Router（更 TS 友好）

**影响**：

- 必须重写所有 UI（不能"复制" PySide6 设计）
- 字体、间距、色板需重新设计（基于 Tailwind v4 tokens）
- a11y 标准升级到 WCAG 2.2 AA

### ADR-105 持久化用 sqlx + sled

**背景**：现有 Python 用 SQLite（标准库）+ Redis（可选）。

**决策**：

- **sqlx** 0.8（compile-time checked SQL，异步）
- **sled** 0.34（嵌入式 KV，用于插件状态/缓存）
- **不依赖 Redis**：单用户桌面应用无需跨实例

**理由**：

- sqlx 编译期校验 SQL（防止运行时 schema drift）
- sled 用于高频 KV 读写（任务进度、临时状态）
- 避免外部依赖（用户无需装 Redis）

**影响**：

- SQLite schema 迁移走 sqlx-cli（取代 Alembic）
- 任务存储改用 sled（不再走 `~/cache/scenefab/task_store.db`）

### ADR-106 插件沙箱用 wasmtime

**背景**：v2.5 文档提到 "wasmtime 29" 作为插件沙箱选项。

**决策**：插件以 **WASM 模块** 形式分发，通过 **wasmtime** 沙箱执行：

```rust
// 插件清单示例
{
  "id": "scenefab-plugin-deepseek-voice",
  "name": "DeepSeek Voice Clone",
  "wasm": "plugin.wasm",
  "exports": ["generate_voice", "list_voices"],
  "permissions": ["network:outbound", "fs:read:user_voice_models"]
}
```

**理由**：

- WASM 沙箱 = 内存安全 + 隔离（无法访问宿主资源除非显式允许）
- 跨平台（同一份 .wasm 适用于 macOS/Windows/Linux）
- 性能足够（wasmtime 启动 <50ms）

**影响**：

- 现有 Python 插件（`deepseek_ai_generator`、`cinematic_subtitle`）需重写为 Rust → 编译为 WASM
- 内置插件走"特权模式"（直接 Rust crate，非 WASM）
- 第三方插件作者需学习 Rust 基础（提供 `#[scenefab_plugin]` 宏简化）

### ADR-107 国际化用 i18next

**背景**：现有自研 i18n 模块 488+474 键，PySide6 通过 retranslate() 刷新。

**决策**：

- 前端：**react-i18next**（异步加载 JSON 资源）
- 后端：**i18n crate**（rust-i18n），通过 `specta` 暴露给前端
- 资源文件：`apps/desktop/src/locales/{zh-CN,en-US}/common.json`（不再放 .py）

**理由**：

- 行业标准（react-i18next 95% 翻译工具链兼容）
- 资源与组件同目录（co-location）
- 后端错误消息国际化统一

**影响**：

- 488+474 键需重新导出到 JSON
- 后端 Error 必须支持 `LocalizedError` trait
- i18n 切换无 UI 闪烁（v2.5 的 C-03 缺陷彻底解决）

### ADR-108 测试用 cargo test + vitest + Playwright

**背景**：现有 pytest + pytest-qt + 14,972 行测试代码。

**决策**：

- **单元测试**：cargo test（领域 crate）+ vitest（前端）
- **集成测试**：cargo test（带 tokio::test）+ Playwright（端到端 UI）
- **覆盖率**：cargo-tarpaulin（>=70% 核心 crate）+ vitest --coverage
- **回归脚本**：保留现有 73 个 Python 测试作为"行为基准"（v3.0 期间仍跑，对比输出）

**理由**：

- 单元测试迁到新语言（无复用价值，需重写）
- Python 测试作为"行为黄金文件"在迁移期极有价值
- Playwright 验证 Tauri WebView 真实交互

**影响**：

- 73 个 Python 测试文件 1:1 翻译为 Rust 测试
- v3.0 GA 前 Python 测试可删除
- 性能基准测试用 criterion（Rust）+ benchmarks.mjs（TS）

## 4. 目标架构（高层视图）

```
┌─────────────────────────────────────────────────────────────┐
│  WebView Process (React 18 + TS 5 + shadcn/ui + Tailwind v4)│
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ HomePage     │  │ ProductionPg │  │ AssetsPg     │       │
│  │ (Dashboard)  │  │ (5-step)     │  │ (File Browser)│       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ SettingsPg   │  │ UpdatePg     │  │ HelpOverlay  │       │
│  │ (Token/Theme)│  │ (Updater)    │  │ (Markdown)   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                  │                  │             │
│         └──────────────────┴──────────────────┘             │
│                            │                                │
│                   TanStack Query + Zustand                  │
│                            │                                │
│              invoke() / listen() (Tauri IPC)                │
└────────────────────────────┬────────────────────────────────┘
                             │ JSON-RPC over FFI
┌────────────────────────────┴────────────────────────────────┐
│  Main Process (Rust 1.85+ Tauri 2.0)                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ apps/desktop/src-tauri  ── Tauri Command 路由层    │   │
│  │  ├─ command::project  (create/list/get/delete)       │   │
│  │  ├─ command::pipeline (start/status/cancel)          │   │
│  │  ├─ command::export   (enqueue/get_progress)         │   │
│  │  ├─ command::config   (get/set/reset)                │   │
│  │  ├─ command::plugin   (list/enable/disable)          │   │
│  │  ├─ command::update   (check/download/install)       │   │
│  │  └─ command::system   (metrics/health)               │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ AppContext (DI 容器) + EventBus (tokio broadcast)    │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ domain   │ │ llm      │ │ video    │ │ export   │       │
│  │ (Rust)   │ │ (Rust)   │ │ (Rust)   │ │ (Rust)   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ ffmpeg   │ │ plugin   │ │ update   │ │ config   │       │
│  │ (Rust)   │ │ (wasmtime)│ │ (Rust)   │ │ (Rust)   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  External Processes:                                 │   │
│  │   - FFmpeg subprocess (video processing)             │   │
│  │   - Edge-TTS subprocess (audio synthesis)            │   │
│  │   - Plugin WASM instances (wasmtime)                 │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 5. 实施路线图（高层）

| 阶段     | 时间                      | 主要交付物                               | 验收标志                                  |
| -------- | ------------------------- | ---------------------------------------- | ----------------------------------------- |
| **M0**   | 2026-08-04 ~ 08-18 (2 周) | 脚手架 + workspace + CI + specta 链路    | `pnpm tauri dev` 启动空白窗口             |
| **M1**   | 2026-08-19 ~ 09-15 (4 周) | core + domain + config + i18n 全量       | 73 个 Python 测试等价 Rust 测试 100% 通过 |
| **M2**   | 2026-09-16 ~ 10-13 (4 周) | ffmpeg + llm + tts + video 子系统        | 端到端可生成 1 条解说（命令行）           |
| **M3**   | 2026-10-14 ~ 11-10 (4 周) | export + plugin (wasmtime) + update      | 导出剪映草稿可用，插件可加载              |
| **M4**   | 2026-11-11 ~ 12-08 (4 周) | Tauri Command 全部接通 + specta 类型生成 | 前端可调通所有 Command                    |
| **M5**   | 2026-12-09 ~ 01-05 (4 周) | 前端 6 页面 + 主题 + i18n + a11y         | 视觉等价 Python 实现                      |
| **M6**   | 2027-01-06 ~ 02-02 (4 周) | 集成测试 + 性能基准 + 平台打包           | macOS/Windows/Linux 全部可启动            |
| **M7**   | 2027-02-03 ~ 03-02 (4 周) | Playwright E2E + Bug Bash + 灰度         | 5 名外部用户跑通完整流程                  |
| **M8**   | 2027-03-03 ~ 03-30 (4 周) | 文档迁移 + 教程视频 + 公证               | docs/ 全部可读 + 公证通过                 |
| **M9**   | 2027-03-31 ~ 04-27 (4 周) | RC1/RC2/RC3 + 修复                       | 连续 3 个 RC 无 P0/P1                     |
| **M10**  | 2027-04-28 ~ 05-25 (4 周) | v3.0.0 GA + Python 代码删除 + tag 发布   | 0 P0 + 90 天无重大回滚                    |
| **合计** | **42 周**                 | **v3.0.0 GA**                            | 完整替代 Python 实现                      |

## 6. 不变量（不可破坏）

| 类型     | 不变量                                                                  |
| -------- | ----------------------------------------------------------------------- |
| 数据     | `.scenefab` JSON 字段顺序 · `MonologueProject.id` · `output_dir` 默认值 |
| API      | 5 步流水线（导入/拆分/脚本/配音字幕/导出）· 4 种多视频策略              |
| i18n     | zh-CN / en-US 文件存在 · `t(key)` fallback 格式 `[key]` 保留            |
| 主题     | 暗/亮主题运行时切换 · `<200ms` 响应                                     |
| HTTP API | 兼容期提供 `/api/v1/*` 桥接层（M3~M5），M6 后删除                       |
| CLI      | `scenefab` 命令名 · `--version` · `--help`                              |
| 文件     | 旧 `.narrafilm` 兼容读取（保留至 v3.1 后删除）                          |
| 安全     | 路径白名单 · keyring 存储 · 插件沙箱 · SHA-256 校验                     |
| 性能     | 启动 <500ms · 内存 <90MB · 主题切换 <200ms · 拖拽 <100ms                |

## 7. 验收标准（顶层）

### 7.1 功能等价

- ✅ 4 种多视频策略（single/concat/batch/series）行为一致
- ✅ 11 个 LLM Provider 全部可用
- ✅ 5 步流水线状态机不变
- ✅ 暗/亮主题切换无 UI 闪烁
- ✅ 自动更新支持增量包 fallback
- ✅ 插件系统可加载 2 个内置示例 + 1 个第三方示例

### 7.2 质量

- ✅ cargo test 覆盖率 ≥ 70%（核心 crate ≥ 80%）
- ✅ vitest 覆盖率 ≥ 60%
- ✅ cargo clippy --deny warnings 全通过
- ✅ TypeScript strict mode 0 error
- ✅ 前端 ESLint + Prettier 0 warning
- ✅ a11y axe 扫描 0 critical

### 7.3 体验

- ✅ 启动到首页 <500ms
- ✅ 主题切换 <200ms
- ✅ 多文件拖拽 <100ms
- ✅ macOS 公证通过
- ✅ Windows SmartScreen 通过
- ✅ Linux AppImage + deb + rpm 全部可安装

### 7.4 安全

- ✅ Tauri Capabilities 最小化（每个 Command 显式声明）
- ✅ specta 类型无 any
- ✅ 密钥 keyring 存储（无明文）
- ✅ 路径白名单强制
- ✅ 依赖 `cargo audit` 0 high/critical

## 8. 与 v2.5 方案的关键差异

| 维度         | v2.5 方案（保留 Python） | **v3.0 方案（彻底重写）**            |
| ------------ | ------------------------ | ------------------------------------ |
| **后端语言** | Python 3.10+             | **Rust 1.85+**                       |
| **UI 框架**  | PySide6 6.9+ (Qt)        | **React 18 + shadcn/ui**             |
| **HTTP 层**  | FastAPI + Uvicorn        | **Tauri Command（无 HTTP）**         |
| **插件沙箱** | importlib + 路径校验     | **wasmtime 29**                      |
| **状态机**   | PySide6 Signal           | **tokio broadcast channel**          |
| **主题**     | QSS + 重建 stylesheet    | **CSS Variables + Tailwind**         |
| **i18n**     | 自研 + retranslate()     | **i18next + 自动 reload**            |
| **测试**     | pytest + pytest-qt       | **cargo test + vitest + Playwright** |
| **打包**     | PyInstaller              | **Tauri Bundle（dmg/exe/AppImage）** |
| **安装大小** | 80-90MB                  | **<8MB**                             |
| **启动时间** | 1.5s                     | **<500ms**                           |
| **内存**     | 280MB                    | **<90MB**                            |

## 9. 关键风险（前 5）

| 风险                                   | 等级  | 缓解                                                    |
| -------------------------------------- | ----- | ------------------------------------------------------- |
| Rust 编译时间长导致开发体验差          | 🟠 P1 | workspace 拆分 + sccache + 增量编译 + cargo nextest     |
| Tauri WebView 跨平台差异（尤其 Linux） | 🟠 P1 | webkit2gtk 强制版本约束 + Playwright 三平台跑 E2E       |
| 11 个 LLM Provider 重写量大            | 🟠 P1 | 用 `generic-LLM-provider` trait + codegen 减少样板      |
| .scenefab 旧项目读取兼容性             | 🔴 P0 | M0 阶段就建立"Python 输出 → Rust 读取"双向 fixture 测试 |
| Python 实现冻结 → 关键 Bug 无修复      | 🟠 P1 | M5 后允许 1 名工程师继续维护 Python 主线至 M9           |

完整风险见 [§11-risk-rollback.md](./11-risk-rollback.md)。

## 10. 团队分工（建议）

| 角色               | 人数 | 负责 Phase    | 关键产出                                |
| ------------------ | ---- | ------------- | --------------------------------------- |
| 架构师 / Tech Lead | 1    | M0 ~ M10 全程 | ADR 文档 + 核心 crate review            |
| Rust 高级工程师    | 2    | M1 ~ M6       | core/domain/llm/video/export 5 个 crate |
| 前端高级工程师     | 1    | M4 ~ M7       | 6 页面 + 组件库 + 主题 + i18n           |
| 资深测试 / QA      | 1    | M5 ~ M9       | Playwright + 性能基准 + 灰度            |
| 文档 / DevRel      | 0.5  | M6 ~ M10      | 文档迁移 + 教程 + release notes         |
| DevOps             | 0.5  | M0 + M6 + M10 | CI/CD + 公证 + 三平台打包               |

> ⚠️ 最小团队规模：**4.5 人**（1 架构 + 2 Rust + 1 前端 + 0.5 DevOps，QA 由架构师兼任）

## 11. 立即下一步（本周）

1. **本周内（2026-08-04 ~ 08-08）**
   - [ ] 团队对齐本方案（半日 Kick-off）
   - [ ] 创建 `refactor/v3-tauri` 分支
   - [ ] CI 矩阵添加：Rust 1.85、Node 22、pnpm 9
   - [ ] 锁定 Python 主线（仅修 P0 Bug）

2. **下周（2026-08-11 ~ 08-15）**
   - [ ] M0 启动会（2 小时）
   - [ ] Cargo workspace 初始化
   - [ ] 第一个 Rust crate `scenefab-core` 跑通测试
   - [ ] 第一个 Tauri Command `get_version` 在前端可调用

详细任务见 [§10-implementation-roadmap.md](./10-implementation-roadmap.md)。
