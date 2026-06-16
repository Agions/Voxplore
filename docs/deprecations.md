# 弃用清单 (Deprecation Inventory)

> 维护人：Agions · 最后更新：2026-06-16 (v2.1.1)
>
> 本文档跟踪计划移除的兼容层与遗留代码。每条目标注：现状、替代品、迁移期限、移除版本。
> 规则：能删就删；暂不能删的集中为兼容 shim 并在此登记移除期限。

## 状态图例

- 🟥 **可删** — 无活动引用，下个小版本移除
- 🟧 **shim** — 仍有引用，保留薄兼容层，标注移除期限
- 🟩 **活跃** — 误判为弃用，实为活跃实现（仅命名待规范化，见 P5）

---

## 1. 导出层 (export)

| 模块                                                  | 状态    | 说明                                                         | 替代品                | 移除版本   |
| ----------------------------------------------------- | ------- | ------------------------------------------------------------ | --------------------- | ---------- |
| `services/export/video_exporter.py` (`VideoExporter`) | 🟧 shim | 类内已 `warnings.warn(DeprecationWarning)`，仍含真实拼接逻辑 | `DirectVideoExporter` | **v2.3.0** |

**迁移指引**：`export_manager.py` 已全部改用 `DirectVideoExporter`。`VideoExporter` 仅经 `export/__init__.py` 再导出对外可见。
v2.2 周期内将 `video_exporter.py` 的真实实现抽空、仅保留转发到 `DirectVideoExporter` 的薄壳；v2.3 删除文件与 `__init__` 导出。

## 2. AI 服务管理 (services.ai)

| 模块                                                     | 状态    | 说明                                | 替代品                                  | 移除版本   |
| -------------------------------------------------------- | ------- | ----------------------------------- | --------------------------------------- | ---------- |
| `services/ai_service_manager.py`                         | 🟧 shim | 纯转发，模块级 `DeprecationWarning`                 | `services.ai.manager.AIServiceManager` | **v2.3.0** |
| `services/service_manager.py` (`get_ai_service_manager`) | 🟧 shim | P2 已瘦身为转发；调用即 `DeprecationWarning`        | `services.ai.manager.get_ai_service`   | **v2.3.0** |

**P2 已完成**（2026-06-16）：
- `application.py._init_services` 改为 `from scenefab.services.ai.manager import get_ai_service`，直接注册 V2 全局单例。
- `services/service_manager.py` 删除无人使用的 `ServiceManager` 注册表类、`AIServiceManagerCompat` 二次注册层、`ServiceInfo`、模块级 `ServiceManager.initialize()` 副作用、`get_service()`；瘦身为 `get_ai_service_manager()` 转发 + `DeprecationWarning`。
- `services/__init__.py` 同步移除 `ServiceManager` / `AIServiceManagerCompat` 的再导出映射。
- **BREAKING（内部）**：`services.service_manager.ServiceManager` / `ServiceInfo` / `get_service` 已移除（审计确认全项目零引用）。

## 3. 解说流水线 Phase 文件 (pipeline)

| 模块                                 | 状态    | 说明                                                                                 |
| ------------------------------------ | ------- | ------------------------------------------------------------------------------------ |
| `pipeline/narration_steps.py`        | 🟩 活跃 | Phase-1 骨架 step 注册器，被 `narration.py` 引用；phase2/3/4 在其基础上覆盖具体 step |
| `pipeline/narration_steps_phase2.py` | 🟩 活跃 | UNDERSTAND/STORYGRAPH/DRAFT 真实实现，含 API 缺失降级                                |
| `pipeline/narration_steps_phase3.py` | 🟩 活跃 | EVALUATE/HOOK_REWRITE 真实实现                                                       |
| `pipeline/narration_steps_phase4.py` | 🟩 活跃 | TTS_LENGTH_ADJUST/TTS/ASSEMBLE 真实实现                                              |

**结论**：这些**不是死代码**，不可删除。文件内的 `stub` 字样多指"运行时降级桩"（无 API key / 无 edge-tts 时的 fallback），并非待删占位符。

**P5 已完成**（2026-06-16）：
- 模块重命名：`narration_steps_phase2/3/4.py` → `understanding_steps.py` / `evaluation_steps.py` / `assembly_steps.py`（`git mv`，含对应测试文件）。`narration_steps.py`（Phase-1 骨架注册器）保留原名。
- 函数重命名：`register_phase2/3/4_steps` → `register_understanding/evaluation/assembly_steps`。
- 旧模块/函数名为内部 API，无外部消费方，未保留兼容别名。

## 4. 已在本轮删除 (v2.1.1)

- UI 旧组件树（`ui/components/**`、`ui/common/**` 等共 152 个文件，已 `git rm`）— 经全量 import 扫描确认无活动引用。
- 磁盘 `__pycache__` / `*.pyc` 生成物（已被 `.gitignore` 覆盖）。

## 5. FFmpeg 执行层 (P3，2026-06-16)

底座为 `utils/security.py` 的 `SecureExecutor`（`get_ffmpeg_executor()` 全局单例，命令白名单 `[ffmpeg, ffprobe]`）；`video_tools/ffmpeg_tool.FFmpegTool` 为业务便捷层。

本轮收编了所有**绕过安全层直接 `subprocess.run`** 的业务代码：

| 文件 | 原始直调 | 现在 |
|---|---|---|
| `pipeline/narration_steps_phase2.py` | `_probe_duration` 裸 ffprobe | `FFmpegTool.get_duration` |
| `pipeline/narration_steps_phase4.py` | 裸 ffprobe 时长 | `FFmpegTool.get_duration` |
| `services/video/session.py` | 裸 ffprobe info + ffmpeg 抽音 | `FFmpegTool.get_video_info` / `extract_audio`（新增 `sample_rate`/`channels`） |
| `services/video/processor.py` | 4 处裸 ffmpeg（cut/concat/add_audio/subclip） | `get_ffmpeg_executor().run`（专用命令保留，仅换执行入口） |
| `video_tools/ffmpeg_tool.py` | 硬件检测里裸 `ffmpeg -encoders` | `_ffmpeg_supports_encoder` 经执行器 |

**仍保留的裸 subprocess（合法）**：`core/ffmpeg_safe.py`(执行器自身) · `utils/security.py`(`SecureExecutor`) · `ffmpeg_tool.py` 的 `nvidia-smi`/`wmic`（非 ffmpeg 能力探测，不在白名单内）。

**双执行器合并（2026-06-16 后续完成）**：`core/ffmpeg_safe.SafeFFmpegCommand.execute()` 原有独立 `subprocess.run`，现委托 `utils.security.SecureExecutor`（统一底座）。`SafeFFmpegCommand` 保留声明式命令构建 + 校验 + `FFmpegResult`/审计封装，但不再持有第二条执行路径。`SecureExecutor` 将超时/失败包装为 `SecurityError`；`execute()` 按原契约还原（超时 → `TimeoutExpired`，非零 rc → `FFmpegResult(success=False)`）。

**仍未做**：硬件检测/ffprobe 元数据/命令构建未从 `FFmpegTool` 拆为独立模块。留待后续。

## 6. 并发与生命周期 (P4，2026-06-16)

- **事件总线生命周期**：`event_bus.EventBus` 新增 `close()`/`closed`（转发 `UnifiedEventBus.close()`）；`Application.shutdown()` 新增 `_shutdown_event_bus()`，在 `_cleanup()` 前统一释放投递线程池。投递路径本就非阻塞（单 handler 内联、多 handler `executor.submit + add_done_callback`），未改。
- **BatchProcessor 重写为 executor/future**：
  - 手写 `threading.Thread` + `queue.Queue` 生产者-消费者 → `ThreadPoolExecutor` + 每任务一个 `Future`。
  - `wait_until_done` 由 0.5s busy-poll → `concurrent.futures.wait(timeout)` 阻塞等待。
  - 新增**真超时**：`_execute_attempt` 用嵌套单发线程 + `result(timeout=task_timeout_sec)`（此前 `task_timeout_sec` 配置存在但从不生效）。底层 `pipeline.run` 不可中断，超时后后台守护线程自然结束。
  - **可取消退避**：重试 `time.sleep(backoff)` → `self._shutdown.wait(backoff)`，关闭时立即返回。
  - `shutdown()` 用 `executor.shutdown(cancel_futures=True)` 取消未开始任务。
  - 公开 API（`start`/`wait_until_done`/`shutdown`/`summary`/`pipeline_factory`/回调/checkpoint）保持不变。
- **PipelineEngine 不可变上下文（2026-06-16 后续完成，见 §9）**。

## 7. 命名规范化 (P5，2026-06-16)

- **phase 文件/函数重命名**（见 §3）。
- **文档版本修正**：`docs/guide/quick-start.md` / `installation.md` 的 `scenefab --version` 示例输出 `2.2.0` → `2.1.1`。ADR-007/006 中的 "v2.2" 指 narration 里程碑的设计记录，属历史文档，未改。
- **`.narrafiilm` 拼写修正（带向后兼容）**：P5 先将默认拼写从 `.narrafiilm` 改为 `.narrafilm`。**后续（见 §9）进一步统一为 `.scenefab`，与产品名一致。**
  - 内部符号 `_NarrafiilmVersion` → `_NarrafilmVersion`（后续再 → `_ProjectFileVersion`）。

## 9. 项目格式与配置目录统一为 .scenefab (2026-06-16)

将项目文件扩展名 / 配置目录从 `.narrafilm` 统一为 `.scenefab`，与产品名一致。**全程带向后兼容，不孤立既有用户文件/配置。**

- **项目文件扩展名**：`ProjectManager.PROJECT_EXTENSION = ".scenefab"`；`PROJECT_EXTENSIONS = [".scenefab", ".narrafilm", ".narrafiilm", ".vfproj"]`（新文件存 `.scenefab`，旧 `.narrafilm`/`.narrafiilm` 仍可加载）。`monologue_maker.save` 默认后缀同步为 `.scenefab`。
- **配置目录**：默认 `~/.scenefab`；新目录不存在但旧 `~/.narrafilm` / `~/.narrafiilm` 存在时，沿用最先命中的旧目录。
- **安全允许目录**：补 `~/.scenefab` + `/etc/scenefab`，保留旧路径。
- **内部符号**：`_NarrafilmVersion` → `_ProjectFileVersion`（产品中立命名，避免再次改名）；temp 前缀 `narrafilm_*` → `scenefab_*`。
- 测试：新增 `tests/test_pipeline_project_manager.py` 覆盖默认扩展名 + 旧扩展名保留可加载。
- **待移除**：旧 `.narrafilm` / `.narrafiilm` 扩展名与配置目录的兼容读取，建议 **v2.3.0** 一并移除。

## 8. 回归与交付门禁 (P6，2026-06-16)

整个 P0–P5 重构收尾的统一验收门禁，全部通过：

| 门禁 | 命令 | 结果 |
|---|---|---|
| ruff | `ruff check src/ tests/` | All checks passed |
| compileall | `python -m compileall src/scenefab tests` | OK |
| 核心全量 pytest（headless，零环境变量） | `python -m pytest` | 593 passed, 11 skipped |
| UI smoke test（venv + PySide6, offscreen） | `pytest tests/test_ui_main_window.py` | passed |
| 全量（venv，含 PySide6 + pytest-asyncio） | `pytest`（QT offscreen） | 629 passed, 10 skipped |

**11 处 headless skip 均可解释**：10 = 需真实 API key 的集成测试（QWEN/KIMI/GLM5），1 = UI 测试无 PySide6（CI/桌面镜像会跑）。venv 下 PySide6 就位后该 UI skip 消失、async 测试启用，故 +36 通过、skip 降至 10。

**P6 发现并修复的真实 bug**（UI smoke test 首次实例化主窗口暴露，见 commit `9409df6`）：
1. `QFont.Weight.SemiBold` 在 PySide6 不存在 → `DemiBold`（主窗口启动即崩）。
2. 自绘 `StatusBar(QFrame)` 传给 `QMainWindow.setStatusBar()`（要求 `QStatusBar`）→ 改入中央垂直布局底部。

**验收基线**：默认 `pytest` 无需 `PYTHONPATH=src`、无需 Qt binding、无需任何环境变量即可得到 593 passed 的可解释结果（P0 契约成立）。

## 9. PipelineEngine 不可变输入上下文 (2026-06-16)

`core/pipeline_engine.py` 原模型：调度器把共享可变 `context`（含被并发写的 `context["steps"]`）整体传给每个 `step.func`，step 内对 `steps` 的读不加锁，与其他并行 step 的写形成 race。

改为**不可变输入 + 中央归并**：
- 新增权威结果存储 `PipelineEngine._completed_outputs`（加锁写）。
- `_run_step_function` 给每个 step 传入一份输入视图，其中 `steps` 是当时已完成结果的只读快照（`MappingProxyType`）。step 依赖全部 COMPLETED 才 ready，故快照必含其依赖结果，语义不变。
- step 返回值由 `_postprocess_step_success` 集中归并到 `_completed_outputs`，不再写进 step 收到的 context。
- `run()` 末尾把 `_completed_outputs` 汇总进返回 `context["steps"]`，公开输出契约不变；`run()` 入口重置该存储以支持复用。

**BREAKING（内部）**：`step.func` 不能再写 `ctx["steps"]` 影响全局结果（写只读快照抛 `TypeError`）；下游只能读已完成依赖的结果快照。PipelineEngine 无生产调用方（仅 `test_core_v2.py`；`narration_state_machine.py` 中为 docstring 示例），故仅文档化。

---

## 移除流程约定

1. 标 🟥 的条目：下个小版本直接 `git rm` + 删除 `__init__` 再导出。
2. 标 🟧 的条目：保留 shim 至标注版本；shim 必须含 `DeprecationWarning`；到期版本删除并在 CHANGELOG 标注 BREAKING。
3. 删除前运行 P6 回归：`ruff` + `compileall` + 核心 `pytest`。
