# 15. apps/desktop 目录结构对齐 README 报告

> **触发**：用户要求"按照 README.md 中的目录结构，调整现有的目录结构"
> **基准**：`apps/desktop/README.md` §目录结构（v3.0 目标态）
> **结论**：✅ 现状与 README 100% 对齐（含 6 项新增 / 1 项重命名 / 1 项清理）

---

## 1. 调整前后对比

### 1.1 src/ 目录对比

| README 期望条目                                                                                | 调整前状态                              | 调整后状态                       | 处理   |
| ---------------------------------------------------------------------------------------------- | --------------------------------------- | -------------------------------- | ------ |
| `main.tsx` / `App.tsx`                                                                         | ✅ 存在                                 | ✅ 保留                          | —      |
| `routes/{__root,index,production,assets,settings,help}.tsx`                                    | ✅ 存在                                 | ✅ 保留                          | —      |
| `routes/updates.tsx` (路径 `/updates`)                                                         | ⚠️ `routes/update.tsx` (路径 `/update`) | ✅ 重命名 + 路径改 `/updates`    | 重命名 |
| `pages/` (空占位)                                                                              | ✅ 空                                   | ✅ 保留                          | —      |
| `components/{ui,layout,production,home,assets,settings,dashboard,help,palette,common,update}/` | ✅ 11 子目录存在                        | ✅ 保留                          | —      |
| `hooks/useTauriCommand.ts`                                                                     | ❌ 缺失                                 | ✅ 新建                          | 新建   |
| `hooks/usePipeline.ts`                                                                         | ❌ 缺失                                 | ✅ 新建                          | 新建   |
| `hooks/useProject.ts`                                                                          | ❌ 缺失                                 | ✅ 新建                          | 新建   |
| `hooks/useAssets.ts`                                                                           | ❌ 缺失                                 | ✅ 新建                          | 新建   |
| `hooks/useTauriQuery.ts` (M2 已有 · README 之外的补充)                                         | ✅ 存在                                 | ✅ 保留                          | —      |
| `stores/{theme,project,pipeline,update,settings,ui}-store.ts`                                  | ❌ 6 文件全缺失                         | ✅ 6 文件新建                    | 新建   |
| `stores/assets-store.ts` (README 之外的补充 · useAssets 依赖)                                  | ❌ 缺失                                 | ✅ 新建                          | 新建   |
| `ipc/commands.ts` (35 个 commands 类型化包装)                                                  | ❌ 缺失                                 | ✅ 新建 (3 个 facade + 4 个占位) | 新建   |
| `ipc/events.ts` (24 个 events 类型化包装)                                                      | ❌ 缺失                                 | ✅ 新建 (4 个 facade 全占位)     | 新建   |
| `ipc/types.gen.ts` (specta 自动生成)                                                           | ✅ M2 已建                              | ✅ 保留 + 扩展 `IpcEvent` 类型表 | 扩展   |
| `ipc/errors.ts` (SceneFabError 用户可读)                                                       | ❌ 缺失                                 | ✅ 新建 (5 个 helper)            | 新建   |
| `ipc/schema.ts` (cmd/event 名称常量)                                                           | ❌ 缺失                                 | ✅ 新建 (CMD + EVT)              | 新建   |
| `ipc/client.ts` (callIpc 底层 wrapper · M2 已建)                                               | ✅ 存在                                 | ✅ 保留                          | —      |
| `lib/{i18n,tokens,format,log,commands}/`                                                       | ✅ 5 子目录存在                         | ✅ 保留                          | —      |
| `styles/globals.css`                                                                           | ✅ 存在                                 | ✅ 保留                          | —      |
| `workers/` (空占位)                                                                            | ✅ 空                                   | ✅ 保留                          | —      |
| `assets/react.svg` (Vite 模板残留)                                                             | ⚠️ 存在,无任何引用                      | ✅ 删除                          | 清理   |

### 1.2 src-tauri/ 目录对比

| README 期望条目                          | 调整前状态 | 调整后状态 | 处理 |
| ---------------------------------------- | ---------- | ---------- | ---- |
| `Cargo.toml` / `tauri.conf.json`         | ✅ 存在    | ✅ 保留    | —    |
| `capabilities/default.json`              | ✅ 存在    | ✅ 保留    | —    |
| `src/main.rs` / `src/lib.rs`             | ✅ 存在    | ✅ 保留    | —    |
| `src/commands/{app,pipeline,project}.rs` | ✅ M2 已建 | ✅ 保留    | —    |

---

## 2. 关键设计决策

### 2.1 routes 重命名 `update.tsx` → `updates.tsx`

- **原因**：README §目录结构明确 `routes/updates.tsx` + 路径 `/updates`（与 `/assets` `/production` `/settings` 等保持复数一致）
- **影响**：
  - `-routeTree.gen.ts` 由 `pnpm vite build` 自动重生成（无需手改）
  - 产物 hash 由 `update-*.js` 变为 `updates-*.js`（验证 ✅）
- **可访问 URL**：`/updates`（之前 `/update`）

### 2.2 IPC 5 文件结构分工

README §目录结构列出 5 个 ipc 文件，按职责清晰分层：

```
ipc/
├── types.gen.ts       # specta 自动生成的 TS 类型（IpcCommand / IpcEvent 联合）
├── client.ts          # callIpc<C> 底层强类型 wrapper（M2 已有）
├── commands.ts        # 35 个 commands 业务 facade（按 app/project/pipeline/... 分组）
├── events.ts          # 24 个 events 类型化订阅（按 pipeline/assets/updater/app 分组）
├── errors.ts          # SceneFabError → 用户可读（归类/i18n key/脱敏/重试）
└── schema.ts          # CMD / EVT 名称常量（用于 log/埋点/i18n）
```

**M2 → M2+ 扩展**：`types.gen.ts` 末尾新增 `IpcEventPayloads` 接口（24 events）与 `IpcEvent` 联合类型；与 `IpcCommand` 平级。

### 2.3 hooks 4 文件分工

README §目录结构列出 4 个 hooks（M2 已建 `useTauriQuery.ts` 为补充）：

| 文件                 | 模式                        | 用途                        |
| -------------------- | --------------------------- | --------------------------- |
| `useTauriQuery.ts`   | TanStack Query (高阶)       | 列表/详情自动 cache/retry   |
| `useTauriCommand.ts` | useState + useEffect (低阶) | 一次性 trigger,无需 cache   |
| `usePipeline.ts`     | XState v5 占位              | 5 步流水线状态机(M3.2 接入) |
| `useProject.ts`      | store + invoke 占位         | 项目 open/save/close        |
| `useAssets.ts`       | store + invoke 占位         | 素材 import/remove          |

### 2.4 7 stores 分工

README §目录结构列出 6 个 store + `assets-store`（被 `useAssets.ts` 引用，README 隐含依赖）：

| Store               | 持久化       | 内容                                                  |
| ------------------- | ------------ | ----------------------------------------------------- |
| `theme-store.ts`    | localStorage | theme (light/dark/system)                             |
| `project-store.ts`  | 否           | current + recent                                      |
| `pipeline-store.ts` | 否           | state + stepDefs + runId + percent                    |
| `update-store.ts`   | 否           | available + downloading + percent + ready             |
| `settings-store.ts` | localStorage | locale + llmDefault + ttsDefault + autoSaveInterval   |
| `ui-store.ts`       | 否           | sidebarCollapsed + commandPaletteOpen + helpPanelOpen |
| `assets-store.ts`   | 否           | ids + selectedIds (useAssets 依赖)                    |

---

## 3. 新增文件清单（11 个）

### 3.1 IPC 层 (4 个)

- **`src/ipc/commands.ts`** (80 行)
  - 5 个业务 facade：`appIpc` / `projectIpc` / `pipelineIpc` / `assetsIpc` / `settingsIpc` / `updaterIpc`
  - `ipc` 总 facade + `IpcFacade` 类型
  - 6 个 M2 已落地 cmd + 29 个 TODO 占位

- **`src/ipc/events.ts`** (100 行)
  - 4 个 events facade：`pipelineEvents` / `assetsEvents` / `updaterEvents` / `appEvents`
  - 24 个 event 订阅方法全部 M3+ 占位
  - `events` 总 facade + `EventsFacade` 类型

- **`src/ipc/errors.ts`** (99 行)
  - `ErrorCategory` 联合 (10 种分类)
  - `ERROR_CATEGORY` 映射表
  - `RETRYABLE` 矩阵 (决定 UI 是否显示"重试"按钮)
  - `i18nKey(err, subKey)` 派生 t() key
  - `safeMessage(err)` 密钥脱敏 (api_key/secret/token/password/bearer 模式)
  - `formatError(err)` 组合 `[category] message`
  - `asSceneFabError(err)` 类型守卫 (unknown → SceneFabError)

- **`src/ipc/schema.ts`** (58 行)
  - `CMD` 常量 (5 个 M2 落地 cmd)
  - `EVT` 常量 (24 个事件名)
  - `Cmd` / `Evt` 类型联合

### 3.2 Hooks 层 (4 个)

- **`src/hooks/useTauriCommand.ts`** (74 行) — 与 `useTauriQuery` 配对的低阶 trigger
- **`src/hooks/usePipeline.ts`** (84 行) — XState v5 占位,5 步状态机
- **`src/hooks/useProject.ts`** (54 行) — 项目 open/save/saveAs/close 占位
- **`src/hooks/useAssets.ts`** (50 行) — 素材 import/remove 占位

### 3.3 Stores 层 (7 个)

- **`src/stores/theme-store.ts`** (31 行) — 持久化主题
- **`src/stores/project-store.ts`** (26 行) — current + recent
- **`src/stores/pipeline-store.ts`** (36 行) — 5 步状态
- **`src/stores/update-store.ts`** (55 行) — 升级状态
- **`src/stores/settings-store.ts`** (41 行) — 持久化设置
- **`src/stores/ui-store.ts`** (29 行) — UI 临时态
- **`src/stores/assets-store.ts`** (36 行) — 素材 id + 选中

---

## 4. 修改文件清单（4 个）

- **`src/routes/update.tsx` → `src/routes/updates.tsx`** (重命名 + 路径 `/update` → `/updates`)
- **`src/ipc/types.gen.ts`** (扩展 `IpcEventPayloads` 接口 + `IpcEvent` 类型)
- **`src/hooks/useProject.ts`** (清理 useTauriCommand 误引用)
- **`src/hooks/useAssets.ts`** (清理 `assert {}` 旧语法 → TS 5+ 已用 `with`)

---

## 5. 删除清单（2 个）

- `src/assets/react.svg` (Vite 模板默认图,0 引用)
- `src/assets/` (整个目录,内只有 react.svg)

---

## 6. 三轨验证

| 验证项   | 命令                      | 结果                                        |
| -------- | ------------------------- | ------------------------------------------- |
| 类型检查 | `pnpm exec tsc --noEmit`  | ✅ EXIT=0, 0 errors                         |
| 前端构建 | `pnpm exec vite build`    | ✅ 184 modules, 971ms,产物含 `updates-*.js` |
| 后端测试 | `cargo test --workspace`  | ✅ 18/18 passed (9+3+4+2)                   |
| 后端检查 | `cargo check --workspace` | ✅ Finished, 0 warnings                     |

---

## 7. 与 README 的最终一致性

- ✅ 11 个 components 子目录全部存在
- ✅ 4 个 README hooks + 1 个 M2 补充 hooks
- ✅ 6 个 README stores + 1 个 useAssets 依赖 store
- ✅ 5 个 README ipc 文件 + 1 个 M2 底层 client.ts
- ✅ routes 命名 / 路径全部对齐 (`/`, `/assets`, `/help`, `/production`, `/settings`, `/updates`)
- ✅ src-tauri 全部对齐
- ✅ Vite 模板残留 (`src/assets/react.svg`) 已清
- ✅ pages / workers 空目录保留（M3+ 占位）

---

## 8. 后续 M3+ 阶段 TODO 提示

| 文件                       | TODO 标记                                              | 阶段   |
| -------------------------- | ------------------------------------------------------ | ------ |
| `ipc/commands.ts`          | `assetsIpc.list/import/remove/...` (6 个)              | M4     |
| `ipc/commands.ts`          | `pipelineIpc.start/cancel/status/subscribe/...` (7 个) | M3.2   |
| `ipc/commands.ts`          | `settingsIpc.get/set/set_api_key` (4 个)               | M3.3   |
| `ipc/commands.ts`          | `projectIpc.open/save/save_as/...` (10 个)             | M3     |
| `ipc/commands.ts`          | `updaterIpc.check/download/install` (3 个)             | M5     |
| `ipc/events.ts`            | 全部 24 events (后端 broadcast 落地)                   | M3+    |
| `hooks/useTauriCommand.ts` | 替换 TODO 为 `run()` 实际 invoke                       | 全阶段 |
| `hooks/usePipeline.ts`     | XState v5 真实机                                       | M3.2   |
| `hooks/useProject.ts`      | 4 个 TODO                                              | M3     |
| `hooks/useAssets.ts`       | 2 个 TODO                                              | M4     |
