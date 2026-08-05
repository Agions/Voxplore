# SceneFab v3.0 · 风险矩阵 + 回滚策略 + 验收标准

> **基线版本**：v3.0.0
> **关联文档**：[00-overview.md](./00-overview.md) · [02-target-architecture.md](./02-target-architecture.md) · [08-implementation-roadmap.md](./08-implementation-roadmap.md)
> **本文档范围**：12 类风险（按业务/技术/外部/合规维度分组）、每条风险的概率/影响、应急响应、回滚路径、验收标准、签名矩阵。

## 0. TL;DR

| 维度     | 风险数 | P0 关键 | 必须回滚预案 |
| -------- | ------ | ------- | ------------ |
| 技术风险 | 5      | 2       | 5            |
| 业务风险 | 3      | 1       | 3            |
| 外部风险 | 2      | 0       | 2            |
| 合规风险 | 2      | 1       | 2            |
| **合计** | **12** | **4**   | **12**       |

> **回滚"金标准"**：M8 之前任意里程碑可回退到 Python 主线；M8-M10 进入"灰度发布期"，回滚意味着停止推送新版本并保留 v2.4 旁路下载链接。

## 1. 风险矩阵（12 类）

下表按 **风险 ID × 概率 × 影响 × 风险等级** 排序：

| 风险 ID | 类别 | 描述                                                                | 概率 | 影响 | 等级  | 触发信号                              |
| ------- | ---- | ------------------------------------------------------------------- | ---- | ---- | ----- | ------------------------------------- |
| **R1**  | 技术 | Rust ffmpeg-sys-next 跨平台编译失败（特别是 Windows GNU toolchain） | 中   | 高   | 🔴 P0 | CI red on windows-latest              |
| **R2**  | 技术 | 35 个 Tauri Commands 中部分签名阻塞前端开发                         | 中   | 中   | 🟡 P1 | FE blocked > 3 天                     |
| **R3**  | 技术 | specta 类型与 TS 类型漂移（手动改动未重新生成）                     | 高   | 中   | 🟡 P1 | `tsc --noEmit` red 出现               |
| **R4**  | 技术 | Tauri 冷启动时间 > 800ms（达不到 500ms 目标）                       | 中   | 中   | 🟡 P1 | Lighthouse / `performance.now()` 超标 |
| **R5**  | 技术 | wasmtime 插件沙箱不兼容特定 Provider（或性能不可接受）              | 低   | 中   | 🟢 P2 | 单元测试 / 集成测试失败               |
| **R6**  | 业务 | LLM Provider API 行为变化（Qwen / GLM5 / Kimi 等）打破现有 prompt   | 中   | 高   | 🔴 P0 | 单元测试 + 真实调用失败               |
| **R7**  | 业务 | 5 步流水线的产出物格式与 v2.4 不兼容（导致用户资产失效）            | 低   | 高   | 🔴 P0 | 用户导出样本对比失败                  |
| **R8**  | 业务 | 自动更新断链 / SHA-256 校验失败导致升级失败                         | 中   | 高   | 🔴 P0 | 升级阶段错误日志大量出现              |
| **R9**  | 外部 | GitHub Releases 限流 / CDN 不可用                                   | 中   | 中   | 🟡 P1 | 5xx 上报                              |
| **R10** | 外部 | 操作系统升级导致 Tauri 2.x 不兼容（macOS 16 / Windows 12）          | 低   | 高   | 🟡 P1 | Tauri 官方 issue / Discord 通告       |
| **R11** | 合规 | API key 通过 Tauri IPC 泄露给前端 / 通过错误日志外泄                | 低   | 极高 | 🔴 P0 | 安全审计发现                          |
| **R12** | 合规 | 第三方插件权限过界（访问 `$HOME` 之外目录或执行任意 Shell 命令）    | 中   | 高   | 🟡 P1 | Manifest 审查发现                     |

## 2. 风险详情 + 应急 + 回滚

### R1 · Rust ffmpeg 跨平台编译

**详细描述**：

- Linux: 依赖 libavcodec-dev / libavformat-dev 系统库
- macOS: brew install ffmpeg 后 pkg-config 链接
- Windows: 需预编译的 ffmpeg .lib 文件，或切换 `ffmpeg-next` 静态链接

**触发信号**：

- CI 在 `ubuntu-latest` / `macos-13` / `windows-latest` 任一平台编译失败
- 链接器报告 unresolved external symbol（`avcodec_*` 等）

**缓解措施**：

1. M1 阶段（最早）做 PoC：在所有 3 平台编译一次 `ffmpeg-sys-next`
2. CI 矩阵 5 个目标：`ubuntu-latest` × `macos-13` × `macos-14` × `windows-2019` × `windows-2022`
3. 选用 `ffmpeg-next` 而非 `ffmpeg-sys-next`，提供预编译静态库到 GitHub Release
4. 若 Windows 失败 → 暂时"Windows 平台"延后（不可降低 milestone）

**应急路径**：

1. 暂停 M3 / M4
2. 备选方案：调用系统 ffmpeg（外部 sidecar）+ Rust 仅做参数组装
3. 时限：**3 天** 内必须决断；超期则进入回滚

**回滚预案**：

- 把 `scenefab-ffmpeg` 标记 deprecated，所有调用退回到 PySide6 内部 ffmpeg 调用
- 实际场景：v3.0 不支持视频处理，M4 跳过，仅保留"预览 / 元数据"能力
- 影响：v3.0 不能导出视频 → 提前告知用户"v3.0.1 才有完整视频能力"

---

### R2 · Tauri Commands 阻塞前端开发

**详细描述**：35 个 Commands 中 5 个左右涉及多 crate 协调（pipeline / export / update），需先在 Rust 端定 API 才能开始集成 UI。

**触发信号**：

- FE 在某个 story 上卡 ≥ 3 天
- FE 在 Sprint Review 中说 "等待后端 API"

**缓解措施**：

1. M2 末完成所有命令签名的 ADR 评审并冻结（**API 冻结关卡**）
2. FE 用 `tauri-mock` + 手写 stub 启动 UI 开发
3. M3-M5 各阶段都会预演一遍 RS-Interface

**应急路径**：

1. FE 端实现可在真实命令到来前用 TanStack Query mock adapter 跑通
2. 不允许降级（已经固定），后端优先

**回滚预案**：

- 暂无需要回滚；前端一旦 UI 走通，后端只需做契约填充

---

### R3 · specta / TS 类型漂移

**详细描述**：手动改后端 DTO struct 但未重新运行 `cargo test --features specta-export`，前端编译报错。

**触发信号**：

- CI 中 `pnpm typecheck` red
- PR review 时发现"类型不一致需要前端去匹配"

**缓解措施**：

1. CI 强制：`scripts/check-types-drift.sh` 比较生成文件 hash
2. 文档规范：所有 DTO 修改必须重跑生成 + 提交生成文件
3. pre-commit hook: `cargo test --features specta-export`

**应急路径**：

1. 找到最近一次类型对齐的 commit → revert
2. 显式生成新的 TS 类型 + 提交
3. 时限：1 天内修；超期则前端 features flag freeze

**回滚预案**：

- 暂时把该项 feature flag 关闭
- 恢复时按 PR 规则重新走

---

### R4 · 冷启动时间不达标

**详细描述**：Tauri 冷启动包含 Rust 进程初始化 + WebView 启动 + JS bundle 解析 + 首屏渲染。当前预算 500ms P95，实际可能更高。

**触发信号**：

- M8 阶段 Lighthouse / `performance.timing` report 中 start 阶段 > 800ms
- 跨平台手工测试报告

**缓解措施**：

1. Vite 拆分：`react-vendor` / `tanstack` / `i18n` 单独 chunk
2. Rust 启动：把 19 个 service 的初始化拆为"必需启动" vs "后台异步"
3. Splash 视觉：先显示 Skeleton 框架，5 步流水线 UI 在 React 层 lazy
4. 关掉不需要的 Tauri 插件（autostart 默认 false）

**应急路径**：

1. 把 shadcn/ui 换成无动画 / 极简版本
2. WebView 设置禁用 GPU acceleration（在某些 Windows 上加速）
3. 让 Rust 启动期先快速返回，等 React 端 query 后再 hydrate

**回滚预案**：

- 不阻断 GA 发布：v3.0 GA 附 "Recommended for Apple Silicon / Windows 11+"，老硬件用户建议保留 v2.4

---

### R5 · wasmtime 插件沙箱兼容性

**详细描述**：wasmtime 29 在 Windows / Linux 上的稳定性可能不及 Rust 主流运行时。

**触发信号**：

- 单元测试 flaky
- WASM 性能 < 原生 50%

**缓解措施**：

1. 提供两种实现：`scenefab-plugin-host-wasm`（wasmtime）+ `scenefab-plugin-host-dylib`（Rust cdylib）
2. M5 单元测试：插件 sandbox 运行一组 benchmark
3. 设性能红线：WASM 路径性能 ≥ 原生 80% 才算合格

**应急路径**：

- WASM 路径推迟到 v3.1
- 短期：插件用 dynamic library + 沙箱检查（不如 WASM 安全但能跑）

**回滚预案**：

- v3.0 不发布插件市场，标记"Coming in v3.1"

---

### R6 · LLM Provider API 行为变化

**详细描述**：v3.0 在 11 个 LLM Provider 上做统一抽象，但各家 API 经常变更（特别是 Qwen、Kimi、DeepSeek 等新晋厂商）。

**触发信号**：

- 单元测试中至少 1 个 Provider 失败 ≥ 2 周
- 真实调用出现 `400 invalid_request_error` 之类

**缓解措施**：

1. 每个 Provider 一个 trait 实现 + 独立单元测试 + nightly 重放
2. 维护 `provider-spec.md` 记录各家 API 差异
3. Manager 层 fallback：失败时降级到下一个 Provider
4. 不与任一 Provider 绑定硬编码字段（content / message 协议层适配）

**应急路径**：

1. 把失败的 Provider 标记 `disabled`
2. 短期：将"5 Provider" 改成 "3+稳定 Provider"
3. 提供用户文案："XX Provider 当前不可用，请临时选择 YY"

**回滚预案**：

- 不影响 GA：v3.0 GA 时如果只剩 5 个 Provider 能用，公告明确说明

---

### R7 · 5 步流水线产出物与 v2.4 不兼容

**详细描述**：v2.4 的 `.scenefab` 项目 JSON 结构（timeline / scenes / script / 字幕 / 导出 mp4）在 v3.0 必须兼容读取。

**触发信号**：

- 用 v3.0 打开 v2.4 项目后字段错位
- 序列化的 JSON 字段顺序/命名/类型不匹配

**缓解措施**：

1. M3 + M5 设独立 Migration 测试：把 12 个真实样本（在 v2.4 fixture 中保存）用 v3.0 读取
2. JSON schema 双向校验：`v2.4 schema` ⇄ `v3.0 schema`
3. 字段命名严格保持 camelCase，与 v2.4 一致

**应急路径**：

1. 立即切回旧 decoder 路径，限定"读旧 / 写新"
2. 时限：2 周内必须解决否则 M10 GA 推迟

**回滚预案**：

- v3.0 不破坏读取，但写新格式；旧项目用 v2.4 写回

---

### R8 · 自动更新断链

**详细描述**：v3.0 GA 后 v3.0.1 推送流程需要：GitHub Releases → tauri-plugin-updater 下载 → SHA-256 校验 → 应用 → 重启。如果任何一环失败，用户卡在旧版本上。

**触发信号**：

- 自动更新失败率 > 5%
- 用户报"更新卡住"

**缓解措施**：

1. M10 阶段做 2 次完整更新演练（CI 上传 → VM 升级）
2. update-applying 之前先备份当前版本到 `~/.scenefab/backup/v{version}/`
3. 失败后自动回滚到 backup
4. 提供用户引导"如何手动升级"

**应急路径**：

1. 暂停自动更新（关停 tauri-plugin-updater）
2. 仅手动下载 dmg / exe 安装

**回滚预案**：

- 用户群 < 5% 时回滚成本低；> 20% 时通过 in-app 公告告知恢复路径

---

### R9 · GitHub / CDN 不可用

**详细描述**：v3.0 自动更新默认走 GitHub Releases，受限流影响。

**触发信号**：

- 5xx > 5%
- 平均下载时间 > 30s

**缓解措施**：

1. 多端点 fallback：GitHub Releases + 自托管 R2/S3 + CF
2. 端点配置在 runtime 可切换（无需重新发布）

**应急路径**：

- 切到 fallback endpoint
- 公告用户走手动下载

**回滚预案**：

- 不影响主体功能

---

### R10 · 操作系统升级不兼容

**详细描述**：macOS / Windows 大版本发布可能改变 Tauri 行为。

**触发信号**：

- Tauri 官方 issue / Discord 通告
- 在新 OS 上 smoke test 失败

**缓解措施**：

1. M9 阶段同步在每个平台最新版（macOS 15/16 / Windows 11/12）做手工冒烟
2. CI 加 `macos-15` runner
3. 维护 `compatibility-matrix.md`

**应急路径**：

- 升级对 Tauri 2.x patch 跟进
- 必要时暂停该平台 GA（如同 v2.x 当时 macOS 13 才发布）

**回滚预案**：

- 平台用户极少时延迟支持

---

### R11 · API Key 泄露

**详细描述**：Tauri 端把 API key 通过 IPC 传给前端 / 日志打印 key 字符串。

**触发信号**：

- 静态扫描发现 key 在 WebView 资源里
- 安全审计报告
- 用户社区报告

**缓解措施**：

1. **永不**通过 Tauri IPC 传出明文 key
2. 所有 `LlmProvider` 构造在后端持有 key，emit 不带任何 key
3. 日志层：`tracing-log` sanitizer：检测 `sk-...` / `key=` / `Bearer` 模式并替换为 `[REDACTED]`
4. 启动期 audit：用测试断言"前端拿不到 key"

**应急路径**：

1. 立即封堵（hotfix release）
2. 用户侧：强制所有 Provider 走"reset key" 流程

**回滚预案**：

- 立即停服阻断，发布 patch

---

### R12 · 插件权限过界

**详细描述**：恶意插件通过 host import 访问 `~/.scenefab/` 之外目录或执行任意 shell。

**触发信号**：

- Manifest 审查发现 host import 越界
- fuzz 测试发现 host function crash

**缓解措施**：

1. Host import 受限接口：`fs.read_under(under_path)` + `shell.exec(allow_list)`
2. 启动期：每个插件载入时跑 fuzz 测试 30s
3. 第三方插件只能调用 `scenefab:plugin:default` capability，扩展需 user 显式 consent

**应急路径**：

1. 把违规插件 unregister
2. 公告所有用户："已下架插件 XX"

**回滚预案**：

- 短期禁用插件市场

## 3. 业务连续性 + 回滚总策略

### 3.1 三阶段连续性策略

```
M0 ──── M7                M8 ──── M9            M10
│   双轨并行期               灰度+主备期            GA+客户支持期
│                            │                    │
├─ v2.4 唯一真理源            ├─ v3.0 主推          ├─ v3.0 唯一
├─ v3.0 黑盒开发              ├─ v2.4 仅修关键 bug  └─ 自动更新+
└─ Python 仍能 release        └─ 可强制回滚到 v2.4
```

### 3.2 回滚决策矩阵

| 当前阶段  | 用户规模 | 触发条件                       | 决策                                     |
| --------- | -------- | ------------------------------ | ---------------------------------------- |
| M8 之前   | 任意     | 任意 Gate 不达                 | 暂停 v3.0 推进、修问题、保留 Python 主线 |
| M9 灰度期 | < 1000   | 任意 P0 风险 + 修复时长 ≤ 1 周 | Patch 后继续                             |
| M9 灰度期 | < 1000   | P0 修复时长 > 1 周             | 取消 GA，保留 RC                         |
| M10 GA    | ≥ 1000   | 自动更新失败率 > 10%           | 暂停推送 + 公告回退路径                  |
| M10 GA    | ≥ 1000   | 安全漏洞 P0                    | 紧急 hotfix + 回退                       |
| M10 GA    | ≥ 1000   | 数据丢失                       | 立即回滚 + 赔补                          |

### 3.3 紧急回滚路径

```bash
# 假设 v3.0 RC 已发出（5% 用户），需要紧急回退
# 用户可在 2 种路径中选 1：

# 路径 A: 通过自动更新回退到 v2.4
~/.scenefab/scenefab --version
# 显示 3.0.x，则自动检查下一个发布
# 若 v3.0.x 后端服务健康 → 用户手动选择 "回退到 2.4.x"

# 路径 B: 卸载 + 重装 v2.4
# Windows: 控制面板卸载 + 访问 scenefab.com/legacy 下载 dmg
# macOS: 拖入 Trash + 访问 legacy 链接
# Linux: apt remove scenefab + apt install scenefab=2.4.x
```

### 3.4 双轨期工程规范

在 M0-M7 双轨期：

- v2.4 主线仍然 release（新功能可以加）
- v3.0 黑盒单独维护，新 feature flag
- v2.4 与 v3.0 共用一个 `~/.scenefab/` 数据目录
- 项目文件 `.scenefab` schema **冻结**（v2.4 当前版本作为基线）

## 4. 完成定义（DoD）

### 4.1 代码级 DoD

```yaml
rust:
  cargo test --workspace --all-features:
    status: green
    coverage: ≥ 70%
  cargo clippy --workspace -- -D warnings:
    status: 0 warnings
  cargo fmt --check:
    status: 0 diff
  cargo deny check:
    advisories: 0
    bans: 0
    licenses: allow-list pass
    sources: only trusted
  cargo build --release:
    target: x86_64-unknown-linux-gnu
    target: x86_64-apple-darwin
    target: aarch64-apple-darwin
    target: x86_64-pc-windows-msvc
    aarch64-pc-windows-msvc

ts:
  pnpm typecheck: 0 errors
  pnpm lint: 0 errors (eslint + prettier)
  pnpm test: coverage ≥ 80%
  pnpm build: bundle ≤ 500KB gzipped (main)

features:
  - 35 commands + 24 events 全数接通
  - 11 LLM Provider 至少 5 个能跑真实调用（剩余 6 个走 mock）
  - 5 步流水线完整运行（noop + live）
  - 资源导入/删除/列表全数可用
  - 配置三层 fallback：keyring / yaml / env
  - 自动更新：从 mock URL → 下载 → SHA-256 → 应用 → 重启 闭环
  - 系统托盘 + 11 菜单项 + 单实例
  - 暗/亮主题运行时切换 < 80ms
  - zh-CN (488) + en-US (474) 全部 key 命中
  - 路径白名单 + CSP + keyring-rs 三件套
  - 数据迁移：v2.narrafilm → v3.scenefab 0 丢失
  - Playwright 15/15 稳定绿
  - 视觉回归 ≤ 1% 像素差异
  - 冷启动 P95 < 500ms / 三平台
```

### 4.2 流程级 DoD

```yaml
milestone_review:
  gate_0: TL+RA+FE+QA 四方签字 + ADR 发布
  gate_n: 自动化测试全绿 + QA 手工冒烟全过 + TL 签字

release:
  prerelease:
    - bin/scenefab --version 输出正确
    - 自动更新 PoC: 模拟升级 1 次成功
    - 启动验证：三平台各冒烟 2 小时
    - 数据迁移验证：12 个真实样本全过
  postrelease:
    - P1 紧急响应 < 4h
    - 自动更新成功率 ≥ 95% / 24h
    - 用户留存 ≥ 85% / 7d
```

### 4.3 业务级 DoD

| 维度     | 验收项                                                               |
| -------- | -------------------------------------------------------------------- |
| **功能** | 全部 v2.4 核心功能可使用（6 段冒烟视频全通）                         |
| **性能** | 5 步流水线 P95 < v2.4 × 0.85；冷启动 P95 < 500ms                     |
| **稳定** | 7 日崩溃率 < 0.1%                                                    |
| **更新** | 自动更新从 3.0.0 → 3.0.1 成功率 ≥ 95%                                |
| **数据** | 旧 `.narrafilm` → `.scenefab` 迁移 0 丢失                            |
| **i18n** | 全部 key 全数命中（中英双语 962 个 key）                             |
| **a11y** | axe-core 6 页面 0 violations                                         |
| **安全** | 三件套（路径白名单 + CSP + keyring） + API key 不外泄 + 插件沙箱隔离 |
| **合规** | macOS 公证（notarytool）/ Windows 代码签名 / Linux 发行签名          |

## 5. 签名矩阵（sign-off matrix）

```text
┌───────────┬──────┬──────┬──────┬──────┬──────────────────────────────────────────┐
│ Gate      │ TL   │ RA   │ FE   │ QA   │ 注                                      │
├───────────┼──────┼──────┼──────┼──────┼──────────────────────────────────────────┤
│ M0 Gate0  │  ✓   │  ✓   │  ✓   │  ✓   │ 三方都在场                                │
│ M1 Gate1  │  ✓   │  ✓   │  ✓   │  ✓   │ 同上                                      │
│ M2 Gate2  │  ✓   │  ✓   │  ✓   │  ○   │ QA 列席                                   │
│ M3 Gate3  │  ✓   │  ✓   │  ○   │  ✓   │ FE 列席                                   │
│ M4 Gate4  │  ✓   │  ✓   │  ✓   │  ✓   │ 全部在场                                  │
│ M5 Gate5  │  ✓   │  ✓   │  ○   │  ✓   │ FE 列席                                   │
│ M6 Gate6  │  ✓   │  ○   │  ✓   │  ✓   │ RA 列席                                   │
│ M7 Gate7  │  ✓   │  ○   │  ✓   │  ✓   │ FE+QA 主，RA 列席                         │
│ M8 Gate8  │  ✓   │  ✓   │  ✓   │  ✓   │ 全部在场                                  │
│ M9 Gate9  │  ✓   │  ✓   │  ✓   │  ✓   │ 全部在场（GA 前最高门槛）                  │
│ M10 GA    │  ✓   │  ✓   │  ✓   │  ✓   │ 全部在场                                   │
└───────────┴──────┴──────┴──────┴──────┴──────────────────────────────────────────┘
✓ = 必须签字  ○ = 列席
```

每个 Gate 必须至少有：

- 自动化测试报告 + 覆盖率报告
- QA 手工冒烟记录（≥ 6 个核心场景）
- TL 风险评估
- ADR 编号（如有新架构决策）

## 6. 应急流程演练

### 6.1 每季度演练项

| 演练项           | 频率 | 负责人 |
| ---------------- | ---- | ------ |
| 紧急回滚演练     | 季度 | TL+RA  |
| 自动更新失败恢复 | 季度 | RA     |
| 数据迁移恢复     | 季度 | RA     |
| 插件沙箱 fuzz    | 季度 | RA     |
| 安全扫描         | 月度 | RA+TL  |

### 6.2 实战演练（M8 阶段必做）

```text
1. 故意关闭 GitHub Releases 主仓库（使用 mock）
2. 触发自动更新 → 检查 fallback 路径
3. 注入 key 字符串到日志 → 自动 redacted
4. 关闭 keyring 服务 → 检测错误提示并降级
5. 制造 WASM 插件访问禁止目录 → 检测拦截
```

## 7. 持续监控（M10 后）

- **崩溃监控**：Sentry（self-hosted）上报 + 7 日去重
- **性能监控**：自研 sidecar 上报关键路径 latency（5 步流水线 + 冷启动）
- **Llm 监控**：每个 Provider 调用成功率 + 平均 latency + 平均 token 数
- **更新监控**：自动更新阶段耗时 + 失败原因分类
- **i18n 监控**：前端 fallback 触发频率（备用语言覆盖率）

所有监控数据脱敏后入仓 `~/.scenefab/metrics.db`，供 1.0 telemetry 团队同步访问。

## 8. 验收清单速查（Gate 9 直通）

```
□ 所有 PoC 关卡 Gate0-Gate9 通过（自动+人工）
□ Playwright 15/15 稳定绿
□ 视觉回归 ≤ 1% 像素差异
□ Tauri 冷启动 P95 < 500ms / 三平台
□ 5 步流水线 P95 < v2.4 × 0.85
□ LSP + tsc 0 错误
□ cargo clippy 0 警告
□ cargo deny 4 项均 pass
□ axe-core 6 page 0 violations
□ i18n 488+474 全数 key
□ keyring 不外泄 + 日志 redacted
□ 自动更新 PoC 闭环 1 次
□ 数据迁移 12 样本全过
□ macOS 公证 / Windows 代码签名通过
□ TL/RA/FE/QA 四方签字 Gate9
□ 已发布 v3.0 GA 公告
□ 客户支持渠道就位
```

---

> **结尾**：下一节进入 **10-acceptance.md**：M10 GA 公告模板 + 客户支持响应 SOP + 旧 Python 主线冻结流程。
