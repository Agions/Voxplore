# SceneFab v3.0 · 完成定义（DoD）+ 签名矩阵 + GA 流程

> **基线版本**：v3.0.0
> **关联文档**：[00-overview.md](./00-overview.md) · [08-implementation-roadmap.md](./08-implementation-roadmap.md) · [09-risk-rollback.md](./09-risk-rollback.md)
> **本文档范围**：可机读的 DoD 清单（DoD.yaml）、签名矩阵详细版、v3.0 GA 公告模板、客户支持响应 SOP、v2.4 主线冻结流程、v3.0 后续 roadmap 占位。

## 1. DoD 清单（可机读 YAML）

> 这份 YAML 直接被 CI 读取引用，每个项目失败即阻 GA。

```yaml
# docs/refactor/v3-migration/dod.yaml
version: "1.0"

prerequisites:
  - file: "bin/scenefab"
    exists: true
  - file: "apps/desktop/dist/index.html"
    exists: true
  - file: "apps/desktop/src-tauri/target/release/scenefab"
    exists: true
  - file: "apps/desktop/src/ipc/types.gen.ts"
    exists: true

rust_crate:
  cargo_test_workspace:
    cmd: cargo test --workspace --all-features
    expect_exit_code: 0
    coverage:
      threshold: 70
      excludes:
        - "*/tests/*"
        - "*/examples/*"

  cargo_clippy:
    cmd: cargo clippy --workspace --all-features -- -D warnings
    expect_exit_code: 0

  cargo_fmt:
    cmd: cargo fmt --all -- --check
    expect_exit_code: 0

  cargo_deny:
    cmd: cargo deny check
    expect_all_zero:
      - advisories
      - bans
      - licenses
      - sources

  cargo_build_release_matrix:
    targets:
      - x86_64-unknown-linux-gnu
      - x86_64-apple-darwin
      - aarch64-apple-darwin
      - x86_64-pc-windows-msvc
      - aarch64-pc-windows-msvc
    expect_exit_code: 0

react_frontend:
  pnpm_typecheck:
    cmd: pnpm typecheck
    expect_exit_code: 0

  pnpm_lint:
    cmd: pnpm lint
    expect_exit_code: 0

  pnpm_unit_tests:
    cmd: pnpm test
    coverage:
      threshold: 80
      excludes:
        - "src/components/ui/**"
        - "src/workers/**"

  pnpm_build:
    cmd: pnpm build
    output_file: "apps/desktop/dist"
    bundle_limits:
      main_entry_kg: 200
      total_gzipped_kg: 500

features:
  ipc_commands:
    count_required: 35
    cmd_files:
      - apps/desktop/src-tauri/src/commands/project.rs
      - apps/desktop/src-tauri/src/commands/pipeline.rs
      - apps/desktop/src-tauri/src/commands/assets.rs
      - apps/desktop/src-tauri/src/commands/settings.rs
      - apps/desktop/src-tauri/src/commands/llm.rs
      - apps/desktop/src-tauri/src/commands/export.rs
      - apps/desktop/src-tauri/src/commands/theme.rs
      - apps/desktop/src-tauri/src/commands/update.rs
      - apps/desktop/src-tauri/src/commands/help.rs
      - apps/desktop/src-tauri/src/commands/diagnostics.rs
      - apps/desktop/src-tauri/src/commands/window.rs
      - apps/desktop/src-tauri/src/commands/plugin.rs

  ipc_events:
    count_required: 24

  llm_providers:
    functional_min: 5
    unit_tested_min: 11

  pipeline_steps:
    count: 5
    names:
      - "素材导入"
      - "场景拆分"
      - "脚本生成"
      - "配音字幕"
      - "导出发布"

  configuration_fallback_layers:
    - keyring
    - yaml
    - env

  security:
    path_whitelist: true
    csp: true
    keyring: true
    plugin_sandbox: true

  i18n:
    locales: ["zh-CN", "en-US"]
    zh_CN_key_count: 488
    en_US_key_count: 474

  accessibility:
    axe_core_violations_per_page: 0
    pages:
      - "/"
      - "/production"
      - "/assets"
      - "/settings"
      - "/updates"
      - "/help"

e2e:
  playwright:
    test_files:
      - tests/e2e/scenarios/smoke.spec.ts
      - tests/e2e/scenarios/theme.spec.ts
      - tests/e2e/scenarios/palette.spec.ts
      - tests/e2e/scenarios/pipeline.spec.ts
    expect_pass: 15
    retry_strategy: process=2 in_container=0

  visual_regression:
    pixel_diff_pct_threshold: 1
    pages:
      - "/"
      - "/production"
      - "/assets"
      - "/settings"
      - "/updates"
      - "/help"
    themes: ["light", "dark"]

performance:
  cold_start_p95_ms: 500
  pipeline_p95_ratio_to_v24: 0.85
  theme_switch_p95_ms: 80
  route_switch_p95_ms: 100
  bundle_main_kg: 200
  memory_idle_mb: 90

data_migration:
  formats_accepted:
    - ".scenefab"
    - ".narrafilm" # 旧格式
  sample_count: 12
  loss_tolerance: 0

platforms:
  macos:
    min_version: "13.0"
    notarization: required
  windows:
    min_version: "10.0.19041"
    code_signing: required
  linux:
    distributions:
      - debian
      - ubuntu
      - fedora
      - arch

sign_offs:
  gate_0_required: [TL, RA, FE, QA]
  gate_1_required: [TL, RA, FE, QA]
  gate_2_required: [TL, RA, FE]
  gate_3_required: [TL, RA, FE]
  gate_4_required: [TL, RA, FE, QA]
  gate_5_required: [TL, RA, FE, QA]
  gate_6_required: [TL, FE, QA]
  gate_7_required: [TL, FE, QA]
  gate_8_required: [TL, RA, FE, QA]
  gate_9_required: [TL, RA, FE, QA]
  gate_10_required: [TL, RA, FE, QA]
```

### 1.1 CI 集成示例

```yaml
# .github/workflows/dod.yml
name: dod-check

on:
  push:
    branches: [main, release/*]
  workflow_dispatch:

jobs:
  dod:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-python@v5

      - name: Install system deps
        run: |
          sudo apt-get update
          sudo apt-get install -y libavcodec-dev libavformat-dev libavutil-dev

      - name: Run DoD check
        run: ./scripts/dod-check.sh
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

```bash
# scripts/dod-check.sh
#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

# 1. Rust 校验
cargo test --workspace --all-features --quiet
cargo clippy --workspace --all-features -- -D warnings
cargo fmt --all -- --check
cargo deny check

# 2. 前端校验
cd apps/desktop
pnpm install --frozen-lockfile
pnpm typecheck
pnpm lint
pnpm test --coverage --run
pnpm build
cd ../..

# 3. E2E 校验
cd apps/desktop
pnpm exec playwright install --with-deps chromium
pnpm exec playwright test
cd ../..

# 4. 性能基线
./scripts/perf-bench.sh

# 5. DoD YAML 静态校验
python ./scripts/dod_yaml_check.py ./docs/refactor/v3-migration/dod.yaml

echo "✅ DoD passed"
```

## 2. 签名矩阵详细版

### 2.1 Gate 关卡逐项确认表

| Gate | Gate ID    | 验证项                                                    | 自动验证          | 手工验证        | 签字人      |
| ---- | ---------- | --------------------------------------------------------- | ----------------- | --------------- | ----------- |
| 0    | M0-Gate0   | Cargo workspace 编译 / Tauri 空壳启动 / CI green          | cargo / pnpm / CI | repository walk | TL+RA+FE+QA |
| 1    | M1-Gate1   | `bin/scenefab --version` / clippy 0 警告 / 日志输出       | cargo test        | manual smoke    | TL+RA+FE+QA |
| 2    | M2-Gate2   | `getAppInfo` / CSP / Path白名单 / keyring                 | rust test         | manual validate | TL+RA+FE    |
| 3    | M3-Gate3   | 打开 `.scenefab` / 资源增删 / 配置持久化                  | rust test         | QA smoke        | TL+RA+FE+QA |
| 4    | M4-Gate4   | 5 步 noop / 导出 mp4 / 性能 -15%                          | rust test         | manual          | TL+RA+FE+QA |
| 5    | M5-Gate5   | 5 LLM Provider / TTS / 插件 sandbox / 更新器              | rust test         | manual          | TL+RA+FE+QA |
| 6    | M6-Gate6   | 主题切换 < 100ms / 6 路由 / 命令面板 / 快捷键             | vitest            | manual          | TL+FE+QA    |
| 7    | M7-Gate7   | Lighthouse ≥ 90 / axe 0 / i18n 全 / 流水线 happy          | lighthouse + axe  | manual smoke    | TL+FE+QA    |
| 8    | M8-Gate8   | 35 commands + 24 events 接通 / 主题持久化 / LSP 0 错误    | tsc + vitest      | QA smoke        | TL+RA+FE+QA |
| 9    | M9-Gate9   | Playwright 15/15 / 三平台冷启动 < 500ms / 数据迁移 0 丢失 | e2e + bench       | QA + manual     | TL+RA+FE+QA |
| 10   | M10-Gate10 | 用户留存 ≥ 85% / 崩溃率 < 0.1% / 更新成功率 ≥ 95%         | 监控 / telemetry  | 客户支持数据    | TL+RA+FE+QA |

### 2.2 ADR 编号表

| ADR     | 主题                                                    | 阶段 |
| ------- | ------------------------------------------------------- | ---- |
| ADR-101 | 彻底重写而非渐进式迁移                                  | M0   |
| ADR-102 | Workspace 多 crate 而非单体 crate                       | M0   |
| ADR-103 | IPC 用 Tauri Command 而非 HTTP                          | M2   |
| ADR-104 | UI 框架选 shadcn/ui + Tailwind v4                       | M6   |
| ADR-105 | 持久化用 sqlx + sled                                    | M3   |
| ADR-106 | 插件沙箱用 wasmtime                                     | M5   |
| ADR-107 | 国际化用 i18next                                        | M7   |
| ADR-108 | 测试用 cargo test + vitest + Playwright                 | M9   |
| ADR-109 | 自动更新策略：GitHub Releases + 双端点 fallback         | M10  |
| ADR-110 | 数据迁移：v2.narrafilm → v3.scenefab                    | M9   |
| ADR-111 | 性能预算：冷启动 < 500ms + 5 步流水线 P95 = v2.4 × 0.85 | M8   |

## 3. v3.0 GA 公告（模板）

```markdown
# SceneFab v3.0 发布公告

> 我们很高兴地宣布 SceneFab v3.0.0 正式发布！
>
> 这是我们一次彻底的技术栈升级：57,050 行 Python 代码 → Rust 1.85+ workspace + React 18 + TypeScript 5。
>
> ## 重大变化
>
> - **后端**：FastAPI → Tauri 2.0 命令式 IPC（无 HTTP 开销）
> - **前端**：PySide6 → React 18 + shadcn/ui
> - **包大小**：80MB → < 8MB 安装包
> - **冷启动**：1.5s → < 500ms
> - **内存**：280MB → < 90MB（空载）
>
> ## 升级路径
>
> - macOS / Windows / Linux 自动更新推送
> - 旧版本 2.x 仍可在 v3.0 安装目录下载页获取
> - 项目文件 `.scenefab` 完全向下兼容
> - 旧格式 `.narrafilm` 通过内置工具一键升级
>
> ## 已知限制
>
> - 第三方 Python 插件不兼容，需要用新 SDK 重写
> - Linux 平台可能需要额外字体包（详见更新器自动检查）
>
> ## 致谢
>
> [参与内部测试的 100 位用户列表]
> [issue 反馈表]
```

## 4. 客户支持响应 SOP

### 4.1 优先级定义

| 优先级 | 描述                                   | 响应目标 | 修复目标       |
| ------ | -------------------------------------- | -------- | -------------- |
| P0     | 数据丢失 / 安全漏洞 / 主要功能不可用   | < 1h     | < 4h（hotfix） |
| P1     | 单个功能失效 / 性能显著降低 / 升级失败 | < 4h     | < 24h（patch） |
| P2     | UI 错位 / 边缘场景失败 / 文档错误      | < 24h    | 下个 sprint    |
| P3     | 体验改进 / 文案 / 翻译质量             | < 7d     | 下个 minor     |

### 4.2 标准操作流程

```text
P0 流程（生产事故应急）:

[1] 用户提交 issue + logs (自动上传)
    ↓
[2] 自动 triage (severity + 是否数据丢失 + 频次)
    ↓
[3] 紧急 Slack channel #v3-p0-incident (值班 on-call)
    ↓
[4] TL 决定 hotfix / 回滚 / 手动 patch
    ↓
[5] 修复 + 发布 patch (1h 内) + 公告

P1 流程:

[1] 用户 issue 进 backlog
[2] daily standup 三方确认
[3] patch 内 24h 出
[4] 通过自动更新推送

P2/P3 流程:

[1] 入 sprint backlog
[2] 标准 sprint 节奏
```

### 4.3 升级失败响应

```text
1. 用户反馈"更新卡住 / 重启后版本号不变"
   ↓
2. 收集 ~/.scenefab/logs/updater.log + updater-state.json
   ↓
3. 检查 SHA-256 / partial download / quarantine
   ↓
4. 路径 A: 备份还原
   - 还原 ~/.scenefab/backup/v{prev} → 当前
   - 通过 SIGHUP 触发 restart
   路径 B: 强制 hotfix
   - 修复 updater
   - 发布 3.0.1 再推
```

## 5. v2.4 主线冻结流程

### 5.1 状态机

```
ACTIVE (M0-M7) ──→ READ-ONLY (M8-M9) ──→ DEPRECATED (M10) ──→ REMOVED (v3.2)
```

### 5.2 ACTIVE 阶段（M0-M7）

- v2.4 主线仍可接收 PR
- 新 feature 接受，但要求"为 v3.0 移植预留接口"
- CI 双轨：v2.4 测试 + v3.0 测试同时跑

### 5.3 READ-ONLY 阶段（M8-M9）

- v2.4 主线仅修 critical bug
- Bug 修复需要 TL + RA 联合签字
- 不再添加新 feature
- 标记 `READ-ONLY.md` 在仓库根

### 5.4 DEPRECATED 阶段（M10）

- v2.4 不再 release
- 仅保留安全 CVE 修复（按需 backport 到 v3.0）
- 仓库标记 v2.4 为 legacy 分支

### 5.5 REMOVED 阶段（v3.2）

- M10 后 6 个月（即 v3.2 发布时）
- v2.4 代码 + 测试 + fixture 完全从仓库删除
- 旧 issue / PR 历史保留（GitHub archive）
- CI 不再跑 v2.4 测试

## 6. v3.0 → v3.1 路线图（占位）

```yaml
v3.1:
  timeline: "M10 后第 2-3 个月"
  themes:
    - 用户体验增强
    - 多 LLM 接入完整化
    - 跨平台性能优化

  features:
    - 第三方插件市场（wasmtime sandbox 完成）
    - 全部 11 个 LLM Provider 跑通真实调用
    - 原生视频预览（不依赖 ffmpeg）
    - 批量项目导出
    - 多脚本对比模式
    - 实时协作（基于 yjs）
    - Windows ARM64 first-class 支持
    - auto-updater 智能带宽自适应

v3.2:
  timeline: "v3.1 后 3 个月"
  themes:
    - v2.4 完全退役
    - 桌面 + Web 一份代码

  features:
    - apps/web 推出（Tauri 移动化 / Web 化）
    - 云端项目同步（可选）
    - v2.4 代码删除
```

## 7. v3.0 GA 流程清单

```text
M10 第 1 周（RC 阶段）:
  ☐ RC 版本发布（v3.0.0-rc.0）
  ☐ 1000 用户灰度（按区域 + 平台）
  ☐ 监控指标接入
  ☐ 紧急回滚 SOP 演练（已完成）

M10 第 2 周:
  ☐ 监控数据收集（崩溃率 / 留存 / 更新成功率）
  ☐ 反馈 issue P0/P1 闭环
  ☐ patch（v3.0.0-rc.1）

M10 第 3 周:
  ☐ 数据合格 → 发布 v3.0.0 GA
  ☐ 自动更新推送（先 50%，再 100%）
  ☐ 公告 + 客户支持准备

M10 第 4-16 周:
  ☐ 持续监控 + 反馈处理
  ☐ v3.0.1 / 3.0.2 patch 发布
  ☐ v2.4 主线冻结
```

## 8. 持续监控告警阈值

| 指标                  | 阈值                    | 响应            |
| --------------------- | ----------------------- | --------------- |
| 冷启动 P95            | > 800ms (7 日均值)      | 立即调查        |
| 5 步流水线 P95        | > v2.4 × 1.2 (7 日均值) | 立即调查        |
| 7 日崩溃率            | > 0.5%                  | 立即调查        |
| 自动更新失败率（24h） | > 5%                    | 暂停推送        |
| LLM Provider 4xx/5xx  | 任一 > 10%（24h）       | 切换 fallback   |
| API key 泄露          | 任何                    | 立即封堵 + 公告 |
| 插件 sandbox 越权     | 任何                    | 立即下架插件    |
| i18n fallback 触发    | > 20% (key)             | 翻译团队介入    |

## 9. ADR 模板

每个 ADR 必须遵循下面的格式：

```markdown
# ADR-XXX: <标题>

## 状态

- 提议
- 已接受
- 已否决
- 已替代（由 ADR-YYY 替代）

## 背景

<问题/需求/约束条件>

## 决策

<选择的方案>

## 后果

### 正面

- ...

### 负面

- ...

### 风险

- ...

## 替代方案

- 方案 A: ...
- 方案 B: ...

## 决策记录

<日期> · <签字人>

## 变更历史

<修订记录>
```

## 10. v3.0 GA 后组织移交

| 角色     | 接收方    | 交付物                                   |
| -------- | --------- | ---------------------------------------- |
| 开发     | v3.1 团队 | 仓库 + CI + ADR 全部                     |
| 测试     | QA 团队   | Playwright 套件 + 性能基线               |
| DevOps   | SRE       | 自动更新 + 监控 + 回滚脚本               |
| 产品     | PM 团队   | 公告 + 反馈收集表 + 路线图               |
| 客户支持 | Support   | SOP + FAQ + 升级回滚指南                 |
| 安全     | SecOps    | CSP 报告 + 路径白名单审计 + keyring 审计 |

## 11. 迁移完整性校验（最终一次）

发布后第 30 天执行：

```text
□ v2.4 日活 < 5%（可接受范围内）
□ v3.0 自动更新成功率 ≥ 99%
□ 用户平均 7 日留存 ≥ 85%
□ 关键路径 P95（5 步流水线 / 冷启动）达标
□ 数据迁移成功率 ≥ 99.9%
□ 安全审计通过
□ M10 复盘完成

Go/No-Go 决定：v3.0 成功 → v3.1 启动
```

---

## 附录 A · 文件索引

| 文件                                                                     | 主题                                       |
| ------------------------------------------------------------------------ | ------------------------------------------ |
| [00-overview.md](./00-overview.md)                                       | 执行摘要 · 关键决策 · 整体路线图           |
| [01-architecture-audit.md](./01-architecture-audit.md)                   | Python 实现 8 大子系统深度审计             |
| [02-target-architecture.md](./02-target-architecture.md)                 | 目标 Tauri+Rust+React 架构拓扑             |
| [03-rust-backend.md](./03-rust-backend.md)                               | Rust crate 选型与 workspace 依赖           |
| [04-module-mapping.md](./04-module-mapping.md)                           | Python 模块 → Rust crate 1:1 映射          |
| [05-api-services-plugin-updater.md](./05-api-services-plugin-updater.md) | REST API + Service + Plugin + Updater 重写 |
| [06-frontend-react.md](./06-frontend-react.md)                           | React + TypeScript 前端架构                |
| [07-tauri-integration.md](./07-tauri-integration.md)                     | Tauri 集成 · IPC · Capabilities            |
| [08-implementation-roadmap.md](./08-implementation-roadmap.md)           | 分阶段实施 · 任务拆分                      |
| [09-risk-rollback.md](./09-risk-rollback.md)                             | 风险矩阵 · 回滚预案 · 验收标准             |
| [10-acceptance.md](./10-acceptance.md)                                   | DoD · 签名矩阵 · GA 流程                   |

---

> **v3.0 迁移方案定稿**：所有文档由 TL/RA/FE/QA 四方签字后，CI 自动把 `dod.yaml` 集成进 release pipeline，**自动阻塞未达 DoD 的 GA 流程**。从此 v3.0 是一个可强制执行、可审计、可回滚的可信工程计划。
