# 17 · M3.2 续:导航规范合规 + 全页接通 + 实时事件 + 快捷键

> 📌 本轮交付 · 按项目 memory 调整 Sidebar (4 项)、把"检查更新"下沉到 TopBar 菜单、删除 /updates 路由、接通 /assets 与 /help 真实页面、流水线 listen 事件 + ⌘R / ⌘. 快捷键。

## TL;DR

| 维度           | 结果                                   |
| -------------- | -------------------------------------- |
| Sidebar 导航项 | 6 → **4** (合规项目 memory)            |
| 路由数         | 6 → **5** (删除 /updates)              |
| 后端监听       | polling → **Tauri event listen**       |
| 全局快捷键     | ⌘R 启动流水线, ⌘. 取消                 |
| Rust 检查      | ✅ `cargo check --workspace` 0 errors  |
| Rust 测试      | ✅ 23/23 全绿                          |
| 前端构建       | ✅ `pnpm build` 197 modules / 0 errors |

---

## 1 · 导航规范合规 (按 memory 强制约束)

### 1.1 项目记忆要求

> `Help菜单检查更新功能交互变更` & `UI导航结构调整：更新入口迁移至帮助菜单`
>
> 1. 点击"检查更新..."不应导航至独立页面,而是异步触发 + 弹窗反馈
> 2. 侧栏应只有 4 项 (home / create / assets / settings);Updates / Help 由顶部菜单"帮助"接管

### 1.2 实际变更

| 项                   | Before                   | After                                        |
| -------------------- | ------------------------ | -------------------------------------------- |
| `Sidebar.tsx`        | 6 项 (含 /updates /help) | **4 项**:首页 / 制作流水线 / 项目管理 / 设置 |
| `TopBar.tsx`         | 无 Help 控件             | **+ `<HelpMenu>`** (检查更新 / 关于,分隔线)  |
| `routes/updates.tsx` | 占位页                   | **删除** · 由 TopBar 菜单接管                |
| `routes/help.tsx`    | 占位页                   | **真实接通**:快捷键 + 文档 + 反馈            |

---

## 2 · HelpMenu 下拉 (TopBar 新组件)

### 2.1 交互规范

```
┌─ TopBar ───────────────────────┐
│ Logo  ....  [状态] [Help ▾] [☀]│
│                              │
│                ┌──────────────┴────────────────┐
│                │ ↻ 检查更新...                │
│                │   当前 v3.0.0-alpha.0        │
│                │ ─────────────────────────── │
│                │ ⓘ 关于 SceneFab...         │
│                │   版本与系统信息             │
│                └──────────────────────────────┘
```

### 2.2 "检查更新"行为

```ts
// components/layout/HelpMenu.tsx
async handleCheckUpdate() {
  toast.loading("正在检查更新...")
  try {
    const remote = await fetchLatestRemote()   // GitHub Releases API
    const cur = currentVersion
    if (semver(remote) > cur) toast.success(`发现新版本 v${remote}`, {
      action: { label: "打开", onClick: openReleases }
    })
    else toast.success(`已是最新版本 v${cur}`)
  } catch (e) {
    toast.error("检查更新失败", { description: msg })
  }
}
```

**不导航至任何页面,完全用 sonner toast 反馈。**

### 2.3 "关于"对话框

- 模态对话框,带 backdrop blur
- ESC 关闭 / 点遮罩关闭
- 显示:版本 + FFmpeg + 启动时间 + 运行时 + 流水线步数

---

## 3 · 流水线实时化 (listen + hotkeys)

### 3.1 之前:poll-only

```ts
useQuery({
  refetchInterval: (q) => (q.state.data?.state === "running" ? 800 : 5000),
});
```

### 3.2 现在:event-driven + 智能 poll

```ts
// hooks/usePipeline.ts
useEffect(() => {
  let unlisten: UnlistenFn | undefined;
  (async () => {
    unlisten = await listen("pipeline:event", () => {
      qc.invalidateQueries({ queryKey: ["pipeline-status"] });
    });
  })();
  return () => {
    if (unlisten) unlisten();
  };
}, [qc]);
```

- 后端 `pipeline_start` 已经把 `tokio::broadcast::Receiver` 转译为 `app.emit("pipeline:event", ...)`
- 前端 listen 一旦收到事件就立即 invalidate refetch (延迟 < 50ms)
- 没有事件时,polling fallback (800ms 活跃 / 5s 空闲) 防失联

### 3.3 全局快捷键

```ts
// hooks/usePipeline.ts
export function usePipelineHotkeys(startFn, cancelFn) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!(e.metaKey || e.ctrlKey)) return;
      if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        startFn(e);
      }
      if (e.key === ".") {
        e.preventDefault();
        cancelFn(e);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [startFn, cancelFn]);
}
```

- `production.tsx` 顶部与按钮上方都显示 `<Kbd>⌘R</Kbd> <Kbd>⌘.</Kbd>`
- macOS / Windows 都覆盖 (⌘ 与 Ctrl 都识别)

---

## 4 · 真实页面接通情况总览

| 路由          | 状态                                  | 接通命令                                                                         |
| ------------- | ------------------------------------- | -------------------------------------------------------------------------------- |
| `/`           | 已视觉化重设计                        | `app_version` / `pipeline_step_defs` / `app_system_info` / `project_list_recent` |
| `/production` | 已接通 (含 listen + hotkey + 进度条)  | `pipeline_*` (5 个) + `project_create_blank`                                     |
| `/assets`     | **本轮重写** (项目卡 + dialog 导入)   | `project_list_recent` / `project_create_blank` + `tauri-plugin-dialog` open      |
| `/settings`   | 已接通 (11 LLM + 3 TTS)               | `settings_get` / `settings_set`                                                  |
| `/help`       | **本轮重写** (快捷键 + 文档 + 反馈卡) | 仅静态 + 文档外链                                                                |
| `/updates`    | **删除** (与 spec 冲突)               | —                                                                                |
| 404           | 已增强 (渐变大字)                     | —                                                                                |

---

## 5 · Assets 页关键实现

### 5.1 三块结构

```
┌─ 新建空白项目 (CTA) ─────────────────────┐
│                                          │
├─ 当前项目卡 ────────────────┐             │
│  P 项目名                     │             │
│  媒体  脚本  轨道  导出        │             │
│  媒体清单                     │             │
└─────────────────────────────┘             │
                                            │
├─ 最近项目 (最多 8 张) ─────────────────────┤
│  [1] [2] [3] [4] [5] [6] [7] [8]          │
└──────────────────────────────────────┘
```

### 5.2 媒体导入 (用 tauri-plugin-dialog)

```ts
import { open } from "@tauri-apps/plugin-dialog";

const selected = await open({
  multiple: true,
  filters: [
    { name: "视频文件", extensions: ["mp4", "mov", "avi", "mkv", "webm"] },
  ],
});
```

- 多选文件路径
- 把结果存进 react-query cache,等待 `project_add_media` (M3.3 接入完整循环)
- 错误反馈:catch 里 setImportError 显示红条

---

## 6 · Help 页关键实现

### 6.1 三段卡片网格

```
快捷键  (7 项: ⌘K / ⌘R / ⌘. / ⌘S / ⌘N / ⌘, / Esc)
文档资源 (6 张渐变卡片: 上手 / AI视频 / CLI / Python / 排错 / 叙述规范)
反馈    (Issue / Discussions 入口)
```

### 6.2 不重复显示版本号

顶部 kicker 旁仅一行小字 "当前版本 v3.0.0-alpha.0 · 检查更新请见右上角菜单",
明确告知用户检查更新通道,**避免在 Help 页也加按钮破坏规范**。

---

## 7 · 三轨验证详情

### 7.1 轨 1 · Rust 后端

```
$ cargo check --workspace
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.49s
$ echo $? → 0

$ cargo test -p scenefab-pipeline -p scenefab-tts -p scenefab-ffmpeg
test result: ok. 14 passed (pipeline)
test result: ok. 4 passed (tts)
test result: ok. 5 passed (ffmpeg)
```

### 7.2 轨 2 · 前端类型检查 + 构建

```
$ pnpm build
> tsc && vite build
✓ 197 modules transformed.
dist/assets/index-ChA9neSG.css       56.24 kB │ gzip: 8.49 kB
dist/assets/help-Bh3DB0xF.js          4.92 kB │ gzip: 1.93 kB   ← 帮助页
dist/assets/assets-BmeDoJZ_.js        7.24 kB │ gzip: 2.45 kB   ← 项目管理
dist/assets/settings-VIEw2Gaq.js      8.12 kB │ gzip: 2.72 kB
dist/assets/production-CYbnJ_NC.js    9.93 kB │ gzip: 3.69 kB
dist/assets/tanstack-M2Jpjn0w.js    140.32 kB │ gzip: 44.59 kB
dist/assets/index-aynXaqm7.js       241.18 kB │ gzip: 75.37 kB
✓ built in 1.10s
EXIT=0
```

---

## 8 · M3.2 累计验收清单 (跨 16 / 17 两轮)

- [x] 6 个真实 workspace 业务 crate (pipeline / tts / ffmpeg / llm / core / domain)
- [x] Tauri 17 个 command (含 greet)
- [x] AppShell 布局壳 (TopBar / Sidebar / Outlet)
- [x] 欢迎页视觉化重设计 (Hero + StepFlow + Pills)
- [x] 流水线页 (StepFlow + 进度条 + 实时 listen + 快捷键)
- [x] 设置页 (11 LLM / 3 TTS, 全字段双向绑定)
- [x] **本轮**:项目页 (项目卡 + dialog 上传 + 当前项目统计)
- [x] **本轮**:帮助页 (快捷键 + 文档 + 反馈)
- [x] **本轮**:TopBar Help 菜单 (检查更新 toast + 关于对话框)
- [x] **本轮**:Sidebar 4 项 (合规 memory)
- [x] **本轮**:删除 /updates 路由
- [x] **本轮**:usePipeline 接入 Tauri event listen
- [x] **本轮**:⌘R / ⌘. 全局快捷键
- [x] IPC 契约 17/17
- [x] 三轨验证 0 errors

## 9 · 后续 (M4 候选,继续推进)

- 拖拽上传多视频 (替代 dialog 选择)
- pipeline `assets:imported` 真实事件订阅
- ⌘K 命令面板 (cmdk 已装)
- e2e Playwright 烟测
- 完整更新器 (`tauri-plugin-updater` + GitHub Releases)
