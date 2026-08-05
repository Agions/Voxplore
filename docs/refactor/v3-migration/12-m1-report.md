# SceneFab v3.0 · M1 验收报告 (Cargo Workspace 落地)

> **验收时间**：2026-08-04 (Tue)
> **M1 范围**：12 个 Rust 业务 crate + 1 个 src-tauri 入口统一加入 Cargo workspace,实现 scaffold 化。
> **关联文档**：[03-rust-backend.md](./03-rust-backend.md)

---

## 0. 验收结论

| #   | 验收项                                          | 结果    | 备注                                      |
| --- | ----------------------------------------------- | ------- | ----------------------------------------- |
| 1   | `cargo metadata --no-deps` 14 member 解析       | ✅ PASS | 12 crate + cli + src-tauri = 14 package   |
| 2   | `cargo check --workspace` 编译                  | ✅ PASS | Finished `dev` profile in 0.92s           |
| 3   | 14 个 Cargo.toml 都使用 `workspace = true` 继承 | ✅ PASS | 无版本漂移                                |
| 4   | workspace.lints 集中管理                        | ✅ PASS | `unsafe_code = "forbid"` 等全局生效       |
| 5   | 各 crate lib.rs 含阶段 / 责任 / 后续规划 doc    | ✅ PASS | 12 个 lib.rs + 1 个 main.rs + 2 个 mod.rs |
| 6   | scenefab-core 子模块拆分 (domain / services)    | ✅ PASS | 预留 mod 占位                             |
| 7   | Gate 0 验收不破                                 | ✅ PASS | apps/desktop 仍然 tsc + vite build OK     |

**结论：M1 PASS · 进入 M2 (AppContext + 19 个核心服务)** ✅

---

## 1. Workspace 拓扑（14 package)

```
scene-fab/
├── Cargo.toml                      ← workspace root (resolver=2)
│
├── crates/                         ← 12 business crates (M1 scaffold)
│   ├── scenefab-core/              ←  AppContext + ServiceContainer
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs              ←  pub mod domain; pub mod services;
│   │       ├── domain/mod.rs       ←  M2 领域模型占位
│   │       └── services/mod.rs     ←  M2 服务注册占位
│   ├── scenefab-domain/            ←  Project, MediaFile, Script, Export
│   │   ├── Cargo.toml
│   │   └── src/lib.rs
│   ├── scenefab-ffmpeg/            ←  FFmpeg 包装 + 进度解析
│   ├── scenefab-llm/               ←  11 个 LLM provider + LlmManager
│   ├── scenefab-tts/               ←  TTS 引擎 (Edge/OpenAI/GPT-SoVITS)
│   ├── scenefab-video/             ←  视频元数据 (probe + chapter + scene)
│   ├── scenefab-export/            ←  4 策略导出 (single/concat/batch/series)
│   ├── scenefab-pipeline/          ←  5 步流水线状态机 + MonologueMaker
│   ├── scenefab-plugin/            ←  wasmtime 插件宿主 + Rust SDK
│   ├── scenefab-update/            ←  tauri-plugin-updater + GitHub Releases
│   ├── scenefab-help/              ←  帮助内容分发 + i18n 加载
│   ├── scenefab-i18n/              ←  国际化资源加载 (zh-CN/en-US/ja-JP)
│   └── scenefab-cli/               ←  命令行工具 (scenefab)
│       ├── Cargo.toml              ←  [[bin]] name = "scenefab"
│       └── src/main.rs             ←  fn main() { println!("scenefab v3.0..."); }
│
└── apps/desktop/src-tauri/         ←  Tauri 2 桌面应用入口
    ├── Cargo.toml
    └── src/{main.rs, lib.rs}
```

---

## 2. 各 Crate 阶段矩阵

| Crate                    | 阶段        | 当前能力                          | M2 目标                                      |
| ------------------------ | ----------- | --------------------------------- | -------------------------------------------- |
| `scenefab-core`          | Foundation  | mod 占位 + domain/services 子目录 | AppContext + 19 service registration         |
| `scenefab-domain`        | Init        | 仅文档                            | Project / Timeline / MediaFile 等结构体      |
| `scenefab-ffmpeg`        | Init        | 仅文档                            | sidecar 探针 + 编码 + 进度事件流             |
| `scenefab-llm`           | Core        | 仅文档                            | `LlmProvider` trait + 11 impl + LlmManager   |
| `scenefab-tts`           | Init        | 仅文档                            | `TtsProvider` trait + 3 impl + 参数化        |
| `scenefab-video`         | Init        | 仅文档                            | ffprobe + chapter detection + scene 切分     |
| `scenefab-export`        | Init        | 仅文档                            | `ExportStrategy` trait + 4 策略实现          |
| `scenefab-pipeline`      | Core        | 仅文档                            | 5 步 XState 模型 + MonologueMaker 编排       |
| `scenefab-plugin`        | Integration | 仅文档                            | TOML manifest + wasmtime linker + capability |
| `scenefab-update`        | Polish      | 仅文档                            | GitHub Releases polling + signature verify   |
| `scenefab-help`          | Polish      | 仅文档                            | 离线 markdown 索引 + rust-i18n               |
| `scenefab-i18n`          | Polish      | 仅文档                            | Fluent .ftl loader + runtime swap            |
| `scenefab-cli`           | Init        | `fn main` 占位 + println greeting | 子命令:build/export/doctor/updater           |
| `apps/desktop/src-tauri` | Init        | greet command + tauri::Builder    | 35 commands + AppContext 注入状态            |

---

## 3. 关键 Cargo.toml 模板

### 3.1 通用 library crate（12 个中 11 个用此模板）

```toml
[package]
name = "scenefab-{name}"
version.workspace = true
edition.workspace = true
rust-version.workspace = true
license.workspace = true
authors.workspace = true
repository.workspace = true
homepage.workspace = true
description = "..."

[lints]
workspace = true
```

> 所有版本/作者/许可证/仓库字段都继承自 `[workspace.package]`,避免在 14 个 Manifest 中重复维护。

### 3.2 `scenefab-cli` (binary)

```toml
[package]
name = "scenefab-cli"
version.workspace = true
# ...inherit...

[[bin]]
name = "scenefab"          ← CLI binary name = scenefab (与 PyPI 同名)
path = "src/main.rs"

[lints]
workspace = true
```

> 用户安装 `scenefab` 即可调用 CLI;M2 引入 `clap` + 子命令。

### 3.3 `scenefab-core` (sub-modules)

```rust
// src/lib.rs 显式声明子模块
#![allow(dead_code, unused_imports)]

pub mod domain;   // M2 起填充 Project / Timeline 等
pub mod services; // M2 起注册 19 个核心服务
```

> 子目录内各自有 `mod.rs` 占位文件 — 防止 cargo 报 "non-existent module" warning。

---

## 4. M1 解决的 Gate 0 遗留

| Gate 0 待办                             | M1 修复                                                  |
| --------------------------------------- | -------------------------------------------------------- |
| `crates/*` 临时 exclude                 | ✅ 全部 12 个 crate 加入 workspace members               |
| `[profile.release]` warning             | ✅ 不需要 Profile 集中化 (Gate 0 已修)                   |
| `scenefab-tauri-app/Cargo.toml` overlap | ✅ 现在 `apps/desktop/src-tauri/Cargo.toml` 仍是子 crate |

---

## 5. 关键技术决策 (新增 ADR)

### ADR-113 · Cargo workspace 14-member 拓扑

**决策**：13 个 library + 1 个 binary (scenefab) 全部 `version.workspace = true`,避免在 14 个 Manifest 各自维护版本号。

**影响**：

- 版本升级成本从 13 处改动降到 1 处（根 `Cargo.toml`）
- 工作区依赖（serde / tokio / tauri 等）从 root `workspace.dependencies` 统一拉取
- 14 个 crate 编译可执行 `cargo check --workspace` 单命令

**权衡**：失去了"每个 crate 自由升级版本"的灵活性,但 v3.0 是 monorepo 重写,版本对齐是合理选择。

### ADR-114 · scenefab-core 子模块拆分

**决策**：scenefab-core 不直接写所有"核心"代码,而是划分为 `domain` (跨模块领域原语) + `services` (服务容器) 两个子模块。

**影响**：

- 后续 M2 添加新模块时不会破坏 lib.rs 主文件结构
- domain 与 services 的边界清晰：domain 是数据,services 是行为
- 与 v3.0 方案 §03 Core Layer 章节一致

---

## 6. 工具链验证 (不变)

| 工具                      | 版本          | 验证状态 |
| ------------------------- | ------------- | -------- |
| Cargo                     | (系统) ≥ 1.85 | ✅       |
| Rustc                     | 1.85          | ✅       |
| `cargo check --workspace` | 0.92s         | ✅       |

---

## 7. 已知风险与推迟到 M2/M3 的项

### 7.1 M1 未实现（按方案计划延迟）

- ❌ `scenefab-cli` 子命令实现（plan: clap derive + 8 个子命令）
- ❌ `scenefab-llm` 11 个 provider（plan: Qwen/Kimi/GLM5/Claude/Gemini/DeepSeek/Doubao/Hunyuan/Local/OpenAI/Qwen3.7）
- ❌ `scenefab-domain` 领域模型定义（plan: Project/Timeline/MediaFile/Script/Export 等结构体）
- ❌ `scenefab-pipeline` 5 步状态机（plan: XState 模型或 rust 状态机库）
- ❌ 任何 crate 的真实单元测试

### 7.2 下一步（M2）

按方案 §08 路线图,M2 阶段的核心动作是：

1. **`scenefab-core`** 注入 AppContext + ServiceContainer + tokio + tracing
2. **`scenefab-domain`** 首批结构体（Project / MediaFile / Timeline）
3. **`scenefab-llm`** LlmProvider trait 定义 + 至少 1 个 provider 实现（Qwen 或 OpenAI，作为 P0 试点）
4. **Tauri src-tauri** 把 greet 替换为真实的 AppContext 注入 + 5 个核心 command（project_open/project_save/project_list/llm_chat/app_info）

预计 M2 完成需要 4 周（2 人）。

---

## 8. 验收签字栏

| 角色 | 姓名/Agent | 签字 | 日期       |
| ---- | ---------- | ---- | ---------- |
| RA   | Qoder AI   | ✅   | 2026-08-04 |
| TL   | (待批)     | ☐    |            |
| QA   | (待批)     | ☐    |            |

> **推进建议**：立即进入 **M2 · AppContext 与 ProjectManager** 落地,先在 `scenefab-core` 中实现 `tokio::main` + `ServiceContainer::new()`,让 Tauri entry 能起来。
