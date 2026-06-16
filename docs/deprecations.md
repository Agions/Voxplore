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

**结论**：这些**不是死代码**，不可删除。属于 **P5 命名规范化**范畴：

- `narration_steps_phase2.py` → `understanding_steps.py`
- `narration_steps_phase3.py` → `evaluation_steps.py`
- `narration_steps_phase4.py` → `assembly_steps.py`

文件内的 `stub` 字样多指"运行时降级桩"（无 API key / 无 edge-tts 时的 fallback），并非待删占位符。

## 4. 已在本轮删除 (v2.1.1)

- UI 旧组件树（`ui/components/**`、`ui/common/**` 等共 152 个文件，已 `git rm`）— 经全量 import 扫描确认无活动引用。
- 磁盘 `__pycache__` / `*.pyc` 生成物（已被 `.gitignore` 覆盖）。

---

## 移除流程约定

1. 标 🟥 的条目：下个小版本直接 `git rm` + 删除 `__init__` 再导出。
2. 标 🟧 的条目：保留 shim 至标注版本；shim 必须含 `DeprecationWarning`；到期版本删除并在 CHANGELOG 标注 BREAKING。
3. 删除前运行 P6 回归：`ruff` + `compileall` + 核心 `pytest`。
