# 更新日志

本文件记录 Vynaro 所有重要变更。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [语义化版本控制](https://semver.org/lang/zh-CN/)。

---

## [Unreleased]

## [2.5.0] - 2026-08-05

> Vynaro v2.5.0 — **Rust + Tauri 2 + React 主线正式确立**。Python v2.4 主线退役冻结。

### 🚀 Features (Rust 13 + Tauri 2 主线)

- **feat(rust): Rust workspace 13 个领域 crate**（commit `4fc4cd3`）
  - `vynaro-core` · `vynaro-domain` · `vynaro-ffmpeg` · `vynaro-llm` (11 Provider)
  - `vynaro-tts` (3 引擎) · `vynaro-video` · `vynaro-export`
  - `vynaro-pipeline` (5 步状态机 + DAG) · `vynaro-plugin` (WASM 运行时)
  - `vynaro-update` · `vynaro-help` · `vynaro-i18n` · `vynaro-assets`
  - workspace root `version = 2.5.0`，所有 14 个 scenefab package 共享
    (本版本后又移除 vynaro-cli → 现为 13 领域 crate + 1 Tauri entry)

- **feat(tauri): Tauri 2.0 集成 + 10 个 domain command + Capability ACL**（commit `e399073`）
  - `greet` + 9 业务 command（app / assets / export / help / pipeline / project / settings / theme / update）
  - Capability ACL（`apps/desktop/src-tauri/capabilities/default.json`）
  - `apps/desktop/src-tauri/src/lib.rs` Tauri 2 entry point

- **feat(desktop): React 19 + Vite 7 前端工程完整切换**（commit `2e21f68`）
  - `apps/desktop/` 从零搭建：6 routes · 12 component dirs · 7 hooks · 7 stores · 38 IPC types
  - TanStack Router/Query v5 · Zustand v5 · XState v5 · cmdk 命令面板
  - 同时删除 538 个 Python v2.4 旧主线文件（`src/app/` · `tests/services` · `docs_bundle/` · `uv.lock` · `main.py`）

- **chore(rust): 移除 vynaro-cli crate**（commit `57226ba`）
  - 纯桌面端无需独立 CLI 入口，3 个文件 + workspace member 一并清理
  - workspace 收敛为 13 个领域 crate + 1 个 Tauri entry（14 个 package）

### 💥 Breaking Changes（版本号与主线）

- **chore(release): 版本号回滚 v3.0.0-alpha.0 → v2.5.0**（commit `038eab4`）
  - 仅触动 4 个版本号配置文件 + `Cargo.lock` 同步：
    `Cargo.toml` · `apps/desktop/src-tauri/Cargo.toml` · `tauri.conf.json` · `package.json`
  - 业务代码 / 文档 / commit message 历史全部不动
  - cargo metadata 现报告 vynaro-\* package 一律 version = 2.5.0

- **chore(governance): Python v2.4 主线退役存档**（commit `75ce862`）
  - 退役公告与历史说明保留在 `CHANGELOG.md` 主体中，不再单列文件
  - `.gitignore`：tsbuildinfo / playwright-report / test-results 入库规则
  - v2.4 进入只读维护期，不添加新功能，仅修关键阻塞性 bug

### 🐛 Bug Fixes

- **fix(routes): 修正 help.test.tsx 的 HelpPage import 路径**（commit `51b771c`）
  - 路由入口 `routes/help.tsx` 只导出 `Route`，不导出 `HelpPage`
  - 测试目标测组件本身，应从 `../components/help/HelpPage` 而非 `./help` 导入
  - TS2305 消除，`pnpm exec vitest run src/routes/help.test.tsx` 从全失败 → 8/8 PASS

### 📚 Documentation

- **docs(readme): 重写根 README**（commit `24f92bc`）
  - 117 行 apps/desktop 子目录错误内容 → 390 行 v2.5.0 项目总览
  - 15 个章节：Hero · 定位 · 6 模块能力矩阵 · 架构图 · 技术栈 · 快速开始 · 项目结构 · 3 轨验证 · 发布流程 · 路线图 · 贡献指南 · 文档导航 · 历史归档 · License · 致谢
  - shields.io `for-the-badge` 徽章 + ASCII 架构图 + 11 张分类表

- **docs(refactor): 撤回 docs/refactor/v3-migration/ 入库**（commit `9076878`）
  - 上游明确指示该目录禁止提交
  - 21 个迁移文档从 index 移除，本地 working tree 保留供作者参考
  - `.gitignore` 重新启用 `docs/refactor/` 全忽略规则

### 🧪 Tests

- **总测试规模**（本次新增 + 入库）：
  - Rust workspace：`cargo test --workspace` **112 / 112 PASS**
  - 前端：`pnpm exec vitest run` **12 test files · 165 / 165 PASS**（help.test 8 项首次入库）
  - `cargo check --workspace` 0 errors
  - `cargo clippy --workspace --all-targets -- -D warnings` 0 warnings
  - `pnpm exec tsc --noEmit` EXIT=0
  - `pnpm build` 270 modules · 1.18s
  - `pnpm gen:ipc` 38 types generated

### 📝 关联文档

- 迁移方案：`docs/refactor/v3-migration/`（21 份，本地参考保留，不入库）
- 上线指南：[docs/guide/quick-start.md](docs/guide/quick-start.md) · [docs/guide/installation.md](docs/guide/installation.md)
- 发布流程：[docs/guide/release-process.md](docs/guide/release-process.md)
- 历史说明：见上文「chore(governance): Python v2.4 主线退役存档」段

### 🔗 完整 commit 链（10 commits，本分支）

```text
51b771c  fix(routes):   修正 help.test.tsx 的 HelpPage import 路径
24f92bc  docs(readme):  重写根 README · 反映 v2.5.0 真实工程状态
57226ba  chore(rust):   移除 vynaro-cli crate
9076878  docs(refactor): 撤回 docs/refactor/v3-migration/ 入库
038eab4  chore(release): 版本号回滚 v3.0.0-alpha.0 → v2.5.0
eb484a3  docs(refactor): v3.0 迁移方案文档完整入库 (历史痕迹，已被 9076878 抵消)
2e21f68  feat(desktop):  前端工程完整切换 + 删除 Python 旧主线
e399073  feat(tauri):    Tauri 2.0 集成 + 10 domain command
4fc4cd3  feat(rust):     Rust workspace + 13 个领域 crate
75ce862  chore(governance): Python 主线退役存档
```

---

## [2.4.3] - 2026-07-29

### 🐛 Bug Fixes

- **fix(tests): 修复 test_theme_runtime 硬编码颜色断言**
  - `test_theme_aware_mixin_*` 测试使用了硬编码的 `"BG=#f6f8fb"` / `"BG=#0f172a"`，
    主题 `_C.BG_BASE` 实际为 `"#eef3f8"`，导致本地断言失败；改为基于 `_C.BG_BASE` 的动态断言

### 🛠️ CI

- **fix(ci): Ubuntu Noble 安装 libEGL** — `ci.yml` test job 新增 `apt-get install -y libegl1 libgl1`，
  让 CI runner 拥有 libEGL.so.1，PySide6 可导入
- **fix(tests): PySide6 QWidget 测试加 `@pytest.mark.skipif` 头盾**
  - `test_home_viewmodel.py`、`test_ui_module_smoke.py`、`tests/ui/test_main_window.py`
    在 CI headless Linux 上跳过 QWidget 构造（libEGL 存在时仍然崩溃，解释器级 abort）
  - `test_theme_runtime.py`：用模块级 `pytest.skip` 包裹全部 PySide6/主题包导入（libEGL 缺失时模块
    不可收集，现在优雅降级为全部 skip，CI 退出码为 0）
- **新增 `tests/ui/test_assets_page.py`**: 素材目录页单元测试（含 skipif 头盾 + PySide6 免依赖的 contract 测试）

---

## [2.4.2] - 2026-07-29

### 🧹 Lint & Cleanup

- **fix(ci): 修复 ruff lint 检查失败 30 处**
  - 24 处 import 排序（I001）：自动修复
  - 4 处未定义变量（F821）：为 `project/manager.py` 和 `settings/manager.py` 添加缺失的 `json` import
  - 2 处方法重定义（F811）：移除 `main_window` 末尾重复的 `show_message`/`show_loading`
  - 4 处无用 import（F401）：清理 `script_stream`/`assets_page`/`home_page`/`production_page`
  - 1 处无用 dict 字面量（B033）：移除 `services/__init__.py` 中冗余定义
  - 1 处过时语法（UP035）：更新 `tts_providers.py`

### 🛠️ CI

- 同步 `uv.lock` 版本号至 2.4.2

---

## [2.4.1] - 2026-07-29

### 🐛 Bug Fixes

- **fix(ui): 修复 UI 页面加载崩溃导致交互无响应** (issue #96, commit `6b9c39f`)
  - `application.py`: 修正重构后遗留的 `project_manager`/`settings_manager` 导入路径，应用初始化成功
  - `viewmodels/__init__.py`: 修复 `scenefab.project_manager` 导入为 `scenefab.project.manager`
  - `settings_page.py`: 补充缺失的 `_QSETTINGS_ORG` / `_QSETTINGS_APP` 常量，设置页可正常打开
  - `main_window/__init__.py`: 修复 `QShortcut` 导入位置（QtGui），补充 `SystemTrayController` 实例化
  - `page_router.py`: 页面构造异常时显示可见的错误占位页，不再被 Qt 静默吞掉
  - `assets_page.py`: "素材目录"/"输出目录" 卡片新增"选择目录"按钮，跳转至系统设置页

### 🧹 Chore

- 移除 `state_machine.py` 中已废弃的 `_build_flow_table()` 函数及死代码（52 行）
- 同步 `uv.lock` 开发包版本号至 2.4.0

---

### 🎨 Brand & Docs (v2.4.0 品牌重塑 + 文档升级, 6 commits)

**触发**: "作为资深架构师，帮我完全重写 vynaro 项目的 docs 下的在线文档、README.md、logo 和资源图片，设计必须好看专业，使用，大气、美观" (2026-07-03)

- **feat(brand): redesign logo system + render pipeline** (commit `fdd7e73`) — 22 files +788/-153
  - 3 SVG 重设计: `assets/logo-mark.svg` (256²) + `assets/logo-horizontal.svg` (512×128) + `docs/public/favicon.svg` (32²)
  - 保留核心识别符 (Play 三角 + dark bg + cyan/violet), 升级精致度 (双环轨道 + AI 弧线 + 4 tick)
  - `resources/app_icon.svg` 重写为**无文字版** (符合 `resources/README.md` 自家 design 原则)
  - `resources/icons/app_icon_{32,64,128,256,512,1024}.png` (6 尺寸 PNG 全部重新生成)
  - `docs/public/og-image.png` (NEW, 1280×640): **修复 og:image 404 bug** — `config.ts` 一直引用但文件从未存在
  - 注：原 v2.4 时期的 `scripts/render-assets.py` 渲染流水线在 v2.5.0 收官清理中已移除，资产改由 `assets/` 仓库源文件 + 设计师同步维护
- **feat(icons): upgrade 24×24 feature icons with duotone palette** (commit `52a0256`) — 6 files +152/-46
  - 6 个 docs 站功能图标从单色 cyan → cyan + violet 双色调 (multi-video / monologue / emotion / module / style / export)
  - stroke 从 2.0 → 1.75, round caps, AI 模块用 violet 强调
- **docs(readme): full restructure with hero, mermaid arch, roadmap** (commit `b120e56`) — 1 file +212/-109
  - README.md 271 → 373 行: Hero + 痛点表 + 2×3 能力矩阵 + Mermaid 架构图 + 路线图 3 阶段 + Conventional Commits 表
  - shields.io `for-the-badge` 徽章 (主人偏好, 不是自托管 SVG)
- **feat(docs): redesign homepage with role cards, workflow timeline, platform grid** (commit `b3c435c`) — 3 files +533/-35
  - `docs/index.md` 95 → 192 行: 5 个新 section (角色入口 + 6 步工作流 + 8 平台 + 6 技术栈 + CTA)
  - `docs/.vitepress/theme/style.css` 873 → 1247 行: +374 行 (sf-role-card / sf-workflow / sf-platform-grid / sf-tech-grid / sf-cta / Hero gradient mesh / fade-in 动画)
  - `docs/cspell.json` 新增 'Pydantic' / 'uvicorn' (技术栈合法词)
- **feat(brand): wire new logos into VitePress + document brand system** (commit `7c495ee`) — 2 files +39/-6
  - `docs/.vitepress/config.ts` logo 字段升级: `/logo.png` (旧 64×64) → `/logo.svg` (新 256² mark)
  - alternate icon `/logo.png` → `/favicon.png` (新生成)
  - `resources/README.md` 新增 "Brand Identity" section: 5 资产清单 + 色系 + 6 icon + pipeline
- **feat(brand): add light theme logo variants + auto-switching nav** (commit `b08bdea`) — 10 files +381/-3
  - `assets/logo-mark-light.svg` + `logo-horizontal-light.svg` (NEW): 浅色主题版本 (白底 + 深 cyan #0891b2 + 深 violet #7c3aed)
  - 4 尺寸 light PNG (128/256/512/1024)
  - `config.ts` logo 字段升级 `{ dark, light, alt }` 平铺格式 (不是 `src` 嵌套!) — VitePress `ThemeableImage` 第 3 种
  - 踩坑修正: 首次写 `{ src: { light, dark } }` 触发 `TypeError: path.startsWith is not a function` build 失败, 修正为 `{ light, dark, alt }` 平铺后通过

**修复的隐藏 bug**:

- 🐛 `docs/public/og-image.png` 一直**不存在** (`config.ts` og:image 引用但从未创建), 现已新建 1280×640 社交卡片
- 🐛 `resources/app_icon.svg` 违反自家 `resources/README.md` "text-free" 原则 (有 Vynaro 文字), 现已无文字版
- 🐛 cspell 字典漏 `Pydantic` 和 `uvicorn` (技术栈合法词), 现已加入

**校验全过**:

- `npm run docs:build` ✓ 7.68s (vitepress v1.6.4)
- `npm run docs:lint` ✓ 0 errors (markdownlint-cli2 v0.23.0)
- `npm run docs:spellcheck` ✓ 0 errors

**GitHub repo 校准**:

- description: vynaro - AI 影视解说创作工具 | 智能拆条 · AI 解说生成 · 一键配音合成 ✓ (已对齐)
- topics: +'brand-redesign' +'vitepress' (新增双主题 + 文档站)
- 详见 `references/vynaro-brand-redesign-2026-07-03.md` (待沉淀)

**参考经验**: frame-fab 2026-07-02 (13 步全栈重写, 65 files) + project-brand-redesign skill 沉淀 + vynaro 2026-06-02 三 PR saga (避免 squash 漏文件 + shields.io 偏好)

### 🛠️ CI / Docs

- **ci(docs): 用 lychee 替换孤儿外部链接检查脚本** (commit `d4cfeac` ~ `f56405d`, 7 commits) — docs/ 第 5 层 CI
  - 新增 `.lychee.toml` (accept 4xx 容忍反爬, exclude 自指, 3 次重试, 30s 超时)
  - 新增 `.github/workflows/docs-external-links.yml` (周更周日 07:00 UTC + push/PR/dispatch, `lycheeverse/lychee-action@v2.8.0`, GitHub cache 复用)
  - 新增 `.lycheeignore` 兜底(实际未被使用,见下)
  - 删 `scripts/docs-check-external-links.mjs` (孤儿脚本, 仅 HEAD 5xx/405 无法处理 deepseek 等反爬)
  - `docs/package.json`: `docs:check-external-links` 改用 lychee 命令(本地可用)
  - **5 次失败尝试 → 1 次成功的真实轨迹**:
    1. `exclude_loop` → `exclude_loopback` 字段名修正 (v0.23+ 重命名)
    2. `.lycheeignore` 不生效(根相对链接在 build URL 阶段崩, 早于 ignore 过滤)
    3. `--base-url` / `--root-dir` 仍会 GET GitHub Pages(职责重复)
    4. `--scheme https` 对无 scheme 链接不生效
    5. `--remap '^/ ...'` 失败(v0.24 只接受字面前缀, 不接受正则)
  - **最终方案**: workflow 加 sed 预处理 step, `](/guide/...)` → `](https://internal.invalid/guide/...)`, 配合 `.lychee.toml` exclude 占位 host
  - **CI 验证**: run #28633088278 ✅ Total 40 / Successful 7 / Errors 0
  - **新增 4 层 docs CI** (本次扩展): format / lint / spellcheck / links(内部) / **links(外部)** — 见 `references/vynaro-docs-ci-4layer-2026-07-02.md`

### 🔮 后续 (P2 候选, 暂未实现)

- drag-drop 文件拖拽 (`dragEnterEvent` / `dropEvent` override on `AssetsPage`)
- viewmodel 直接 import `scenefab.services.X` / `scenefab.models.X`,不 import `scenefab.ui.*` 任何东西(目前用 `TYPE_CHECKING` 解决 runtime,但逻辑分层仍耦合 UI 类型)

---

## [2.4.0] - 2026-07-01

> Vynaro v2.4.0 — UI 架构全面升级: Phase 1 ~ 3+ 闭环 (ViewModel 化 + 暗色主题 + 运行时切换)

5 个子阶段累计落地, 39 commits (5 月底 → 7 月初), 净增 UI 模块化分层 + 实时主题切换端到端。

### 🏗️ Architecture (Phase 1 拆分)

- **refactor(ui): drop dead theme + split main window + wire application** (commit `8e7c8f4`) — Phase 1 重构, 净 **-1536 行**
  - 删除 1462 行死代码: `tokens.py` / `theme_manager.py` / `base_styles.py` / `resources/styles/*.qss` / 空 `__pycache__` 幽灵目录
  - `ui/main/registry.py`(新): `NAV_ITEMS` / `PAGE_TITLES` / `PAGE_BUILDERS` 单源真相, 消除 `nav_components.NAV_ITEMS` 与 `main_window.PAGE_TITLES` 双源
  - `ui/main/page_router.py`(新): 页面懒加载 + 路由
  - `ui/main/system_tray.py`(新): 系统托盘生命周期
  - `ui/main/controls.py`(新): `ToggleSwitch` 抽离
  - `VynaroMainWindow` 从 273 行(6 职责)缩为装配器, 接 `application=` 注入 (Phase 2 留口)
  - 755 passed / 1 skipped (基线 562 → +193 项目成长)

- **feat(ui): HomePage ViewModel + service injection** (commit `4098e0d`) — Phase 2A, 4 张状态卡接 `ProjectManager` 实时数据
  - `ui/viewmodels/__init__.py`(新): `ViewModelBase` 抽象基类
  - `ui/viewmodels/home_viewmodel.py`(新): `HomePageViewModel` 订阅 `project_opened` / `project_closed` / `project_saved` / `recent_projects_updated` 信号, 暴露 5 个变化信号
  - `ui/main/registry.py`: `PageBuilder` 签名从 `() -> QWidget` 改为 `(Application | None) -> QWidget`, 新增 `_build_home` 工厂
  - `PageRouter.__init__` 接 `application=`, 转给 `PAGE_BUILDERS[page_id](app)`
  - `HomePage` 接 `viewmodel=` 参数, 4 张状态卡改读 `vm.media_count` / `scene_count` / `script_status` / `export_config`, 最近资产改读 `vm.recent_projects`
  - 无 project / 无 application 时, VM fallback 到"未导入 / 0 / 待生成 / 1080x1920" 默认文案 (行为同 Phase 1)
  - 4 个新测试 `tests/test_home_viewmodel.py`, 覆盖: 无 application fallback / 有 application 无 project / 有 VM 渲染 / 无 VM 静态默认

### 🧠 ViewModel 架构 (Phase 2B + 2C)

- **feat(ui): ProductionPage ViewModel + 5-step pipeline state machine** (Phase 2B)
  - `ui/viewmodels/production_viewmodel.py`(新): `ProductionPageViewModel` 暴露 `step_definitions` / `step_status` / `pipeline_state` / `current_step` 4 个属性, 5 个变化信号
  - 5 步流水线状态机: `pending` → `active` → `done` (或 `error`)。`STEP_DEFINITIONS` 常量抽到 VM, ProductionPage 从 `vm.step_definitions` 拿, 避免两边数据漂移
  - `QThreadPool` + `QRunnable` + 内部 `QObject` signals 实现 step 推进跨线程
  - 状态切换 idle / running / done / failed, `start_pipeline(src, ctx)` / `reset_pipeline()` 公开方法
  - 6 个新测试 `tests/test_production_viewmodel.py`

- **feat(ui): AssetsPage ViewModel + recent projects + asset summary** (Phase 2C)
  - `ui/viewmodels/assets_viewmodel.py`(新): `AssetsPageViewModel` 暴露 `current_assets` (`AssetSummary`) / `recent_projects` (`list[RecentProjectInfo]`)
  - `RecentProjectInfo` dataclass: 从 `ProjectManager.get_recent_projects()` 返回的 `list[str]` 包装成 UI 友好的元数据
  - `AssetSummary` dataclass: media / script / audio / export 4 类计数 + `total` / `is_empty` 派生属性
  - 订阅 PM 5 个 signals, 无 application 时 fallback 到空 summary
  - 8 个新测试 `tests/test_assets_viewmodel.py`

- **chore(app): register MonologueMaker in DIContainer** (Phase 2B 硬前置)
  - `application.py` 在 `project_manager` 之后注册 `monologue_maker` (`MonologueMaker()`)
- **refactor(ui): ViewModel wiring via registry factories** — `ui/main/registry.py` 新增 `_build_production` / `_build_assets` 工厂

### ⚡ 运行时集成 (Phase 2B+1 + 2D+)

- **feat(ui): wire 2B+1 live runner — env-gated MonologueMaker integration**
  - `ProductionPageViewModel` 新增 `runner_mode` 属性 (`"noop"` / `"live"`) + `_setup_pipeline()` + `_live_runner()` factory
  - `runner_mode` 由 `_has_runtime_keys()` 决定 — 检查 `VYNARO_TTS_KEY` / `VYNARO_LLM_KEY` 环境变量
  - live mode 下: `_setup_pipeline` 调 `maker.create_project(src, ctx)`, 失败自动降级 noop 并打 warning
  - 4 个新测试: runner_mode 默认 noop / env 触发 live / `_has_runtime_keys` 单元 / live 失败降级 noop

- **feat(ui): wire 2D+ import button to file dialog (拖拽导入素材 placeholder)**
  - `AssetsPage` `_on_import_requested` slot: 点击"导入素材"按钮弹 `QFileDialog.getOpenFileNames` 多选
  - 过滤器支持视频 (mp4/mov/mkv/avi/flv/wmv) + 音频 (mp3/wav/m4a/flac) + 所有文件 fallback
  - 选中后调 `vm.import_media(paths)` 转发到 `ProjectManager.add_media_file`
  - 移除了 `import_requested` signal 的 emit — page 自治, 信号无人接是 zombie

### 🎨 暗色主题 (Phase 3)

- **feat(ui): Phase 3 dark theme palette + set_theme_mode runtime switch** (commit `99fa6b7`)
  - `ui/theme/ds_tokens.py` 新增 `DarkColors` class — 41 个 color token 全部镜像 (深色背景 + 提亮主色 + 反转文字)
  - `set_theme_mode(mode: str) -> str` 全局函数: 重新绑定 `_C` 所有颜色属性到 `Colors` / `DarkColors` 对应 palette
  - `get_theme_mode() -> str` 读 active 状态; 支持 `"light"` / `"dark"`, 未知 fallback light
  - 7 个新测试 `tests/test_theme.py`

### 🌗 运行时切换端到端闭环 (Phase 3+, 本次 05b885f + d544c37)

- **feat(ui): wire Phase 3 runtime theme switcher + Settings UI** (commit `05b885f`)
  - `ui/theme/runtime.py`(新): `restyle_app(app=None) -> int` 遍历 `QApplication.allWidgets()`, 对每个 widget 调 `style().unpolish(w) / polish(w) / w.update()`; headless/无 QApplication 路径返回 0
  - `ThemeAwareMixin` 让 `QWidget` 派生类持 `_build_stylesheet: Callable[[], str]`, `apply_theme()` 重新求值并 `setStyleSheet(qss)` 返回新 QSS
  - `ui/theme/__init__.py`(新): 包级 re-export `restyle_app` / `ThemeAwareMixin` / `set_theme_mode` / `get_theme_mode` / 全部 design token, 统一入口
  - `VynaroMainWindow(QMainWindow, ThemeAwareMixin)`: 初始化时 `setStyleSheet(build_global_stylesheet())`, 通过 `_wire_theme_switcher()` 懒连接 `SettingsPage.theme_changed` signal (用 `_theme_signal_wired` flag 去重, 因为 router 缓存页面会重复 visit)
  - `_on_theme_switched(mode)`: 完整切换链 `set_theme_mode(mode)` → `self.apply_theme()` → 遍历 `router._page_map` 找所有 `ThemeAwareMixin` 页面 `apply_theme()` → `restyle_app()` 重 polish 非主题 widget (e.g. native dialog)
  - `SettingsPage(QFrame, ThemeAwareMixin)`: 新增 `_appearance_group` (浅色/深色 combo), `currentIndexChanged` 触发 `theme_changed` signal 传 `"light"` / `"dark"`; 同时提供 `set_theme_mode_index(mode)` 在 startup 时从 QSettings 恢复用户偏好
  - `docs/public/logo-horizontal.svg`(新): 暗色主题配套横版 logo (与正方形 logo 同色系, 横版布局适配 512x128)
  - **mypy 清理**: 删除 3 个未触发的 `# type: ignore` 注释; `restyle_app` 加 `isinstance(app, QApplication)` 收窄 `QCoreApplication` 类型差
  - **架构价值**: Phase 3 暗色主题从「token 切了但 UI 不刷新」升到「Settings → SettingsPage.combo → MainWindow → 所有页面 + 全局 widget 实时重 polish」端到端闭环

- **fix(test): gate test_theme_runtime on libEGL availability (CI compat)** (commit `d544c37`)
  - 修复 CI runner 无 libEGL 时 `no_qapp` fixture 触发 `ImportError` 链
  - 修法: `pytest.skip(allow_module_level=True)` + `(ImportError, OSError)` 双抓 — pytest 官方"module unavailable" pattern
  - 本地有 libEGL → 7/7 跑; CI runner 无 libEGL → 7/7 SKIPPED (exit 0)

- **refactor(ui): drop zombie re-export of VynaroMainWindow from `__init__`** (commit `eac6059`, P1 架构清理)
  - `scenefab.ui.__init__` 删除 `from .main.main_window import VynaroMainWindow` + `__all__`
  - **价值**: 解 `import scenefab.ui.viewmodels.X` → `scenefab.ui.__init__` → `VynaroMainWindow` → `PySide6.QtWidgets` → libEGL 链
  - **根本原因** — 06-30 早 + 06-30 晚两轮 libEGL 修复的根因

### 🧪 Tests

- 新增 32 个测试, 共 **791 passed / 1 skipped** (基线 759 → +32)
  - Phase 2A HomeVM: +4
  - Phase 2B ProductionVM: +6
  - Phase 2C AssetsVM: +8
  - Phase 2B+1 Production runner: +4
  - Phase 3 theme palette: +7
  - Phase 3+ theme runtime: +7 (含 `no_qapp` fixture 修跨测试 QApplication 单例污染)
- **修复 1 个真测试设计 bug**: `no_qapp` fixture 用 `monkeypatch.setattr(QApplication, "instance", ...)` 隔离跨测试 QApplication 单例污染 — 此前 `test_home_viewmodel` 跑完后 `restyle_app` 静默遍历残留 widgets (140 个), headless 测试断言 `0 == 140` 一直假绿

### ⚠️ 不兼容变更

- `VynaroMainWindow` 必传 `application=` 参数(主入口 `main.py` 已同步)
- 页面元数据 (导航 / 标题 / 工厂) 统一从 `scenefab.ui.main.registry` 导入
- `PageBuilder` 签名变更: `(Application | None) -> QWidget`, 第三方自定义 page builder 需要更新
- `scenefab.ui.__init__` 不再 re-export `VynaroMainWindow`, 显式路径 `from scenefab.ui.main.main_window import VynaroMainWindow`

---

## [2.3.0] - 2026-06-26

> Vynaro v2.3.0 — 代码审计 + 2 P1 安全修复 + API/UI 测试覆盖补齐

### 🐛 Bug Fixes

- **fix(security): hardware.py subprocess 走 SecureExecutor 审计链** — `check_nvidia_smi` / `check_intel_cpu` 改走新 `get_probe_executor()` 单例 (白名单: nvidia-smi, wmic), 不再裸 `subprocess.run`. 移除 `import subprocess`. 异常类型改 `SecurityError` + `TimeoutError`
- **fix(security): api/routers/pipeline.py 缺路径校验** — 复用 export router 模式 (`_DEFAULT_ALLOWED_BASE_DIRS` + `_get_path_validator` + `_validate_output_dir`), 早期拒绝空 `video_url`, `_process_narration` 校验 `output_dir` 失败时降级到 `cwd/outputs/jianying_drafts`
- **fix(api): GET / 根路由未注册** — `@app.get("/")` 在 `app = create_app()` 之后定义, 装饰器把 root 注册到 `app` 局部变量, 实际不生效. 修复: 把 root 移入 `create_app()` 函数内
- **fix(api): GET /api/v1/plugins/types 永远 404** — FastAPI 按路由声明顺序匹配, `/plugins/{plugin_id}` 在 `/plugins/types` 之前注册, 拦截 "types" 路径. 修复: 重排为 `/plugins` → `/plugins/types` → `/plugins/{plugin_id}` → `/plugins/{plugin_id}/enable`
- **fix(ci): detect libEGL.so.1 to skip ui smoke in headless CI** (commit `3ea77e6`) — 之前 conftest 只在 PySide6 import 失败时 skip, 但 CI runner 装了 PySide6 + 无 libEGL 时 `importlib` 仍尝试加载 Qt → `libEGL.so.1` 缺失. 修复: 加 `ctypes.CDLL` 检测 libEGL, 缺则 skip ui smoke. 本地 PySide6 6.11 + offscreen 仍能跑全部 8 个测试

### 🔧 Maintenance

- **refactor(llm): narrow HTTPClientMixin.\_call_api** — 改前 `except Exception` (宽 catch, 吞 RuntimeError/TypeError), 改后异常分两段 catch: `httpx.HTTPStatusError` → `_handle_http_error`, `httpx.HTTPError` → `ProviderError("网络错误")`, `json.JSONDecodeError/ValueError` → `ProviderError("响应解析")`. 真 bug 不再被吞
- **chore(cleanup): jianying_exporter.py MaterialType 注释** — pyflakes 报 "unused", 实际是间接 re-export (不在 `__all__` 但与其他 adapter 类型对齐). 注释明确为 "package-private" + 指引测试用 `from jianying_adapter import` 直路径
- **test(api): 补 api/ 0% 测试覆盖** — 18 个集成测试覆盖 5 个 router (health/pipeline/plugins/export/projects) + 全局异常处理 + 路由顺序
- **test(ui): 补 ui/ 0% 测试覆盖** — 8 个 headless-safe smoke test 覆盖 VynaroMainWindow 类结构 + 子模块 import + theme 模块
- **style: ruff auto-fix 49 lint errors + skip ui smoke in headless CI** (commit `fff0168`) — R13 audit 引入 49 个 ruff 错 (17 F401 + 15 I001 + 2 F841 + 8 UP0xx + 1 B007) 未跑 `ruff --fix`. `--fix --unsafe-fixes` 全自动清零, 19 文件 +39/-52. **0 行为变化**
- **chore(dead-code): drop 2 unused plugin example plugins (-655 LOC)** (commit `fcc8203`) — Dim 14 dead-file scan 报 40 候选, pytest 验证后仅 2 真死 (`plugins/examples/cinematic_subtitle` + `plugins/examples/deepseek_ai_generator`). 其余 38 个是 `_EXPORTS` lazy import / relative `__init__.py` import / `__main__.py` 隐式引用 / startup smoke test 引用 — 全保. **净效果**: 2 files / 655 LOC 真死删除, 0 行为变化

### 🛡️ Security

- **新 utils/security.py:get_probe_executor()** — 全局 read-only 探测执行器单例, 白名单: `nvidia-smi`, `wmic`. 仍受 SecureExecutor 审计链约束 (白名单 + 路径 + shell=False + env sanitization)

### 诚实性记录

- **pyflakes 4 个 false positive** 经主 agent 亲自 verify: 3 个是懒导入/TYPE_CHECKING 模式 (非 bug), 1 个是 docstring 字符串
- **HTTPClientMixin 抽取 ROI 调研** 发现流式模式 (`async with self.http_client.stream`) 抽不出干净 helper (嵌套 context manager 冲突), 改为 narrow 化已有 `_call_api` 获得真 ROI
- **headless UI 测试** 写"结构契约 + import smoke" 替代行为测试, 避免 PySide6 offscreen + 系统 GL 库缺失的 flaky

### 测试

- 748 → 755 passed (+7, +1 skipped typography optional)
- 0 regression across 39,848 LOC
- 25 commits ahead of remote, 全部 pushed

### PR 链 (6 commits, all pushed)

| SHA       | 类型          | 摘要                                                  |
| --------- | ------------- | ----------------------------------------------------- |
| `7da45ec` | fix(security) | 2 P1 — hardware subprocess + pipeline router 路径校验 |
| `2727e02` | refactor(llm) | narrow HTTPClientMixin.\_call_api 异常分两段          |
| `b57cda4` | test(api)     | 补 api/ 覆盖 + 修 2 真 bug (根路由 + 路由顺序)        |
| `4543ea3` | test(ui)      | 补 ui/ smoke test                                     |

---

## [2.2.0] - 2026-06-25

> Vynaro v2.2.0 — 深度架构重构（PR #88）+ API 安全加固

### 🚀 Features

- **examples/ 目录** — 5f214d1 closes #90，新增示例项目
- **架构深度重构** — 9b1bccf v2.2.0 主 PR, 删除 ~15000 行死代码, 收敛 5 个 LLM provider 基类, 统一 retry/JSON IO/项目 IO
- **全站文档专业重设计** — README、架构概览、AI 模型、配置参考

### 🐛 Bug Fixes

- **fix(api): 修 P0 字段名不一致** — `pipeline.py:124` `req["source_video"]` → `req["video_url"]` (与 schema 对齐, 修 KeyError 死路); emotion 默认值 `"惆怅"` → `"healing"` (对齐 EmotionType 枚举)
- **fix(api): 路径校验改用 PathValidator** — `export.py:80-94` 自造 `".." in parts` 校验改走 `PathValidator` + `DANGEROUS_PATH_PATTERNS` + 扩展名白名单 + 4 个默认 base_dir (cwd/outputs, ~/.scenefab/exports, ~/Downloads, ~/.cache/scenefab/exports); 可通过 `settings.allowed_base_dirs` 扩展
- **fix(export): ExportManager dispatch 显式化** — DirectVideoExporter 缺统一 `export()` 方法, 调用链 `ExportManager.export → exporter.export` 抛 `AttributeError`; 改为显式 `_dispatch` 分发到 `JianyingExporter.export(draft, output_dir, ...)` 或 `DirectVideoExporter.export(project_data, config)`, 缺字段时抛明确 `ExportError` 而非 crash
- **fix(test): test_project_manager 不硬编码版本** — `assert metadata.version == "2.1.2"` 改为 `get_version_string()` 动态断言, 跟随 pyproject 真实状态
- **fix(ci): ruff lint** — import 排序 + 语法残留 + 未使用导入清理 (e0b5208 / bd2152a / ad739fe / 1bf19da / 2c9e055)

### 🔧 Maintenance

- **chore(release): version 2.1.2 → 2.2.0** — 跟随 PR #88 实际状态, pyproject.toml + utils/version.py
- **chore(cleanup): 删 4 个空目录** — `cache_impl/` / `interfaces/` / 顶层 `orchestration/` / `services/viral/` (无 .py 残留, 仅 `__pycache__`)
- **test(update): 补 update/checker.py 测试** — 0% → 100% 覆盖, 20 个测试 (parse_version / strip_tag / check_update 7 个 mock 场景 / format_update_message)
- **test(export): 手写 P0 路径校验 10 case 回归测试** — 危险路径 400 / 白名单 202 / None 202 全部按预期

### 🗑️ Removed (v2.2.0 重构期间)

- `core/batch_processor.py` (526) / `core/config_v2.py` (448) / `core/event_store.py` (419) / `core/platform_adapter.py` (643) / `core/platform_extended.py` (622) / `core/ws_hub.py` (330)
- `services/ai/adapters/` / `services/ai/infra/` / `services/ai/asr.py` / `tts.py` / `cache.py` / `manager.py` / `llm.py` / `errors.py` / `interfaces.py` / `model_registry.py` / `vision.py` / `sensevoice_provider.py` (637) / `whisper_asr_provider.py` (305) / `providers/gemini35_flash.py` (359) / `provider_models.py` (226)
- `services/ai_service_manager.py` / `services/service_manager.py` / `services/export/video_exporter.py` (409)
- `utils/config.py` / `pickle_io.py` / `performance.py` / `secure_config_loader.py` / `shortcut_manager.py`
- 顶层 `task_manager.py` (519) / `version_manager.py` (573) / `version_models.py` / `registry_models.py` / `service_container.py` / `event_bus.py` / `cache_manager.py`

### 测试

- 611 → **631 passed** (新增 20 个 update/checker 测试)
- 手写 10 case P0 路径校验回归测试全部通过
- ruff 修复后 CI green

---

## [2.1.2] - 2026-06-22

> Vynaro v2.1.2 — 模型目录统一 · 架构精简 · 文档专业重设计

### 新增

- **模型目录单源真相** — `ModelProfile` 冻结数据类 + `MODEL_CATALOG` 覆盖 10 个 Provider；`DEFAULT_MODELS` / `NARRATION_MODEL_STACK` / `settings_model_options()` 统一派生
- **端到端冒烟测试** — 35 个测试覆盖 VisionService → ScriptGenerator → SubtitleTranslator → DirectVideoExporter 全流水线
- **VisionAnalysisResult 兼容增强** — 新增 `__getitem__` / `__contains__` / `get()` / `keys()` / `to_dict()` 方法

### 重构

- **Provider 模型统一** — 所有 Provider 从 `model_catalog` 派生 `MODELS` 和 `DEFAULT_MODEL`，消除硬编码
- **LLMManager 配置模型生效** — 新增 `_apply_configured_model()`，`LLMRequest(model="default")` 正确应用 YAML 配置
- **导出层精简** — 删除 `video_exporter.py`（409 行），只保留 `DirectVideoExporter`
- **视觉链精简** — 删除 `gemini35_flash.py`（359 行）和 `QwenVLProvider` 死代码
- **兼容层清理** — 删除 `ai_service_manager.py` / `service_manager.py` / `utils/config.py`（零消费者）

### 修复

- 修复 `ConfigManager.get()` 对缺失 key 抛出 AttributeError 的问题（Issue #82）
- 修复 `VisionProvider` 返回类型声明
- 修复 Settings UI 中的模型名称
- 修复 Script Generator fallback 模型名
- 修复 `SubtitleTranslator` 导入路径
- 修复 `ErrorInfo.timestamp` Qt 实例调用问题
- 修复 `DirectVideoExporter._progress_callback` 未初始化问题
- 修复 `release-build.yml` 的发布依赖链（PR #85）

### 文档

- 全站文档专业重设计：README、架构概览、AI 模型、配置参考、功能矩阵、安全设计
- VitePress 主题更新：统一配色方案
- 架构文档添加 4 个 Mermaid 图（架构 / 交互 / 流水线 / 数据流）

### 测试

- `test_integration.py` 重写 — 31 个测试全部修复
- `test_model_catalog.py` 扩展 — 3 → 35 个测试
- `test_vision_providers.py` 更新 — QwenVLProvider → Qwen37FrameProvider
- 总计 695 passed, 1 skipped

### 移除

- `services/ai/providers/gemini35_flash.py` — 冗余 Provider
- `services/export/video_exporter.py` — 旧导出器
- `services/ai_service_manager.py` / `service_manager.py` — 兼容层
- `utils/config.py` — 零消费者配置系统
- `tests/test_video_exporter.py` — 旧导出器测试

---

## [2.1.1] - 2026-06-16

> Vynaro v2.1.1 — 解说生成状态机 + 架构基线清理

### 新增

- **解说生成状态机** — 5 状态 + 评估循环（UNDERSTAND → STORYGRAPH → DRAFT → EVALUATE → HOOK_REWRITE）
- **NarrationEvaluator** — 5 维加权解说稿质量评估器

### 维护

- 测试入口修复：`pytest` 无需 `PYTHONPATH=src` 或 editable install 即可运行
- 版本号单源真相：`pyproject.toml` / README 徽章 / UI 导航构建标签统一
- 死代码与生成物清理（UI 旧组件、`__pycache__` / `.pyc`）

---

## [2.1.0] - 2026-06-04

> Vynaro v2.1.0 — 架构升级：单源真相事件总线 + 类型化领域事件 + DI 现代化

### 新增

- **UnifiedEventBus** — 取代 v1.x 两个并行 EventBus 实现；字符串事件 + DomainEvent 强类型事件统一入口
- **类型化领域事件** — 8 个预定义 `DomainEvent`（Pipeline / Task / LLM / FFmpeg）
- **UnifiedTask 状态机** — 合法状态转换图 + CancelToken + TaskSource
- **DIContainer v2.1** — SCOPED 作用域 + 解析钩子 + 全局自动注入
- **TaskStore 3 后端** — InMemory / SQLite / Redis
- **EventStore 持久化** — 按 event_name / correlation_id 查询 + 自动双写
- **SettingsV2** — pydantic-settings + 7 配置组 + env 自动映射 + JSON Schema 生成
- **WebSocket Hub** — 实时推送事件到 WS 客户端

### 集成

- `TaskManager` / `PipelineEngine` 自动发布领域事件
- v1.x 公开 API 完全兼容

### 测试

- `tests/test_arch_v21.py` — 43 个 v2.1 新增测试，76/76 全过

---

## [2.0.0] - 2026-06-04

> Vynaro v2.0.0 — 短剧解说特化与 DAG 并行流水线

### 新增

- **DAG 并行流水线引擎** — 拓扑排序 + parallel_group 并行执行；短剧整季生产 25 集从 ~29min 降至 ~15min（↓48%）
- **FFmpeg 安全封装** — 参数白名单 + 危险字符检测 + 路径黑名单 + 审计日志
- **操作审计日志** — SQLite 持久化 + `track()` 上下文管理器
- **批量任务处理器** — 并行 worker + 自动重试 + 断点续传
- **短剧解说特化** — 4 风格 + 7 桥段识别 + 集数扫描
- **多平台智能适配** — 8 平台配置 + 智能裁剪 + 平台专属封面
- **统一 Worker 基类** — PySide6 / headless 双模式
- **LLM 流式输出 Worker** — 逐 token Signal 推送 + 句子边界检测

### 性能

| 指标           | v1.1.0 | v2.0.0 | 提升  |
| -------------- | :----: | :----: | :---: |
| 10min 视频处理 |  ~70s  |  ~40s  | ↓ 43% |
| 短剧整季 25 集 | ~29min | ~15min | ↓ 48% |
| LLM 首字延迟   |  20s   |  < 2s  | ↓ 90% |

---

## [1.1.0] - 2026-06-02

> Vynaro v1.1.0 — 大型架构重构与质量改进

### 改进

- **8 阶段架构重构** — 消除重复类型定义、清理冗余兼容层、拆分大文件、统一枚举与命名
- **依赖审计** — 同步运行依赖，移除冗余工具，升级 PySide6 6.9.0 / pydantic 2.5.0

### 兼容性

- 完全向后兼容 v1.0.x，所有公共 API 与 import 路径保持不变

---

## [1.0.1] - 2026-05-31

> Vynaro v1.0.1 — 修复 GUI 启动问题

### 修复

- 修正 `app.ui.components.containers.common_styles` 旧路径
- CI release-build workflow 路径与构建参数对齐

---

## [1.0.0] - 2026-05-31

> Vynaro v1.0.0 — 首个正式发行版。

### 核心功能

- AI 视频解说生成（Qwen3.7 + DeepSeek-V4 + Edge-TTS / F5-TTS）
- AI 视频混剪（智能分组 + 情绪峰值检测 + 视角映射）
- 导出支持（MP4 / MOV / GIF + 剪映草稿）
- 多平台预设（B站 / YouTube / Twitter / TikTok / 微信）

### 架构

- Provider 插件化（VisionProvider / LLMProvider / TTSProvider）
- 依赖注入 + 事件驱动
- PySide6 桌面端

### 安全

- SecureExecutor：所有 subprocess 统一安全策略校验
- PBKDF2：HMAC 迭代次数 480,000（OWASP 标准）

### 质量指标

- 测试：389+ passed, 0 failed
- Ruff Lint：All checks passed
- 死代码清理：删除 820+ 行冗余代码
