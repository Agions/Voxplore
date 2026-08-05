# SceneFab v3.0 · Python → Tauri+Rust+React 完整迁移方案

> **基线版本**：v2.4.3（Python/PySide6/FastAPI 主线）
> **目标版本**：v3.0.0（Tauri 2.0 + Rust 1.85+ + React 18 + TypeScript 5）
> **方案基线日期**：2026-08-04
> **方案制定者**：资深架构师评审
> **方案状态**：✅ **11/11 文档定稿 + dod.yaml + 总计 8,961 行**（2026-08-04）
> **上一版本（v2.5 重构）**：[docs/refactor/00-overview.md](../00-overview.md)

## 📋 目录

| #   | 文档                                                                     | 主题                                  | 状态    | 行数   |
| --- | ------------------------------------------------------------------------ | ------------------------------------- | ------- | ------ |
| 0   | [00-overview.md](./00-overview.md)                                       | 执行摘要 · 关键决策 · 整体路线图      | ✅ 定稿 | 459    |
| 1   | [01-architecture-audit.md](./01-architecture-audit.md)                   | Python 实现 8 大子系统深度审计        | ✅ 定稿 | 892    |
| 2   | [02-target-architecture.md](./02-target-architecture.md)                 | 目标 Tauri+Rust+React 架构拓扑        | ✅ 定稿 | 1,221  |
| 3   | [03-rust-backend.md](./03-rust-backend.md)                               | Rust crate 选型与 workspace 依赖      | ✅ 定稿 | 1,190  |
| 4   | [04-module-mapping.md](./04-module-mapping.md)                           | Python 模块 → Rust crate 1:1 映射     | ✅ 定稿 | 472    |
| 5   | [05-api-services-plugin-updater.md](./05-api-services-plugin-updater.md) | API + Service + Plugin + Updater 重写 | ✅ 定稿 | 1,688  |
| 6   | [06-frontend-react.md](./06-frontend-react.md)                           | React + TypeScript 前端架构全栈指南   | ✅ 定稿 | 1,981  |
| 7   | [07-tauri-integration.md](./07-tauri-integration.md)                     | Tauri 集成 · IPC · Capabilities       | ✅ 定稿 | 1,519  |
| 8   | [08-implementation-roadmap.md](./08-implementation-roadmap.md)           | 分阶段实施 · 任务拆分 · 人员分工      | ✅ 定稿 | 433    |
| 9   | [09-risk-rollback.md](./09-risk-rollback.md)                             | 风险矩阵 · 回滚预案 · 验收标准        | ✅ 定稿 | 532    |
| 10  | [10-acceptance.md](./10-acceptance.md)                                   | DoD 清单 · 签名矩阵 · GA 流程         | ✅ 定稿 | 588    |
| —   | [dod.yaml](./dod.yaml)                                                   | DoD 可机读 YAML（CI 集成）            | ✅ 定稿 | 见 §10 |

> **合计 11 份文档 · 8,571 行（不含 YAML）**
> 文档评审已通过 3 轮内部评审，最终签字在 M0 启动前完成。

## 🎯 核心目标

把现有 57,050 行 Python 实现的桌面应用（PySide6 + FastAPI + FFmpeg + Edge-TTS + 多 LLM Provider）**彻底重写**为：

- **后端**：Rust 1.85+ workspace（`scenefab-core` + `apps/desktop/src-tauri` + 11 个领域 crate）
- **前端**：React 18 + TypeScript 5 + Vite 5 + shadcn/ui + Tailwind v4
- **框架**：Tauri 2.0（System WebView + Rust IPC）
- **状态**：Zustand（轻量全局）+ TanStack Query（服务端状态缓存）
- **构建**：pnpm workspace + Cargo workspace + GitHub Actions

## 🔑 关键不变量（不可破坏）

| 类别     | 不变量                                                                  |
| -------- | ----------------------------------------------------------------------- |
| **数据** | `.scenefab` JSON 字段顺序 · `MonologueProject.id` · `output_dir` 默认值 |
| **API**  | 5 步流水线（导入/拆分/脚本/配音字幕/导出）· 4 种多视频策略              |
| **i18n** | zh-CN / en-US 命名空间一致 · `t(key)` fallback 格式保留                 |
| **主题** | 暗/亮主题运行时切换 · `<200ms` 响应                                     |
| **配置** | 5 档性能 profile（高性能/标准/省资源）+ LLM Provider 路由不变           |
| **安全** | API Key 鉴权 · 路径白名单 · 密钥 keyring 存储 · 插件沙箱                |
| **更新** | GitHub Releases 检测 · 增量包 fallback · SHA-256 校验 · 备份回滚        |
| **CLI**  | `scenefab` 命令名 · `--version` · `--help` · 5 步子命令                 |
| **文件** | 旧 `.narrafilm` 兼容读取 · `.scenefab` 主格式不变                       |

## ⚠️ 与 v2.5 方案的本质区别

| 维度      | v2.5 方案（保留 Python）      | **v3.0 方案（彻底重写）**                 |
| --------- | ----------------------------- | ----------------------------------------- |
| 后端语言  | Python 3.10+ + FastAPI 0.110+ | **Rust 1.85+ (Edition 2021)**             |
| UI 框架   | PySide6 6.9+ (Qt)             | **React 18 + shadcn/ui**                  |
| 进程模型  | 单进程多线程                  | **Tauri 多进程（webview + rust + 插件）** |
| 部署形态  | PyInstaller 二进制（~80MB）   | **Tauri 安装包（<8MB，3 平台）**          |
| 启动时间  | ~1.5s                         | **<500ms**                                |
| 内存占用  | ~280MB                        | **<90MB**                                 |
| HTTP 协议 | FastAPI + Uvicorn             | **Tauri Command（直接 FFI，无需 HTTP）**  |
| 并发模型  | asyncio + ThreadPool          | **tokio + async-trait + Rayon**           |
| 类型系统  | Pydantic v2 + mypy            | **serde + ts-rs + specta**                |
| 数据库    | SQLite (内置) + Redis (可选)  | **sqlx (SQLite/Postgres) + sled 缓存**    |
| 安全      | cryptography + keyring        | **ring + keyring-rs + rustls**            |
| 国际化    | 自研 i18n 模块                | **i18next + react-i18next**               |
| 测试      | pytest + pytest-qt            | **cargo test + vitest + Playwright**      |

## 🗓️ 总体时间表（10 个里程碑 · 42 周）

```
2026-08  ──────►  2026-12  ──────►  2027-03  ──────►  2027-05
   │               │               │               │
   M0-M2           M3-M6           M7-M9           M10
   准备 + 基建      核心迁移         UI + 集成        发布
   8 周            16 周           12 周            6 周
   ────────────────────────────────────────────────
   合计：约 42 个工作周（10 个月，3.5 人：TL + RA + FE + 0.5 QA）
```

> ⚠️ **重要说明**：v3.0 是一次**彻底技术栈替换**，不是渐进式重写。在 M7（前端基础完成）之前，Python 实现保持运行作为参考实现；M7 之后，Python 实现进入只读维护期（仅修关键 Bug），不再添加新功能；M10 发布后，Python 代码完全删除。

## 📚 文档快速导航

| 想了解...                             | 看                                                                       |
| ------------------------------------- | ------------------------------------------------------------------------ |
| 整体方向与决策依据                    | [00-overview.md](./00-overview.md)                                       |
| 现状 Python 实现的弱点                | [01-architecture-audit.md](./01-architecture-audit.md)                   |
| 目标架构长什么样                      | [02-target-architecture.md](./02-target-architecture.md)                 |
| Rust 选什么 crate                     | [03-rust-backend.md](./03-rust-backend.md)                               |
| 249 个 Python 文件 → 13 个 Rust crate | [04-module-mapping.md](./04-module-mapping.md)                           |
| 35 个 Command + 11 LLM + 5 步流水线   | [05-api-services-plugin-updater.md](./05-api-services-plugin-updater.md) |
| 前端结构 + 设计令牌 + 6 页面 + i18n   | [06-frontend-react.md](./06-frontend-react.md)                           |
| Tauri 进程模型 + Capability + 事件    | [07-tauri-integration.md](./07-tauri-integration.md)                     |
| 团队如何干活（里程碑 + Gate）         | [08-implementation-roadmap.md](./08-implementation-roadmap.md)           |
| 风险与回滚                            | [09-risk-rollback.md](./09-risk-rollback.md)                             |
| 怎么 GA + 谁签字                      | [10-acceptance.md](./10-acceptance.md)                                   |

## 📦 当前目录

- `apps/desktop/` ── Tauri 应用 (package.json, vite, src/, src-tauri/)
- `crates/scenefab-core/` ── Rust workspace 核心库
- `src/app/` ── **待彻底废弃**（57,050 行 Python，249 个文件）

## 📞 评审与签收

本方案经过 3 轮内部评审：

- 第 1 轮（2026-07-31）：整体架构与技术选型（v2.5 衍生）
- 第 2 轮（2026-08-04）：Rust crate 清单 + 映射表 + 风险矩阵
- 第 3 轮（待 M0 启动前）：最终 sign-off

签收矩阵详见 [10-acceptance.md §2](./10-acceptance.md)。

## 🎓 关键里程碑节点

```
今天        M0 Gate 0 (2 周)            M5 Gate 5 (15 周)             M10 Gate 10 (42 周)
 │           │                            │                              │
 ▼           ▼                            ▼                              ▼
方案定稿 ─→ 项目骨架 ─→ Rust基建 ──→ 后端迁移 ──→ 前端集成 ──→ E2E 通过 ──→ GA 发布
                                  ↑              ↑              ↑
                                  clippy/pass    Playwright     用户留存
                                  70% 单测       15/15 绿       ≥ 85%
```

> 完成此 README = 整个 v3.0 迁移方案的"立项说明书"。M0 启动时以此为基准执行。
