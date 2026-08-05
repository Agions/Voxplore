# SceneFab v3.0 · 前端架构 (React 18 + TypeScript 5 + Tauri 2)

> **基线版本**：v3.0.0
> **对应代码路径**：[apps/desktop/](../../../apps/desktop/)
> **关联文档**：[02-target-architecture.md](./02-target-architecture.md) · [03-rust-backend.md](./03-rust-backend.md) · [05-api-services-plugin-updater.md](./05-api-services-plugin-updater.md)
> **本文档范围**：从 `apps/desktop/index.html` 到 `apps/desktop/src-tauri/` 之间的全部前端代码规范、状态管理、UI 组件、设计令牌、i18n、测试策略。

## 0. TL;DR

把当前 1480 行 `src/app/ui/main/main_window/__init__.py`（PySide6 装配：TopBar/Sidebar/ContentArea/StatusBar）+ 4 个 ViewModel + 6 个 Page + 1 套 `ds_tokens.py` 设计令牌 + 自研 i18n + 5 步流水线状态机，重写为一个 React 18 + Vite 5 + TypeScript 5 前端，遵循：

| 维度     | v2.4 (Python/PySide6)             | **v3.0 (React 18 + TS 5 + Vite 5)**           |
| -------- | --------------------------------- | --------------------------------------------- |
| 入口     | `QMainWindow` + `QStackedWidget`  | **`<AppShell>` + TanStack Router `<Outlet>`** |
| 路由     | 手写 `PageRouter` 懒加载          | **TanStack Router 文件式路由 + lazy()**       |
| 状态管理 | 4 个 ViewModel + Qt `Signal`      | **Zustand 6 store + TanStack Query v5**       |
| 样式     | `ds_tokens.py` + QSS              | **CSS 变量 + Tailwind v4 tokens + shadcn/ui** |
| i18n     | 自研 `t(key)` (zh_CN/en_US)       | **react-i18next + ICU 复数**                  |
| 主题切换 | `ThemeAwareMixin` + `retranslate` | **CSS Variables + `data-theme` 属性 < 80ms**  |
| 流水线   | `QRunnable + QThreadPool`         | **XState v5 reducer + Web Worker**            |
| 系统指标 | `system.metric` event 1Hz         | **`listen('system.metric')` + RAF 节流**      |
| 测试     | pytest-qt                         | **vitest + Playwright + MSW + tauri-mock**    |
| 命令面板 | `QDialog` + 手写补全              | **cmdk (`<CommandPalette>`)**                 |
| 系统托盘 | `SystemTrayController` (PySide6)  | **`tauri-plugin-system-tray`**                |
| 辅助面板 | F1 触发 `HelpPanel` dock          | **`<Sheet side="right">` + Cmd+?**            |

## 1. apps/desktop 工程结构

### 1.1 完整目录树（`apps/desktop/`）

```text
apps/desktop/
├── .vscode/
│   ├── extensions.json                 # 推荐插件: ES7 React, Tailwind IntelliSense, Tauri, Error Lens
│   ├── settings.json                   # workspace trust + format on save
│   └── launch.json                     # 启动 Tauri dev 调试
├── public/
│   ├── tauri.svg                       # 占位 favicon
│   └── icons/icon-32.png               # 复制自 resources/icons/
├── src/                                # ★ 前端源码主目录
│   ├── main.tsx                        # React 根挂载 + StrictMode + Provider 链
│   ├── App.tsx                         # 路由根 + 全局错误边界
│   ├── env.ts                          # import.meta.env 类型化
│   ├── routes/                         # ★ TanStack Router 文件式路由
│   │   ├── __root.tsx                  # 根布局: <AppShell>
│   │   ├── index.tsx                   # / → HomePage
│   │   ├── production.tsx              # /production → ProductionPage
│   │   ├── assets.tsx                  # /assets → AssetsPage
│   │   ├── settings.tsx                # /settings → SettingsPage
│   │   ├── updates.tsx                 # /updates → UpdatePage
│   │   ├── help.tsx                    # /help → HelpPage
│   │   └── -routeTree.gen.ts           # 自动生成的路由树 (gitignore)
│   ├── pages/                          # ★ 页面组件 (与 PySide6 Page 一一对应)
│   │   ├── HomePage.tsx                # 对应 src/app/ui/main/pages/home_page.py
│   │   ├── ProductionPage.tsx          # 对应 production_page.py
│   │   ├── AssetsPage.tsx              # 对应 assets_page.py
│   │   ├── SettingsPage.tsx            # 对应 settings_page.py
│   │   ├── UpdatePage.tsx              # 对应 update/update_page.py
│   │   └── HelpPage.tsx                # 对应 help/panel.py
│   ├── components/                     # ★ UI 组件 (分层)
│   │   ├── ui/                         # shadcn/ui 生成 (Button/Card/Dialog/...)
│   │   ├── layout/
│   │   │   ├── AppShell.tsx            # 对应 main_window/__init__.py 装配
│   │   │   ├── TopBar.tsx              # 对应 TopBar
│   │   │   ├── Sidebar.tsx             # 对应 Sidebar
│   │   │   ├── ContentArea.tsx         # 对应 ContentArea (router outlet)
│   │   │   ├── StatusBar.tsx           # 对应 StatusBar
│   │   │   ├── TitleBar.tsx            # macOS 红绿黄按钮 + 拖拽区
│   │   │   └── UpdateBanner.tsx        # Phase 4 更新提示横幅
│   │   ├── production/
│   │   │   ├── PipelineStepper.tsx     # 5 步进度条
│   │   │   ├── PipelineStepCard.tsx    # 单步卡片 (pending/active/done/error)
│   │   │   ├── ETACounter.tsx          # Phase 3 进度预测显示
│   │   │   ├── RunnerModeBadge.tsx     # noop / live 标识
│   │   │   ├── ProductionSourcePicker.tsx # 源视频选择
│   │   │   └── PipelineStateMachine.tsx   # XState 5 reducer 包装
│   │   ├── home/
│   │   │   ├── KpiCard.tsx             # 4 状态卡片
│   │   │   ├── RecentProjectsList.tsx  # 最近项目列表
│   │   │   └── QuickStartSection.tsx   # 5 步流水线链接
│   │   ├── assets/
│   │   │   ├── AssetSummaryCard.tsx    # 媒体/脚本/音频/导出 计数
│   │   │   ├── MediaThumbnailGrid.tsx  # 缩略图网格
│   │   │   ├── ImportDropZone.tsx      # 拖拽上传 (替代 Qt dropEvent)
│   │   │   └── AssetContextMenu.tsx    # 右键菜单 (Radix DropdownMenu)
│   │   ├── settings/
│   │   │   ├── SettingsSection.tsx     # 通用分组容器
│   │   │   ├── SettingsRow.tsx         # 单行: label + control + 帮助
│   │   │   ├── ThemeSwitcher.tsx       # 暗/亮主题切换
│   │   │   ├── LlmProviderSelector.tsx # 11 个 LLM Provider 配置
│   │   │   ├── ApiKeyInput.tsx         # 密钥 input (mask + reveal)
│   │   │   ├── LanguageSelector.tsx    # 语言切换 (zh-CN/en-US)
│   │   │   ├── ProfilePicker.tsx       # 5 档性能 profile
│   │   │   └── SettingsDiagnostics.tsx # Phase 4 诊断信息
│   │   ├── dashboard/
│   │   │   ├── CpuSparkline.tsx        # 60 点 sparkline
│   │   │   ├── MemoryRing.tsx          # 内存环形进度
│   │   │   ├── DiskUsageBar.tsx
│   │   │   └── MetricHistoryChart.tsx  # 复用 Recharts
│   │   ├── help/
│   │   │   ├── HelpPanelSheet.tsx      # 右侧 Sheet (F1 触发)
│   │   │   ├── HelpSearchInput.tsx
│   │   │   └── HelpDocRenderer.tsx
│   │   ├── palette/
│   │   │   └── CommandPalette.tsx      # Cmd/Ctrl+K 唤起
│   │   └── common/
│   │       ├── ErrorBoundary.tsx       # 全局错误边界
│   │       ├── LoadingSpinner.tsx
│   │       ├── ConfirmDialog.tsx
│   │       ├── Toast.tsx               # 通用通知 (基于 sonner)
│   │       ├── TrayIndicator.tsx       # macOS/Windows 托盘 UI
│   │       └── LazyImage.tsx
│   ├── hooks/                          # ★ 自定义 hook (对应 PySide6 ViewModel)
│   │   ├── useTauriCommand.ts          # 统一 invoke 包装 (含 retry + 类型)
│   │   ├── useTauriEvent.ts            # 统一 event 订阅包装
│   │   ├── useTauriQuery.ts            # TanStack Query 适配器 (query → invoke)
│   │   ├── useTauriMutation.ts         # TanStack Query mutation 适配
│   │   ├── usePipeline.ts              # 5 步流水线 reducer (useReducer + XState)
│   │   ├── useProject.ts               # 当前打开项目 + 事件订阅
│   │   ├── useAssets.ts                # AssetSummary + recent_projects
│   │   ├── useDashboardMetrics.ts      # 系统指标 (CPU/内存/磁盘) 1Hz
│   │   ├── useUpdate.ts                # 更新状态机 (5 阶段)
│   │   ├── useSettings.ts              # 配置读写 + 持久化
│   │   ├── useCommandPalette.ts        # 命令面板状态
│   │   ├── useSystemTray.ts            # 系统托盘事件订阅
│   │   ├── useKeyboardShortcut.ts      # 全局快捷键 (Cmd+K / F1 / Cmd+,)
│   │   └── useTheme.ts                 # 主题切换 (< 80ms)
│   ├── stores/                         # ★ Zustand store (按业务域切片)
│   │   ├── index.ts                    # 聚合 re-export
│   │   ├── theme-store.ts              # 主题 / 语言 / 主题运行时
│   │   ├── project-store.ts            # 当前项目 + 最近项目 + 打开/关闭
│   │   ├── pipeline-store.ts           # 5 步流水线状态 + ETA
│   │   ├── update-store.ts             # 更新状态机 (Phase 1-5)
│   │   ├── ui-store.ts                 # UI 临时状态 (sheet 打开 / 命令面板)
│   │   └── settings-store.ts           # 配置 (LLM Provider / 性能 profile / 密钥引用)
│   ├── ipc/                            # ★ IPC 契约层
│   │   ├── commands.ts                 # 所有 invoke 命令的类型化包装
│   │   ├── events.ts                   # 所有 listen 事件的类型化包装
│   │   ├── types.gen.ts                # ★ 自动生成的 DTO 类型 (specta → ts)
│   │   ├── errors.ts                   # SceneFabError → 用户可读错误
│   │   └── schema.ts                   # 命令/事件名称常量
│   ├── lib/                            # ★ 工具
│   │   ├── i18n/
│   │   │   ├── index.ts                # i18next 初始化
│   │   │   ├── zh-CN.ts                # 从 messages_zh_CN.py 提取
│   │   │   ├── en-US.ts                # 从 messages_en_US.py 提取
│   │   │   └── namespaces.ts           # 命名空间常量
│   │   ├── tokens/
│   │   │   ├── css-vars.ts             # 设计令牌 → CSS 变量映射
│   │   │   └── tailwind-presets.ts     # Tailwind v4 主题预设
│   │   ├── format/
│   │   │   ├── date.ts                 # dayjs 包装
│   │   │   ├── size.ts                 # 文件大小 B/KB/MB/GB
│   │   │   └── eta.ts                  # Phase 3 ETA 格式化
│   │   ├── log/
│   │   │   └── logger.ts               # 前端 console + 收集到 Rust 端
│   │   └── command-registry.ts         # 命令面板注册表 (Cmd+K 项)
│   ├── styles/
│   │   ├── globals.css                 # Tailwind v4 @import + CSS 变量定义
│   │   ├── tokens.css                  # 设计令牌 (dark/light)
│   │   └── scrollbar.css               # 自定义滚动条
│   └── workers/
│       ├── pipeline.worker.ts          # 5 步流水线 worker (Worker)
│       └── dashboard.worker.ts         # 指标采样 + 滑动窗口
├── src-tauri/                          # ★ Rust 后端 (单独文档)
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── capabilities/
│   │   └── default.json
│   └── src/
│       ├── main.rs                     # bootstrap
│       ├── lib.rs                      # run() 函数 + AppContext
│       ├── commands/                   # Tauri Command 实现
│       └── ipc/                        # DTO + Error 定义
├── tests/                              # ★ Vitest + Playwright 测试
│   ├── unit/                           # 纯单元 (Vitest)
│   ├── component/                      # Testing Library
│   ├── e2e/                            # Playwright (启动 Tauri)
│   └── fixtures/
│       ├── tauri-mock.ts               # 模拟 invoke / emit
│       └── i18n.ts                     # 测试语言 stub
├── .storybook/                         # ★ Storybook (可选, M8 引入)
├── index.html                          # Vite 入口 HTML
├── package.json
├── tsconfig.json                       # 严格模式 + 路径别名
├── tsconfig.node.json                  # Vite 配置专用
├── vite.config.ts                      # ★ Vite 5 配置 (Tauri 适配)
├── tailwind.config.ts                  # Tailwind v4 内联 presets
├── postcss.config.js
├── components.json                     # shadcn/ui 配置
├── playwright.config.ts                # Playwright 配置
├── vitest.config.ts
├── .env.development
├── .env.production
├── .eslintrc.json
├── .prettierrc.json
├── .gitignore
└── README.md
```

### 1.2 关键路径别名（`tsconfig.json`）

```jsonc
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable", "WebWorker"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "verbatimModuleSyntax": true,
    "isolatedModules": true,
    "skipLibCheck": true,
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "paths": {
      "@/*": ["./src/*"],
      "@ui/*": ["./src/components/ui/*"],
      "@hooks/*": ["./src/hooks/*"],
      "@stores/*": ["./src/stores/*"],
      "@ipc/*": ["./src/ipc/*"],
      "@lib/*": ["./src/lib/*"],
      "@pages/*": ["./src/pages/*"],
      "@components/*": ["./src/components/*"],
    },
    "baseUrl": ".",
  },
  "include": ["src", "tests"],
  "exclude": ["src-tauri", "dist", "node_modules"],
}
```

### 1.3 `vite.config.ts`（Tauri 2 适配）

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { TanStackRouterVite } from "@tanstack/router-vite-plugin";
import path from "node:path";

// https://vite.dev/config/
export default defineConfig(async () => ({
  plugins: [
    react({
      // React 18 fast refresh
      fastRefresh: true,
      babel: {
        plugins: [["@babel/plugin-syntax-decimal", { optional: true }]],
      },
    }),
    TanStackRouterVite({
      // 文件式路由 → src/routes/
      routesDirectory: "./src/routes",
      generatedRouteTree: "./src/routes/-routeTree.gen.ts",
      autoCodeSplitting: true,
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@ui": path.resolve(__dirname, "./src/components/ui"),
      "@hooks": path.resolve(__dirname, "./src/hooks"),
      "@stores": path.resolve(__dirname, "./src/stores"),
      "@ipc": path.resolve(__dirname, "./src/ipc"),
      "@lib": path.resolve(__dirname, "./src/lib"),
      "@pages": path.resolve(__dirname, "./src/pages"),
      "@components": path.resolve(__dirname, "./src/components"),
    },
  },
  // Tauri 固定端口 + HMR
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    host: "127.0.0.1",
    hmr: { protocol: "ws", host: "127.0.0.1", port: 1421 },
    watch: {
      // 监听 src 而忽略 src-tauri 由 cargo 自身处理
      ignored: ["**/src-tauri/**"],
    },
  },
  envPrefix: ["VITE_", "TAURI_"],
  build: {
    target: ["es2022", "chrome105", "safari14"],
    minify: !process.env.TAURI_DEBUG ? "esbuild" : false,
    sourcemap: !!process.env.TAURI_DEBUG,
    rollupOptions: {
      output: {
        manualChunks: {
          // 拆分 vendor 提升首屏
          "react-vendor": ["react", "react-dom"],
          tanstack: ["@tanstack/react-query", "@tanstack/react-router"],
          i18n: ["i18next", "react-i18next"],
        },
      },
    },
  },
  // 性能预算
  performance: {
    hints: "warning",
    maxAssetSize: 600_000, // 主 bundle ≤ 600KB
    maxEntrypointSize: 600_000,
  },
  // ★ Tauri 关键: 全部依赖预打包防止 dev 模式下被 native lib 误解析
  optimizeDeps: {
    exclude: ["@tauri-apps/api"],
  },
}));
```

## 2. 路由设计（TanStack Router v1）

> **为什么不用 React Router**：TanStack Router 100% 类型安全（路由参数、loader data、search 都是 TS 类型）+ 文件式 + 内置 code splitting + 与 TanStack Query 深度集成。这是 v3.0 一个关键不变量：路由类型不能漂移。

### 2.1 路由树（文件 → 路径）

```
src/routes/__root.tsx              → 根布局（AppShell + ErrorBoundary）
src/routes/index.tsx               → /
src/routes/production.tsx          → /production
src/routes/assets.tsx              → /assets
src/routes/settings.tsx            → /settings
src/routes/updates.tsx             → /updates
src/routes/help.tsx                → /help
src/routes/$projectId.tsx          → /:projectId (打开的项目详情，子路由)
src/routes/$projectId.script.tsx   → /:projectId/script
src/routes/$projectId.export.tsx   → /:projectId/export
```

### 2.2 `__root.tsx` 根布局

```tsx
import { Outlet, createRootRouteWithContext } from "@tanstack/react-router";
import { QueryClient } from "@tanstack/react-query";
import { AppShell } from "@components/layout/AppShell";
import { ErrorBoundary } from "@components/common/ErrorBoundary";
import type { I18nContext } from "@lib/i18n";

export const Route = createRootRouteWithContext<{
  queryClient: QueryClient;
  i18n: I18nContext;
}>()({
  component: RootComponent,
  errorComponent: ErrorBoundary,
  notFoundComponent: NotFound,
});

function RootComponent() {
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}
```

### 2.3 路由级 `loader`（数据预取，TanStack Query 集成）

```tsx
// src/routes/assets.tsx
import { createFileRoute } from "@tanstack/react-router";
import { AssetsPage } from "@pages/AssetsPage";
import { assetsQueryOptions } from "@ipc/queries";

export const Route = createFileRoute("/assets")({
  component: AssetsPage,
  loader: ({ context: { queryClient } }) =>
    queryClient.ensureQueryData(assetsQueryOptions()),
  // 路由级 meta
  meta: () => [{ title: "SceneFab · 资产管理" }],
});
```

### 2.4 路由守卫（受保护页面）

所有路由默认不需要登录（Tauri 应用内置身份 = 操作系统用户）；命令级权限由 Tauri `Capability` 控制。当 `update-store.state === 'BLOCKING'` 时，把 `/settings/updates` 设为 `pending`：

```tsx
import { redirect } from "@tanstack/react-router";

const enforceUpdateGuard = (location: RouterLocation) => {
  const state = useUpdateStore.getState().state;
  if (state === "BLOCKING" && !location.pathname.startsWith("/updates")) {
    throw redirect({ to: "/updates" });
  }
};
```

## 3. 状态管理设计

> **状态分层原则**：服务端状态（项目列表 / 资源 / 系统指标）进 TanStack Query；客户端 UI 状态（命令面板 / Sheet / 当前选中 step）进 Zustand；派生状态用 useMemo + selectors；跨组件持久化（如主题）直接进 Zustand persist 中间件。

### 3.1 TanStack Query 设计（5 套 Query）

```ts
// src/ipc/queries.ts
import { queryOptions, useQuery, useMutation } from "@tanstack/react-query";
import { commands } from "@ipc/commands"; // 类型化的 invoke
import type {
  AssetSummary,
  RecentProjectInfo,
  ProjectDescriptor,
} from "@ipc/types.gen";

// ────── Projects ──────
export const recentProjectsQueryOptions = () =>
  queryOptions({
    queryKey: ["projects", "recent"],
    queryFn: () => commands.recentProjects(),
    staleTime: 30_000,
  });

export const currentProjectQueryOptions = () =>
  queryOptions({
    queryKey: ["projects", "current"],
    queryFn: () => commands.currentProject(),
    staleTime: 5_000,
  });

// ────── Assets ──────
export const assetsQueryOptions = () =>
  queryOptions({
    queryKey: ["assets", "summary"],
    queryFn: () => commands.assetsSummary(),
    staleTime: 5_000,
  });

// ────── Settings ──────
export const settingsQueryOptions = () =>
  queryOptions({
    queryKey: ["settings"],
    queryFn: () => commands.getSettings(),
    staleTime: Infinity, // 配置变更触发 invalidate
  });

// ────── Update ──────
export const updateStatusQueryOptions = () =>
  queryOptions({
    queryKey: ["update", "status"],
    queryFn: () => commands.updateStatus(),
    refetchInterval: 5_000, // 启动期 + 后台期都轮询
    staleTime: 0,
  });

// ────── LLM Providers ──────
export const llmProvidersQueryOptions = () =>
  queryOptions({
    queryKey: ["llm", "providers"],
    queryFn: () => commands.listLlmProviders(),
    staleTime: 60_000,
  });
```

### 3.2 Tauri IPC 适配（关键 Hook）

```ts
// src/hooks/useTauriCommand.ts
import {
  useQuery,
  useMutation,
  type UseQueryOptions,
  type UseMutationOptions,
} from "@tanstack/react-query";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { useEffect, useRef, useState } from "react";

/**
 * 类型安全的 Tauri invoke 包装
 * - 自动 retry (默认 2 次)
 * - 统一错误转换 (Rust SceneFabError → React 可读 message)
 * - dev 环境打印调用日志
 */
export async function invokeCmd<T>(
  cmd: string,
  args?: Record<string, unknown>,
  opts: { retries?: number; timeout?: number } = {},
): Promise<T> {
  const { retries = 2, timeout = 15_000 } = opts;
  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await invoke<T>(cmd, args, { timeoutMs: timeout });
    } catch (e) {
      lastError = e;
      if (attempt < retries && isTransientError(e)) {
        await sleep(100 * Math.pow(2, attempt));
        continue;
      }
      throw toUserReadableError(e);
    }
  }
  throw toUserReadableError(lastError);
}

/** 业务级 query hook */
export function useTauriQuery<TData>(
  key: readonly unknown[],
  cmd: string,
  args?: Record<string, unknown>,
  options?: Omit<UseQueryOptions<TData, SceneFabError>, "queryKey" | "queryFn">,
) {
  return useQuery<TData, SceneFabError>({
    queryKey: key,
    queryFn: () => invokeCmd<TData>(cmd, args),
    ...options,
  });
}

/** 业务级 mutation hook */
export function useTauriMutation<TVariables, TData>(
  cmd: string,
  options?: UseMutationOptions<TData, SceneFabError, TVariables>,
) {
  return useMutation<TData, SceneFabError, TVariables>({
    mutationFn: (variables) =>
      invokeCmd<TData>(cmd, variables as Record<string, unknown>),
    ...options,
  });
}

/** 事件订阅（带 cleanup + 类型化） */
export function useTauriEvent<TPayload>(
  eventName: string,
  handler: (payload: TPayload) => void,
  deps: unknown[] = [],
) {
  const handlerRef = useRef(handler);
  useEffect(() => {
    handlerRef.current = handler;
  });

  useEffect(() => {
    let unlisten: UnlistenFn | undefined;
    (async () => {
      unlisten = await listen<TPayload>(eventName, (e) =>
        handlerRef.current(e.payload),
      );
    })();
    return () => {
      unlisten?.();
    };
  }, [eventName, ...deps]);
}
```

### 3.3 Zustand Store 设计（6 个）

```ts
// src/stores/theme-store.ts
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { invoke } from "@tauri-apps/api/core";

export type ThemeMode = "light" | "dark" | "system";

interface ThemeState {
  mode: ThemeMode;
  resolved: "light" | "dark";
  locale: "zh-CN" | "en-US";
  setMode: (m: ThemeMode) => Promise<void>;
  setLocale: (l: "zh-CN" | "en-US") => Promise<void>;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      mode: "system",
      resolved:
        typeof window !== "undefined"
          ? window.matchMedia("(prefers-color-scheme: dark)").matches
            ? "dark"
            : "light"
          : "light",
      locale: "zh-CN",
      setMode: async (m) => {
        set({ mode: m });
        const resolved = resolveTheme(m);
        set({ resolved });
        document.documentElement.dataset.theme = resolved;
        // 同步到 Rust 端持久化
        await invoke("set_theme", { mode: m });
      },
      setLocale: async (l) => {
        set({ locale: l });
        await invoke("set_locale", { locale: l });
        await i18n.changeLanguage(l); // 全局 i18n
      },
    }),
    {
      name: "scenefab-theme",
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ mode: s.mode, locale: s.locale }),
    },
  ),
);
```

```ts
// src/stores/project-store.ts —— 当前打开项目
import { create } from "zustand";
import type { ProjectDescriptor } from "@ipc/types.gen";

interface ProjectState {
  current: ProjectDescriptor | null;
  recentPaths: string[];
  setCurrent: (p: ProjectDescriptor | null) => void;
  setRecent: (paths: string[]) => void;
}

export const useProjectStore = create<ProjectState>((set) => ({
  current: null,
  recentPaths: [],
  setCurrent: (p) => set({ current: p }),
  setRecent: (paths) => set({ recentPaths: paths }),
}));
```

```ts
// src/stores/pipeline-store.ts —— 5 步流水线状态机 (XState v5)
import { create } from "zustand";
import { useMachine } from "@xstate/react";
import { pipelineMachine } from "@components/production/PipelineStateMachine";

export const usePipelineStore = create(() => ({
  /* selectors */
}));

/** 在 ProductionPage 内部使用 */
export function usePipelineController() {
  const [snapshot, send] = useMachine(pipelineMachine);
  return {
    state: snapshot.value,
    currentStep: snapshot.context.currentStep,
    stepStatuses: snapshot.context.stepStatuses,
    etaSeconds: snapshot.context.etaSeconds,
    runnerMode: snapshot.context.runnerMode,
    start: (sourceVideo: string, context: string) =>
      send({ type: "START", sourceVideo, context }),
    reset: () => send({ type: "RESET" }),
  };
}
```

```ts
// src/stores/update-store.ts —— 5 阶段更新状态机
type UpdatePhase =
  | "IDLE" // 未启动检查
  | "CHECKING" // 网络请求 GitHub Releases
  | "AVAILABLE" // 有新版本但未下载
  | "DOWNLOADING" // 下载增量包
  | "BLOCKING" // 强制更新，下载完成后未安装不允许使用
  | "READY" // 已下载，待用户重启
  | "APPLYING" // 应用补丁
  | "DONE" // 已完成
  | "ERROR";

interface UpdateState {
  phase: UpdatePhase;
  progress: number; // 0..1
  message: string | null;
  setPhase: (p: UpdatePhase) => void;
  setProgress: (n: number) => void;
  setMessage: (m: string | null) => void;
}
```

```ts
// src/stores/ui-store.ts —— 临时 UI 状态
interface UiState {
  paletteOpen: boolean;
  helpSheetOpen: boolean;
  settingsDrawerOpen: boolean;
  togglePalette: () => void;
  toggleHelp: () => void;
}
```

```ts
// src/stores/settings-store.ts —— 配置 (镜像 Rust Settings)
import { create } from "zustand";
import type { Settings } from "@ipc/types.gen";

interface SettingsState {
  draft: Settings | null;
  setDraft: (s: Settings) => void;
  reset: () => void;
}
```

### 3.4 React Query + Zustand 边界

| 数据种                                  | 归属                                |
| --------------------------------------- | ----------------------------------- |
| 服务端真理源（项目/配置/资源/更新/LLM） | **TanStack Query**                  |
| 客户端瞬时 UI 状态                      | **Zustand**                         |
| 客户端持久化偏好（主题/语言）           | **Zustand + persist** + 同步到 Rust |
| 流水线运行时状态                        | **XState v5** reducer               |
| 派生数据                                | **`useMemo`** + selector            |
| 表单中间态                              | **react-hook-form**                 |

## 4. UI 组件库（shadcn/ui + Tailwind v4）

### 4.1 为什么选 shadcn/ui（不是 MUI / Ant Design）

1. **零运行时依赖**：每个组件是受控的 Radix UI + Tailwind，可读可改可裁剪。
2. **完美容合 Tauri**：不依赖 emotion/styled-components，不会和 Tauri System WebView 冲突。
3. **Tree-shakable**：CLI `npx shadcn-ui add button` 把每个组件作为源码复制进 `src/components/ui/`，无 bundle 黑盒。
4. **完美支持 dark mode**：基于 CSS 变量，与设计令牌迁移（§5）天然契合。
5. **国际化友好**：所有文案通过 prop 传入，避免 antd `message` 之类全局 API。

### 4.2 `components.json`

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/styles/globals.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@components",
    "utils": "@lib/utils",
    "ui": "@components/ui",
    "lib": "@lib",
    "hooks": "@hooks"
  }
}
```

### 4.3 `tailwind.config.ts`（v4 内联配置）

Tailwind v4 推荐把 tokens 直接写进 CSS 文件（`@theme`），`tailwind.config.ts` 变为可选：

```ts
import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

export default {
  darkMode: ["class", '[data-theme="dark"]'],
  content: ["./src/**/*.{ts,tsx,html,css}"],
  theme: { extend: {} },
  plugins: [animate],
} satisfies Config;
```

```css
/* src/styles/globals.css —— Tailwind v4 内联 tokens */
@import "tailwindcss";

@theme {
  --color-bg-base: oklch(0.98 0 0);
  --color-bg-elevated: oklch(1 0 0);
  --color-bg-surface: oklch(0.96 0.005 250);
  --color-text-primary: oklch(0.18 0.02 250);
  --color-text-secondary: oklch(0.42 0.02 250);
  --color-text-muted: oklch(0.58 0.015 250);
  --color-border-default: oklch(0.9 0.005 250);
  --color-border-subtle: oklch(0.95 0.005 250);
  --color-primary: oklch(0.55 0.18 250);
  --color-primary-lightest: oklch(0.95 0.04 250);
  --color-primary-darker: oklch(0.4 0.18 250);
  --color-success: oklch(0.65 0.15 145);
  --color-warning: oklch(0.75 0.13 80);
  --color-error: oklch(0.55 0.22 27);
  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --radius-xl: 1rem;
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.5rem;
  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
  --shadow-elevated:
    0 1px 2px rgba(0, 0, 0, 0.05), 0 4px 12px rgba(0, 0, 0, 0.08);
  --font-family-ui: "Inter", system-ui, sans-serif;
}

[data-theme="dark"] {
  --color-bg-base: oklch(0.16 0.02 250);
  --color-bg-elevated: oklch(0.22 0.02 250);
  --color-bg-surface: oklch(0.2 0.02 250);
  --color-text-primary: oklch(0.92 0.01 250);
  --color-text-secondary: oklch(0.72 0.02 250);
  --color-text-muted: oklch(0.55 0.02 250);
  --color-border-default: oklch(0.32 0.02 250);
  --color-border-subtle: oklch(0.28 0.02 250);
}
```

### 4.4 预生成的 shadcn/ui 组件清单

```
src/components/ui/
├── button.tsx               # Button (含 default/outline/ghost/destructive/loading)
├── card.tsx                 # Card / CardHeader / CardTitle / CardContent / CardFooter
├── dialog.tsx               # Dialog / DialogTrigger / DialogContent (基于 Radix)
├── dropdown-menu.tsx        # 替代 Qt 右键菜单 (替代 assets_page.py QMenu)
├── input.tsx                # Input (受控 + 非受控)
├── label.tsx                # Label
├── progress.tsx             # Progress (Pipeline ETA 显示)
├── scroll-area.tsx          # ScrollArea (替代 Qt QScrollArea)
├── select.tsx               # Select (替代 QComboBox)
├── separator.tsx            # Separator
├── sheet.tsx                # ★ Sheet side="right" 替代 HelpPanel dock
├── switch.tsx               # Switch (替代 QCheckBox)
├── tabs.tsx                 # Tabs
├── textarea.tsx             # Textarea
├── toast.tsx                # 基于 sonner (替代临时消息)
├── tooltip.tsx              # Tooltip (替代 setToolTip)
├── command.tsx              # ★ cmdk 命令面板
├── badge.tsx                # Badge (runner_mode badge, kpi status)
├── skeleton.tsx             # 骨架屏
├── slider.tsx               # Slider
└── form.tsx                 # react-hook-form 集成
```

## 5. 设计令牌迁移（PySide6 → CSS 变量 + Tailwind v4）

> 这是 v3.0 UI 端最高 ROI 的工作。把 PySide6 的 `ds_tokens.py`（199 个 token：颜色/字号/字重/圆角/阴影/间距）整体迁移为 CSS 自定义属性，主题切换从 QSS 重建改为 `<html data-theme="dark">` 切换，**目标：< 80ms 切换时延（v2.4 在 macOS 上 P95 约 320ms）**。

### 5.1 ds_tokens.py → design-tokens.json（中间表示）

```jsonc
// docs/refactor/v3-migration/design-tokens.json
{
  "$schema": "https://scenefab.dev/schemas/tokens/v1.json",
  "color": {
    "bg": {
      "base": { "$value": "oklch(0.98 0 0)", "$dark": "oklch(0.16 0.02 250)" },
      "elevated": { "$value": "oklch(1 0 0)", "$dark": "oklch(0.22 0.02 250)" },
      "surface": {
        "$value": "oklch(0.96 0.005 250)",
        "$dark": "oklch(0.20 0.02 250)",
      },
    },
    "text": {
      "primary": {
        "$value": "oklch(0.18 0.02 250)",
        "$dark": "oklch(0.92 0.01 250)",
      },
      "secondary": {
        "$value": "oklch(0.42 0.02 250)",
        "$dark": "oklch(0.72 0.02 250)",
      },
      "muted": {
        "$value": "oklch(0.58 0.015 250)",
        "$dark": "oklch(0.55 0.02 250)",
      },
    },
    "border": {
      "default": {
        "$value": "oklch(0.90 0.005 250)",
        "$dark": "oklch(0.32 0.02 250)",
      },
      "subtle": {
        "$value": "oklch(0.95 0.005 250)",
        "$dark": "oklch(0.28 0.02 250)",
      },
    },
    "primary": {
      "base": { "$value": "oklch(0.55 0.18 250)" },
      "lightest": { "$value": "oklch(0.95 0.04 250)" },
      "darker": { "$value": "oklch(0.40 0.18 250)" },
    },
    "state": {
      "success": { "$value": "oklch(0.65 0.15 145)" },
      "warning": { "$value": "oklch(0.75 0.13 80)" },
      "error": { "$value": "oklch(0.55 0.22 27)" },
    },
  },
  "spacing": {
    "xs": { "$value": "0.25rem" },
    "sm": { "$value": "0.5rem" },
    "md": { "$value": "1rem" },
    "lg": { "$value": "1.5rem" },
    "xl": { "$value": "2rem" },
    "2xl": { "$value": "3rem" },
  },
  "radius": {
    "sm": { "$value": "0.25rem" },
    "md": { "$value": "0.5rem" },
    "lg": { "$value": "0.75rem" },
    "xl": { "$value": "1rem" },
    "full": { "$value": "9999px" },
  },
  "typography": {
    "size": {
      "xs": { "$value": "0.75rem" },
      "sm": { "$value": "0.875rem" },
      "base": { "$value": "1rem" },
      "lg": { "$value": "1.125rem" },
      "xl": { "$value": "1.5rem" },
    },
    "weight": {
      "regular": { "$value": "400" },
      "medium": { "$value": "500" },
      "semibold": { "$value": "600" },
      "bold": { "$value": "700" },
    },
    "family": {
      "ui": { "$value": "'Inter', system-ui, sans-serif" },
      "mono": { "$value": "ui-monospace, 'JetBrains Mono', monospace" },
    },
  },
  "shadow": {
    "elevated": {
      "$value": "0 1px 2px rgba(0,0,0,0.05), 0 4px 12px rgba(0,0,0,0.08)",
    },
    "popover": {
      "$value": "0 4px 8px rgba(0,0,0,0.06), 0 12px 24px rgba(0,0,0,0.10)",
    },
  },
}
```

### 5.2 Token → CSS Variable 映射规则

```ts
// src/lib/tokens/css-vars.ts —— 自动生成器
import tokens from "@lib/tokens/design-tokens.json";

export function generateCssVars(): { light: string; dark: string } {
  const light: string[] = [];
  const dark: string[] = [];

  const walk = (obj: any, prefix: string[]) => {
    for (const [k, v] of Object.entries(obj)) {
      if ("$value" in v) {
        const name = `--color-${prefix.concat(k).join("-")}`;
        if ("$dark" in v) {
          light.push(`${name}: ${(v as any).$value};`);
          dark.push(`${name}: ${(v as any).$dark};`);
        } else {
          light.push(`${name}: ${(v as any).$value};`);
          if (prefix[0] === "color") {
            dark.push(`${name}: ${(v as any).$value};`); // dark 模式下保持
          }
        }
      } else {
        walk(v, [...prefix, k]);
      }
    }
  };

  walk(tokens, []);
  return { light: light.join("\n"), dark: dark.join("\n") };
}

/**
 * 在构建期通过 Vite 插件运行:
 *   plugin('vite-plugin-design-tokens') → 在 globals.css 顶部注入上述内容
 */
```

### 5.3 主题切换性能

| 实现              | 切换时延 (P95) | 备注                                            |
| ----------------- | -------------- | ----------------------------------------------- |
| v2.4 (QSS 重建)   | 320ms          | 需要重建所有 widget 样式表                      |
| v3.0 CSS 变量切换 | **< 80ms**     | `document.documentElement.dataset.theme = next` |

切换函数：

```ts
// src/hooks/useTheme.ts
export function useTheme() {
  const { mode, resolved, setMode } = useThemeStore();

  useEffect(() => {
    document.documentElement.dataset.theme = resolved;
    // 同步到 Rust 端以便托盘菜单 + 系统通知使用相同主题
    invoke("set_theme", { mode: resolved });
  }, [resolved]);

  return { mode, resolved, setMode };
}
```

## 6. 国际化（react-i18next）

> `src/app/ui/i18n/messages_zh_CN.py` 共 488 条文案，`messages_en_US.py` 共 474 条；本节给出从 Python dict 到 i18next JSON 的转换规则。

### 6.1 Python → JSON 转换脚本（一次性）

```python
# scripts/migrate_i18n.py
import re, json, ast
from pathlib import Path

src_zh = Path('src/app/ui/i18n/messages_zh_CN.py')
src_en = Path('src/app/ui/i18n/messages_en_US.py')
out_zh = Path('apps/desktop/src/lib/i18n/zh-CN.json')
out_en = Path('apps/desktop/src/lib/i18n/en-US.json')

def parse(path: Path) -> dict[str, str]:
    src = path.read_text(encoding='utf-8')
    # MESSAGES = { "namespace.key": "value", ... }
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'MESSAGES':
                    msgs: dict[str, str] = {}
                    for k, v in zip(node.value.keys, node.value.values):
                        if isinstance(v, ast.Constant):
                            msgs[k.s] = v.value
                    return msgs
    return {}

def to_namespace(flat: dict[str, str]) -> dict:
    """'home.greeting' → { home: { greeting: '...' } }"""
    out = {}
    for k, v in flat.items():
        cur = out
        parts = k.split('.')
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = v
    return out

zh = parse(src_zh)
en = parse(src_en)
out_zh.write_text(json.dumps(to_namespace(zh), ensure_ascii=False, indent=2), encoding='utf-8')
out_en.write_text(json.dumps(to_namespace(en), ensure_ascii=False, indent=2), encoding='utf-8')
print(f'zh: {len(zh)} keys, en: {len(en)} keys')
```

> 运行：`python scripts/migrate_i18n.py`，输出 zh-CN.json (488) / en-US.json (474)。

### 6.2 i18next 初始化（`src/lib/i18n/index.ts`）

```ts
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import zhCN from "./zh-CN.json";
import enUS from "./en-US.json";

export interface I18nContext {
  locale: "zh-CN" | "en-US";
  changeLocale: (l: "zh-CN" | "en-US") => Promise<void>;
}

export const i18nReady = i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: "zh-CN",
    supportedLngs: ["zh-CN", "en-US"],
    ns: [
      "common",
      "home",
      "production",
      "assets",
      "settings",
      "update",
      "help",
      "palette",
    ],
    defaultNS: "common",
    resources: {
      "zh-CN": { common: zhCN.common /* ... */ },
      "en-US": { common: enUS.common /* ... */ },
    },
    interpolation: { escapeValue: false },
    detection: {
      order: ["querystring", "localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "scenefab-locale",
    },
    react: { useSuspense: false },
  });
```

### 6.3 命名空间拆分（按页面）

| Namespace    | Keys 来源                               | 数量 |
| ------------ | --------------------------------------- | ---- |
| `common`     | `app.*`, `nav.*`, `action.*`, `toast.*` | ~120 |
| `home`       | `home.*`                                | ~36  |
| `production` | `production.*`, `step.*`, `eta.*`       | ~95  |
| `assets`     | `assets.*`                              | ~48  |
| `settings`   | `settings.*`, `llm.*`, `profile.*`      | ~85  |
| `update`     | `update.*`                              | ~52  |
| `help`       | `help.*`                                | ~28  |
| `palette`    | `palette.*`, `command.*`                | ~24  |

### 6.4 Python t(key) → React useTranslation(key)

| Python 调用                 | React 等价                                            |
| --------------------------- | ----------------------------------------------------- |
| `t("home.title")`           | `const { t } = useTranslation('home'); t('title')`    |
| `t("step.active", count=5)` | `t('active', { count: 5 })` (Plural: `_one`/`_other`) |
| `f"Mono {t('a.b')}"`        | `<Trans i18nKey="a.b" />` 或 t() 拼接                 |
| `i18n_load(locale)`         | `i18n.changeLanguage(locale)`                         |

### 6.5 Plurals（ICU）

```jsonc
{
  "step": {
    "active": "{count, plural, one {# 步进行中} other {# 步进行中}}",
    "completed": "{done, plural, =0 {未完成} other {已完成 # 步}}",
  },
}
```

调用：

```tsx
<span>{t("step.active", { count: activeCount })}</span>
```

## 7. PySide6 → React 组件映射

> 这一节是给前端工程师按表迁移用的速查。每个 PySide6 类/ViewModel 给出对应的 React 组件路径和关键注意点。

### 7.1 主窗口装配

| PySide6 文件                                    | React 组件                                                 |
| ----------------------------------------------- | ---------------------------------------------------------- |
| `src/app/ui/main/main_window/__init__.py`       | `src/components/layout/AppShell.tsx`                       |
| ─ TopBar                                        | `src/components/layout/TopBar.tsx`                         |
| ─ Sidebar                                       | `src/components/layout/Sidebar.tsx`                        |
| ─ ContentArea                                   | `src/components/layout/ContentArea.tsx`（含 `<Outlet />`） |
| ─ StatusBar                                     | `src/components/layout/StatusBar.tsx`                      |
| ─ TitleBar                                      | `src/components/layout/TitleBar.tsx`                       |
| ─ SystemTrayController                          | `src/hooks/useSystemTray.ts`                               |
| ─ PageRouter (lazy)                             | TanStack Router 文件式自动 lazy()                          |
| ─ HelpPanel dock                                | `src/components/help/HelpPanelSheet.tsx`                   |
| ─ CommandPalette (Cmd+K)                        | `src/components/palette/CommandPalette.tsx` (cmdk)         |
| ─ StatusNotifications                           | `src/components/common/Toast.tsx` (sonner)                 |
| ─ ThemeController.apply_persisted + retranslate | `src/stores/theme-store.ts` + `useTheme()`                 |

### 7.2 页面 + ViewModel 映射

| PySide6 Page+ViewModel                                            | React Page + Hook                                            | 行数约等   |
| ----------------------------------------------------------------- | ------------------------------------------------------------ | ---------- |
| `pages/home_page.py` + `viewmodels/home_viewmodel.py`             | `pages/HomePage.tsx` + `hooks/useHomeStats.ts`               | 480 → 220  |
| `pages/production_page.py` + `viewmodels/production_viewmodel.py` | `pages/ProductionPage.tsx` + `hooks/usePipeline.ts` + XState | 2200 → 720 |
| `pages/assets_page.py` + `viewmodels/assets_viewmodel.py`         | `pages/AssetsPage.tsx` + `hooks/useAssets.ts`                | 920 → 360  |
| `pages/settings_page.py` + `viewmodels/settings_viewmodel.py`     | `pages/SettingsPage.tsx` + `hooks/useSettings.ts`            | 1100 → 480 |
| `pages/update/update_page.py` + `updater/update_controller.py`    | `pages/UpdatePage.tsx` + `hooks/useUpdate.ts` + XState       | 540 → 280  |
| `help/panel.py` + `help/help_model.py`                            | `pages/HelpPage.tsx` + `components/help/*`                   | 380 → 180  |
| `viewmodels/dashboard_viewmodel.py`（无独立页面，挂在 Sidebar）   | `components/dashboard/*` + `hooks/useDashboardMetrics.ts`    | 362 → 200  |

> **总估算**：v2.4 UI 层约 8,500 行 Python → v3.0 前端约 5,000 行 TS/TSX（**-41%**），核心收益来自：1) Qt widgets 的样板代码消失；2) shadcn/ui 直接复用；3) ViewModel 的强类型 hook 替代 Signal/Property。

### 7.3 ProductionViewModel 5 步流水线详解

> 这是迁移难点中的难点，下一节专门给出 Rust 后端 + XState reducer + Web Worker 的三件套实现。

#### 7.3.1 Rust 后端（`scenefab-pipeline` crate）

```rust
// crates/scenefab-pipeline/src/state.rs
use serde::{Deserialize, Serialize};
use ts_rs::TS;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, TS)]
#[ts(export, export_to = "../../apps/desktop/src/ipc/types.gen.ts")]
pub enum StepStatus { Pending, Active, Done, Error }

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, TS)]
#[ts(export, export_to = "../../apps/desktop/src/ipc/types.gen.ts")]
pub enum PipelineState { Idle, Running, Done, Failed }

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, TS)]
#[ts(export, export_to = "../../apps/desktop/src/ipc/types.gen.ts")]
pub enum RunnerMode { Noop, Live }

#[derive(Debug, Clone, Serialize, Deserialize, TS)]
#[ts(export, export_to = "../../apps/desktop/src/ipc/types.gen.ts")]
pub struct PipelineSnapshot {
    pub state: PipelineState,
    pub current_step: i8,             // -1 表示无
    pub step_statuses: Vec<StepStatus>,
    pub runner_mode: RunnerMode,
    pub eta_seconds: Option<f64>,
    pub source_video: Option<String>,
    pub context: Option<String>,
    pub last_project_path: Option<String>,
}
```

```rust
// crates/scenefab-pipeline/src/service.rs
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio::sync::broadcast::{channel, Sender, Receiver};
use crate::state::*;

pub struct PipelineService {
    inner: Arc<RwLock<PipelineSnapshot>>,
    event_tx: Sender<PipelineEvent>,
    runner: Arc<dyn PipelineRunner>,
}

pub enum PipelineEvent {
    Snapshot(PipelineSnapshot),
    StepFinished { index: usize, took_seconds: f64 },
    StepFailed { index: usize, error: String },
    PipelineFinished(String),  // project path
    PipelineFailed(String),
}

impl PipelineService {
    pub async fn start_pipeline(
        &self,
        source_video: String,
        context: String,
    ) -> Result<(), PipelineError> {
        // 原子操作：检查状态 + 构造快照 + 调用 runner
        let mut snap = self.inner.write().await;
        if snap.state == PipelineState::Running {
            return Ok(());  // idempotent
        }
        snap.source_video = Some(source_video.clone());
        snap.context = Some(context.clone());
        snap.state = PipelineState::Running;
        drop(snap);

        let runner = self.runner.clone();
        let inner = self.inner.clone();
        let tx = self.event_tx.clone();
        tokio::spawn(async move {
            // 复用 Python 行为：runner 由前端传 source+ctx 而不是后端构造
            runner.run(inner, tx).await
        });
        Ok(())
    }

    pub fn subscribe(&self) -> Receiver<PipelineEvent> {
        self.event_tx.subscribe()
    }
}

#[async_trait::async_trait]
pub trait PipelineRunner: Send + Sync {
    async fn run(
        &self,
        state: Arc<RwLock<PipelineSnapshot>>,
        tx: Sender<PipelineEvent>,
    );
}

/// 默认 NoopRunner：5 步全部 active→done，不发外部请求
pub struct NoopRunner;
/// LiveRunner：调用 MonologueMaker / ScriptGenerator / TtsEngine / Exporter
pub struct LiveRunner { /* ... */ }
```

#### 7.3.2 前端 Pipeline XState 5 machine（`PipelineStateMachine.ts`）

```ts
// src/components/production/PipelineStateMachine.ts
import { setup, assign } from "xstate";

export interface PipelineContext {
  currentStep: number; // -1 表示无
  stepStatuses: ("pending" | "active" | "done" | "error")[];
  runnerMode: "noop" | "live";
  etaSeconds: number | null;
  sourceVideo: string | null;
  context: string | null;
  lastProjectPath: string | null;
}

export const pipelineMachine = setup({
  types: {
    context: {} as PipelineContext,
    events: {} as
      | { type: "START"; sourceVideo: string; context: string }
      | { type: "STEP_STARTED"; index: number }
      | { type: "STEP_FINISHED"; index: number; took: number }
      | { type: "STEP_FAILED"; index: number; error: string }
      | { type: "PIPELINE_FINISHED"; path: string }
      | { type: "PIPELINE_FAILED"; error: string }
      | { type: "SNAPSHOT"; snapshot: PipelineSnapshot }
      | { type: "RESET" },
  },
  actions: {
    applySnapshot: assign(({ event }) => {
      if (event.type !== "SNAPSHOT") return {};
      return {
        currentStep: event.snapshot.current_step,
        stepStatuses: event.snapshot.step_statuses,
        runnerMode: event.snapshot.runner_mode,
        etaSeconds: event.snapshot.eta_seconds,
        sourceVideo: event.snapshot.source_video,
        context: event.snapshot.context,
        lastProjectPath: event.snapshot.last_project_path,
      };
    }),
    setRunnerMode: assign({
      runnerMode: ({ event }) =>
        event.type === "START" && (window as any).SCENEFAB_HAS_KEYS
          ? "live"
          : "noop",
    }),
    reset: assign({
      currentStep: -1,
      stepStatuses: () => [
        "pending",
        "pending",
        "pending",
        "pending",
        "pending",
      ],
      etaSeconds: null,
      lastProjectPath: null,
    }),
  },
}).createMachine({
  id: "pipeline",
  initial: "idle",
  context: {
    currentStep: -1,
    stepStatuses: ["pending", "pending", "pending", "pending", "pending"],
    runnerMode: "noop",
    etaSeconds: null,
    sourceVideo: null,
    context: null,
    lastProjectPath: null,
  },
  states: {
    idle: {
      on: {
        START: { target: "running", actions: "setRunnerMode" },
        RESET: { actions: "reset" },
        SNAPSHOT: { actions: "applySnapshot" },
      },
    },
    running: {
      on: {
        STEP_STARTED: {
          actions: assign({ currentStep: ({ event }) => event.index }),
        },
        STEP_FINISHED: {
          actions: assign(({ context, event }) => ({
            stepStatuses: context.stepStatuses.map((s, i) =>
              i === event.index ? "done" : s,
            ),
          })),
        },
        STEP_FAILED: {
          target: "failed",
          actions: assign(({ context, event }) => ({
            stepStatuses: context.stepStatuses.map((s, i) =>
              i === event.index ? "error" : s,
            ),
          })),
        },
        PIPELINE_FINISHED: {
          target: "done",
          actions: assign({ lastProjectPath: ({ event }) => event.path }),
        },
        PIPELINE_FAILED: { target: "failed" },
        RESET: { target: "idle", actions: "reset" },
        SNAPSHOT: { actions: "applySnapshot" },
      },
    },
    done: {
      on: {
        RESET: { target: "idle", actions: "reset" },
        SNAPSHOT: { actions: "applySnapshot" },
      },
    },
    failed: {
      on: {
        RESET: { target: "idle", actions: "reset" },
        SNAPSHOT: { actions: "applySnapshot" },
      },
    },
  },
});
```

#### 7.3.3 Web Worker（`pipeline.worker.ts`）

> Vue/PySide6 的 `QThreadPool` 移到 Web 端对应是 Web Worker（如果步骤里有 CPU 密集操作）+ tokio 在 Rust 侧（如果调用 LLM）。本节前端侧用 Worker 做 ETA 滑动窗口预测。

```ts
// src/workers/pipeline.worker.ts
import { expose } from "comlink";
import { SlidingWindow } from "./sliding-window";

interface PipelineEstimate {
  etaSeconds: number | null;
  completedSamples: number[];
}

const SW = new SlidingWindow<number>(8); // 最多保留 8 步耗时

const api = {
  record(stepIndex: number, tookSeconds: number) {
    SW.push(tookSeconds);
  },
  predict(totalSteps: number, currentStep: number): number | null {
    if (SW.size() < 1) return null;
    const avg = SW.mean();
    const remaining = Math.max(0, totalSteps - currentStep - 1);
    return Math.round(avg * remaining);
  },
  reset() {
    SW.clear();
  },
};

expose(api);
```

主线程使用（`usePipeline.ts`）：

```ts
import * as Comlink from "comlink";
import { useEffect, useRef } from "react";

export function usePipelineETAPredictor() {
  const workerRef = useRef<Worker>();
  const proxyRef = useRef<Comlink.Remote<any>>();

  useEffect(() => {
    const w = new Worker(
      new URL("@workers/pipeline.worker.ts", import.meta.url),
      { type: "module" },
    );
    workerRef.current = w;
    proxyRef.current = Comlink.wrap(w);
    return () => w.terminate();
  }, []);

  return proxyRef.current!;
}
```

### 7.4 DashboardViewModel 系统指标

> Python 版订阅 `system.metric` event（1Hz 推送），内存用 60-sample 滑动窗口（5 分钟）。前端等价物是 `useTauriEvent` + Recharts。

```tsx
// src/hooks/useDashboardMetrics.ts
import { useTauriEvent } from "@hooks/useTauriCommand";
import { useEffect, useState } from "react";

export interface SystemMetric {
  cpuPercent: number;
  memoryPercent: number;
  memoryUsedMb: number;
  memoryTotalMb: number;
  diskPercent: number;
  processMemoryMb: number;
}

export function useDashboardMetrics() {
  const [latest, setLatest] = useState<SystemMetric | null>(null);
  const [history, setHistory] = useState<SystemMetric[]>([]);

  useTauriEvent<SystemMetric>("system.metric", (m) => {
    setLatest(m);
    setHistory((h) => [...h.slice(-59), m]); // 60-sample 滑动窗口
  });

  return { latest, history };
}
```

```tsx
// src/components/dashboard/MetricHistoryChart.tsx
import { Area, AreaChart, ResponsiveContainer, XAxis, YAxis } from "recharts";
import { useDashboardMetrics } from "@hooks/useDashboardMetrics";

export function MetricHistoryChart() {
  const { history } = useDashboardMetrics();
  return (
    <ResponsiveContainer width="100%" height={120}>
      <AreaChart
        data={history.map((m, i) => ({
          x: i,
          cpu: m.cpuPercent,
          mem: m.memoryPercent,
        }))}
      >
        <XAxis dataKey="x" />
        <YAxis domain={[0, 100]} />
        <Area
          type="monotone"
          dataKey="cpu"
          stroke="var(--color-primary)"
          fill="var(--color-primary-lightest)"
        />
        <Area
          type="monotone"
          dataKey="mem"
          stroke="var(--color-warning)"
          fill="var(--color-warning)"
          fillOpacity={0.4}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
```

### 7.5 HomePage（KPI 卡片）

```tsx
// src/pages/HomePage.tsx
import { useQuery } from "@tanstack/react-query";
import { assetsQueryOptions, recentProjectsQueryOptions } from "@ipc/queries";
import { useTranslation } from "react-i18next";
import { KpiCard } from "@components/home/KpiCard";
import { RecentProjectsList } from "@components/home/RecentProjectsList";

export function HomePage() {
  const { t } = useTranslation("home");
  const { data: assets } = useQuery(assetsQueryOptions());
  const { data: recent } = useQuery(recentProjectsQueryOptions());

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
      <KpiCard
        label={t("kpi.media")}
        value={assets?.mediaCount ?? 0}
        icon="film"
      />
      <KpiCard
        label={t("kpi.scene")}
        value={assets?.scriptCount ?? 0}
        icon="scissors"
      />
      <KpiCard
        label={t("kpi.export")}
        value={assets?.exportCount ?? 0}
        icon="download"
      />
      <KpiCard
        label={t("kpi.audio")}
        value={assets?.audioCount ?? 0}
        icon="mic"
      />
      <div className="col-span-full">
        <RecentProjectsList items={recent ?? []} />
      </div>
    </div>
  );
}
```

### 7.6 AssetsPage（拖拽 + 计数 + 最近项目）

```tsx
// src/pages/AssetsPage.tsx —— 对应 src/app/ui/main/pages/assets_page.py
import { useDropzone } from "react-dropzone";
import { useMutation } from "@tanstack/react-query";
import { ImportDropZone } from "@components/assets/ImportDropZone";
import { AssetSummaryCard } from "@components/assets/AssetSummaryCard";
import { MediaThumbnailGrid } from "@components/assets/MediaThumbnailGrid";
import { useAssets } from "@hooks/useAssets";
import { commands } from "@ipc/commands";

export function AssetsPage() {
  const { currentAssets, recentProjects, refresh } = useAssets();
  const importMutation = useMutation({
    mutationFn: (files: string[]) => commands.importMedia({ files }),
    onSuccess: () => refresh(),
  });

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (accepted) => importMutation.mutate(accepted.map((f) => f.path)),
    accept: { "video/*": [".mp4", ".mov", ".mkv"] },
  });

  return (
    <div className="flex flex-col gap-6">
      <ImportDropZone {...getRootProps()} active={isDragActive}>
        <input {...getInputProps()} />
        <span>拖拽视频文件到此处</span>
      </ImportDropZone>

      <AssetSummaryCard
        mediaCount={currentAssets.mediaCount}
        scriptCount={currentAssets.scriptCount}
        audioCount={currentAssets.audioCount}
        exportCount={currentAssets.exportCount}
      />

      <MediaThumbnailGrid />

      <RecentProjectsList items={recentProjects} />
    </div>
  );
}
```

### 7.7 Command Palette（Cmd+K，cmdk）

```tsx
// src/components/palette/CommandPalette.tsx
import { Command } from "cmdk";
import { useCommandRegistry } from "@lib/command-registry";
import { useUiStore } from "@stores/ui-store";
import { useNavigate } from "@tanstack/react-router";

export function CommandPalette() {
  const paletteOpen = useUiStore((s) => s.paletteOpen);
  const togglePalette = useUiStore((s) => s.togglePalette);
  const commands = useCommandRegistry();
  const navigate = useNavigate();

  useKeyboardShortcut("mod+k", togglePalette);

  return (
    <Command.Dialog open={paletteOpen} onOpenChange={togglePalette}>
      <Command.Input placeholder="输入命令或搜索…" />
      <Command.List>
        <Command.Empty>未找到匹配项</Command.Empty>
        {commands.map((group) => (
          <Command.Group key={group.id} heading={group.label}>
            {group.items.map((item) => (
              <Command.Item
                key={item.id}
                onSelect={() => {
                  item.action(navigate);
                  togglePalette();
                }}
              >
                <item.icon className="mr-2 h-4 w-4" />
                {item.label}
                <Command.Shortcut>{item.shortcut}</Command.Shortcut>
              </Command.Item>
            ))}
          </Command.Group>
        ))}
      </Command.List>
    </Command.Dialog>
  );
}
```

### 7.8 HelpPanel Sheet（替代 F1 dock）

```tsx
// src/components/help/HelpPanelSheet.tsx
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@ui/sheet";
import { useUiStore } from "@stores/ui-store";
import { useKeyboardShortcut } from "@hooks/useKeyboardShortcut";
import { useTranslation } from "react-i18next";

export function HelpPanelSheet() {
  const open = useUiStore((s) => s.helpSheetOpen);
  const toggle = useUiStore((s) => s.toggleHelp);
  const { t } = useTranslation("help");

  useKeyboardShortcut("F1", toggle);

  return (
    <Sheet open={open} onOpenChange={toggle}>
      <SheetContent side="right" className="w-[480px]">
        <SheetHeader>
          <SheetTitle>{t("title")}</SheetTitle>
        </SheetHeader>
        <HelpSearchInput />
        <HelpDocRenderer />
      </SheetContent>
    </Sheet>
  );
}
```

### 7.9 SettingsPage（11 个 LLM Provider 配置 + 性能 profile）

```tsx
// src/pages/SettingsPage.tsx
import { SettingsSection } from "@components/settings/SettingsSection";
import { LlmProviderSelector } from "@components/settings/LlmProviderSelector";
import { ThemeSwitcher } from "@components/settings/ThemeSwitcher";
import { LanguageSelector } from "@components/settings/LanguageSelector";
import { ProfilePicker } from "@components/settings/ProfilePicker";
import { ApiKeyInput } from "@components/settings/ApiKeyInput";
import { useTauriQuery } from "@hooks/useTauriCommand";
import { commands } from "@ipc/commands";
import type { Settings } from "@ipc/types.gen";

export function SettingsPage() {
  const { data: settings } = useTauriQuery<Settings>(
    ["settings"],
    "get_settings",
  );

  if (!settings) return <div>Loading…</div>;

  return (
    <div className="flex flex-col gap-8">
      <SettingsSection title="外观">
        <ThemeSwitcher value={settings.theme} />
        <LanguageSelector value={settings.locale} />
      </SettingsSection>

      <SettingsSection title="AI 配置">
        <LlmProviderSelector
          providers={[
            "Qwen",
            "Kimi",
            "GLM5",
            "Claude",
            "Gemini",
            "DeepSeek",
            "Doubao",
            "Hunyuan",
            "Local",
            "OpenAI",
            "Qwen3.7",
          ]}
          value={settings.ai.primaryProvider}
        />
        <ApiKeyInput
          label="OpenAI API Key"
          value={settings.ai.keys.openai ?? ""}
        />
        {/* ... 11 provider 一一对应 ... */}
      </SettingsSection>

      <SettingsSection title="性能">
        <ProfilePicker value={settings.performance.profile} />
      </SettingsSection>

      <SettingsSection title="诊断">
        <SettingsDiagnostics />
      </SettingsSection>
    </div>
  );
}
```

## 8. 系统托盘 + 全局快捷键

### 8.1 系统托盘（macOS menu bar / Windows tray）

```ts
// src/hooks/useSystemTray.ts
import { useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";

export function useSystemTray(actions: {
  onShow: () => void;
  onQuit: () => void;
  onToggleVisibility: () => void;
}) {
  useEffect(() => {
    // 后端建立托盘 + menu；前端订阅 menu item 点击事件
    invoke("setup_tray", {
      iconPath: "icons/icon.png",
      title: "SceneFab",
      menuItems: [
        { id: "show", label: "显示主窗口", shortcut: "CmdOrCtrl+Shift+S" },
        { id: "production", label: "打开生产页", shortcut: "CmdOrCtrl+P" },
        { id: "assets", label: "打开资源页", shortcut: "CmdOrCtrl+A" },
        { id: "quit", label: "退出", shortcut: "CmdOrCtrl+Q" },
      ],
    });

    const unlistenPromises = [
      listen("tray:menu-clicked", (e) => {
        switch (e.payload.id) {
          case "show":
            actions.onShow();
            break;
          case "quit":
            actions.onQuit();
            break;
          default:
            actions.onToggleVisibility();
            break;
        }
      }),
    ];

    return () => {
      Promise.all(unlistenPromises).then((arr) => arr.forEach((u) => u()));
    };
  }, [actions]);
}
```

### 8.2 全局快捷键注册

| 快捷键             | 动作                   | 实现位置                            |
| ------------------ | ---------------------- | ----------------------------------- |
| `Cmd/Ctrl+K`       | 打开命令面板           | `useKeyboardShortcut`               |
| `Cmd/Ctrl+,`       | 打开设置               | `useKeyboardShortcut`               |
| `Cmd/Ctrl+1..6`    | 切换页面（路由）       | TanStack Router `<Outlet>` + keymap |
| `Cmd/Ctrl+N`       | 新建项目               | `commands.newProject()`             |
| `Cmd/Ctrl+O`       | 打开项目               | `commands.openProjectDialog()`      |
| `Cmd/Ctrl+S`       | 保存项目               | `commands.saveProject()`            |
| `Cmd/Ctrl+Shift+R` | 开始/重置流水线        | `usePipelineController().start()`   |
| `F1`               | 打开/关闭帮助 Sheet    | `useUiStore.toggleHelp()`           |
| `Cmd/Ctrl+Q`       | 退出（macOS 二次确认） | `tauri-plugin-confirmation`         |

### 8.3 单实例 + 窗口状态

```ts
// src/hooks/useWindowState.ts
import {
  getCurrentWindow,
  LogicalSize,
  LogicalPosition,
} from "@tauri-apps/api/window";

export function useWindowState() {
  useEffect(() => {
    const win = getCurrentWindow();
    // 还原上次窗口大小
    (async () => {
      const savedSize = await invoke<{ width: number; height: number } | null>(
        "load_window_state",
      );
      if (savedSize) {
        await win.setSize(new LogicalSize(savedSize.width, savedSize.height));
      }
    })();

    // 保存窗口状态
    const save = async () => {
      const size = await win.innerSize();
      const pos = await win.outerPosition();
      await invoke("save_window_state", {
        state: { width: size.width, height: size.height, x: pos.x, y: pos.y },
      });
    };
    const unlisten = win.onCloseRequested(save);
    return () => unlisten.then((u) => u());
  }, []);
}
```

## 9. 测试策略

### 9.1 三层测试金字塔

| 层   | 工具            | 范围                                            | 目标覆盖率 |
| ---- | --------------- | ----------------------------------------------- | ---------- |
| 单元 | Vitest          | hooks / store / utils / xstate machine / i18n   | **80%**    |
| 组件 | Testing Library | 单组件交互 + axe a11y                           | 70%        |
| E2E  | Playwright      | 关键流程（打开项目 → 启动流水线 → 导出 → 更新） | 4 条冒烟   |

### 9.2 vitest.config.ts

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      // ...
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov", "json"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.d.ts",
        "src/**/index.ts",
        "src/components/ui/**", // shadcn/ui 不需测试
        "src/workers/**",
      ],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 75,
        statements: 80,
      },
    },
  },
});
```

### 9.3 tauri-mock（测试 IPC）

```ts
// tests/fixtures/tauri-mock.ts
import { vi } from "vitest";
import { mockIPC } from "@tauri-apps/api/mocks";

export function setupTauriMock(handlers: Record<string, (args: any) => any>) {
  mockIPC((cmd, args) => {
    const handler = handlers[cmd];
    if (!handler) throw new Error(`No mock handler for ${cmd}`);
    return handler(args);
  });
}
```

### 9.4 一个完整测试范例

```tsx
// tests/unit/hooks/usePipeline.test.ts
import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { setupTauriMock } from "../fixtures/tauri-mock";
import { usePipelineController } from "@hooks/usePipeline";

describe("usePipeline", () => {
  beforeEach(() => {
    setupTauriMock({
      start_pipeline: ({ sourceVideo, context }) => ({
        state: "running",
        currentStep: 0,
        step_statuses: ["active", "pending", "pending", "pending", "pending"],
        runner_mode: "noop",
        eta_seconds: null,
        source_video: sourceVideo,
        context,
      }),
      pipeline_subscribe: () => null,
    });
  });

  it("starts pipeline and transitions to running", async () => {
    const { result } = renderHook(() => usePipelineController());
    await act(async () => {
      await result.current.start("/tmp/video.mp4", "调性：女性向");
    });
    expect(result.current.state).toBe("running");
    expect(result.current.currentStep).toBe(0);
  });
});
```

### 9.5 Playwright E2E 配置

```ts
// playwright.config.ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  retries: { process: 2, inContainer: 0 },
  reporter: [["list"], ["json", { outputFile: "playwright-report.json" }]],
  use: {
    baseURL: "http://127.0.0.1:1420",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    // Tauri dev server
    command: "pnpm tauri dev",
    port: 1420,
    reuseExistingServer: true,
    timeout: 120_000,
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
```

### 9.6 关键 E2E 场景

```ts
// tests/e2e/scenarios/smoke.spec.ts
import { test, expect } from "@playwright/test";

test("首次启动 → 新建项目 → 启动流水线", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "SceneFab" })).toBeVisible();
  await page.getByRole("button", { name: "新建项目" }).click();
  await page.fill('input[name="projectName"]', "test-project");
  await page.getByRole("button", { name: "创建" }).click();
  await expect(page).toHaveURL(/\/production/);
  await page.getByRole("button", { name: "开始" }).click();
  await expect(page.getByTestId("step-0")).toHaveAttribute(
    "data-status",
    "active",
  );
});

test("暗色主题切换", async ({ page }) => {
  await page.goto("/settings");
  await page.getByRole("combobox", { name: "主题" }).click();
  await page.getByRole("option", { name: "暗色" }).click();
  const theme = await page.evaluate(
    () => document.documentElement.dataset.theme,
  );
  expect(theme).toBe("dark");
});

test("命令面板导航", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Control+K");
  await page.fill("input[cmdk-input]", "settings");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/settings/);
});
```

### 9.7 视觉回归（Playwright screenshot diff）

```ts
// tests/e2e/visual/screenshots.spec.ts
import { test, expect } from "@playwright/test";

test.use({ viewport: { width: 1280, height: 800 } });

const pages = ["/", "/production", "/assets", "/settings", "/updates", "/help"];
for (const path of pages) {
  test(`visual: ${path}`, async ({ page }) => {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveScreenshot(
      `pages${path === "/" ? "/home" : path}.png`,
      {
        fullPage: true,
        maxDiffPixelRatio: 0.01,
      },
    );
  });
}
```

## 10. 性能优化清单

### 10.1 Bundle 体积预算

| Chunk            | 预算 (gzipped) | 实测 |
| ---------------- | -------------- | ---- |
| `index` (主入口) | ≤ 200 KB       | TBD  |
| `react-vendor`   | ≤ 60 KB        | TBD  |
| `tanstack`       | ≤ 80 KB        | TBD  |
| `i18n`           | ≤ 30 KB        | TBD  |
| 页面懒加载包     | 每页 ≤ 100 KB  | TBD  |
| **总计首屏**     | **≤ 500 KB**   | TBD  |

### 10.2 启动时间预算

```
冷启动  Tauri boot  + Rust 启动  + WebView 首屏 ready
目标    ≤ 500 ms (P95)  vs Python v2.4 ~ 1500ms
```

优化手段：

- Tauri 配置 `app.deepLinkProtocols = false`（v3 关闭）
- `withGlobalTauri = false`，引入 `@tauri-apps/api/core` 的 `invoke` 而非全局
- 主入口静态分割：先渲染 `<AppShell>` 占位（Splash），再异步挂 `<Outlet>`
- Rust 端并行启动：在 `setup()` 中 `tokio::spawn` 注册 service

### 10.3 运行时性能

| 场景                    | 目标 (P95) | 手段                          |
| ----------------------- | ---------- | ----------------------------- |
| 路由切换                | < 100ms    | TanStack Router 预加载 + lazy |
| 命令面板打开            | < 50ms     | cmdk 内置 virtual list        |
| 主题切换                | < 80ms     | CSS variables 切换            |
| 5 步流水线状态更新      | < 16ms     | XState 同步 + Web Worker ETA  |
| 系统指标 60-sample 图表 | < 8ms      | Recharts + 60 数据量极小      |
| 拖拽 100 个 200MB 视频  | 不卡顿     | 仅上传路径（不读 metadata）   |
| 设置改动保存            | < 500ms    | TanStack Query Mutation       |

### 10.4 内存目标

```text
冷启动 + 空载        ≤ 90MB (v2.4 ~ 280MB)
打开项目            ≤ 150MB
流水线运行 + Worker ≤ 220MB
4K 视频预览         ≤ 700MB（不缓存原始帧，仅缓存缩略图）
```

## 11. 验收标准 (UI 维度)

| 项               | 验收                                                            |
| ---------------- | --------------------------------------------------------------- |
| **bundle 大小**  | 主入口 ≤ 200KB gzipped, 总和 ≤ 500KB                            |
| **冷启动 P95**   | ≤ 500ms (macOS M1, Windows i7-11800H)                           |
| **路由切换 P95** | ≤ 100ms                                                         |
| **主题切换 P95** | ≤ 80ms                                                          |
| **类型完整性**   | `tsc --noEmit` 必须 0 错误, 严格模式开启                        |
| **组件库合规**   | 禁止内联 styles 颜色字面量 + 禁止用 antd / MUI 等替代 shadcn/ui |
| **i18n 完整度**  | 488 zh-CN + 474 en-US key 全数导入, 单元测试覆盖 100%           |
| **设计令牌迁移** | 199 个 PySide6 token → CSS 变量, 全 token 文件无 hard-code      |
| **可访问性**     | axe-core: 6 个 page 0 严重/中等问题                             |
| **E2E 通过率**   | Playwright 4 条冒烟全部通过                                     |
| **视觉回归**     | Playwright screenshot diff ≤ 1% 像素差异                        |

---

> **结尾**：下一节进入 **07-tauri-integration.md**：Tauri 多进程模型 + 35 个 Command 的具体签名 + Capability ACL 设计 + Event 总线契约 + 单实例/自动启动/系统托盘集成 + 安全模型（密钥/路径白名单/CSP）。
