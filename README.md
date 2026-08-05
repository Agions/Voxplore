# apps/desktop · SceneFab v3.0 前端骨架

> **所属迁移**：[v3.0 · Python → Tauri+Rust+React](../../../docs/refactor/v3-migration/00-overview.md)
> **当前阶段**：M0 Gate 0（项目骨架）
> **后端包**：`src-tauri/` (Rust · Tauri 2 + Cargo)
> **前端包**：`src/` (React 19 + TypeScript 5 + Vite 7)

## 🚀 开发命令

```bash
# 安装依赖（首次或新依赖后）
pnpm install

# 启动 Tauri 开发模式（桌面窗口 + HMR）
pnpm tauri:dev

# 类型检查
pnpm typecheck

# Lint + Format
pnpm lint
pnpm format

# 单元测试
pnpm test                 # 单次
pnpm test:watch           # 监听
pnpm test:coverage        # 覆盖率

# E2E 测试（Playwright）
pnpm test:e2e

# 生产构建
pnpm tauri:build          # 三平台产物 (dmg/msi/AppImage)
```

## 📁 目录结构（v3.0 目标态 · 当前为骨架占位）

```
src/
├── main.tsx               # React 根
├── App.tsx                # 顶层路由出口
├── routes/                # TanStack Router 文件式路由
│   ├── __root.tsx
│   ├── index.tsx          # /
│   ├── production.tsx     # /production
│   ├── assets.tsx         # /assets
│   ├── settings.tsx       # /settings
│   ├── updates.tsx        # /updates
│   └── help.tsx           # /help
├── pages/                 # 页面组件（6 页面）
├── components/            # UI 组件
│   ├── ui/                # shadcn/ui 生成
│   ├── layout/            # AppShell + TopBar + Sidebar + ContentArea + StatusBar
│   ├── production/        # PipelineStepper + 5 步卡片 + ETA
│   ├── home/              # KpiCard + RecentProjectsList
│   ├── assets/            # DragDrop + 缩略图网格
│   ├── settings/          # LLM Selector + 密钥 UI + ThemeSwitch
│   ├── dashboard/         # CPU/Memory sparkline
│   ├── help/              # HelpPanelSheet
│   ├── palette/           # CommandPalette (cmdk)
│   ├── common/            # ErrorBoundary / Toast / ConfirmDialog
│   └── update/            # UpdateBanner
├── hooks/                 # 自定义 hook（替代 PySide6 ViewModel）
│   ├── useTauriCommand.ts # invoke + 类型化包装
│   ├── usePipeline.ts     # 5 步流水线 reducer（XState v5）
│   ├── useProject.ts      # 当前项目
│   ├── useAssets.ts       # AssetSummary
│   └── ...
├── stores/                # Zustand 6 store
│   ├── theme-store.ts
│   ├── project-store.ts
│   ├── pipeline-store.ts
│   ├── update-store.ts
│   ├── settings-store.ts
│   └── ui-store.ts
├── ipc/                   # ★ Tauri IPC 契约
│   ├── commands.ts        # 35 个 commands 类型化包装
│   ├── events.ts          # 24 个 events 类型化包装
│   ├── types.gen.ts       # 自动从 Rust 生成的 TS 类型
│   ├── errors.ts          # SceneFabError → 用户可读
│   └── schema.ts          # 命令/事件名称常量
├── lib/                   # 工具
│   ├── i18n/              # react-i18next 集成
│   ├── tokens/            # 设计令牌 (ds_tokens.py → CSS vars)
│   ├── format/            # 日期/大小/ETA 格式化
│   └── log/               # 前端日志 → Rust 收集
├── styles/                # globals.css + tokens.css
└── workers/               # Web Worker
    ├── pipeline.worker.ts # 5 步流水线 ETA 滑动窗口
    └── dashboard.worker.ts # 系统指标 60-sample

src-tauri/
├── Cargo.toml
├── tauri.conf.json
├── capabilities/
│   └── default.json       # ACL（Gate 0 仅 window:allow-*）
└── src/
    ├── main.rs
    └── lib.rs             # Tauri 入口（M0 仅占位 greet）
```

## 📚 关联文档

| 主题             | 文档                                                                                    |
| ---------------- | --------------------------------------------------------------------------------------- |
| 前端架构总览     | [§06-frontend-react.md](../../../docs/refactor/v3-migration/06-frontend-react.md)       |
| Tauri 集成与 IPC | [§07-tauri-integration.md](../../../docs/refactor/v3-migration/07-tauri-integration.md) |
| Rust 后端        | [§03-rust-backend.md](../../../docs/refactor/v3-migration/03-rust-backend.md)           |
| DoD 验收         | [§10-acceptance.md](../../../docs/refactor/v3-migration/10-acceptance.md)               |

## 📍 当前里程碑状态

- ✅ **M0 Gate 0 收尾**：pnpm create tauri-app 完成骨架、配置 + Cargo + TS 改造完成
- ⏳ **M0 Gate 0 验证**：cargo check + pnpm install + pnpm tauri dev 冒烟
- 📋 **M0 Gate 1 (M1)**：Rust workspace + 13 个 crate 骨架

> **ADR-112 计划**：方案 §06 写 React 18，但 create-tauri-app@latest 默认安装 React 19。决定跟随官方默认 + 重新评估兼容性（React 19 与 TanStack Query v5 / Zustand v5 完全兼容，且 WebView 内核已支持）。
