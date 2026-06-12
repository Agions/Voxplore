---
title: ADR-007 解说生成状态机 — v2.2 核心流程重做
description: 视频解说生成从"线性编排器"进化为"上下文工程 + 状态机"流水线
category: architecture
version: 1.0
---

# ADR-007: 解说生成状态机 — v2.2 核心流程重做

- **状态**: 🟡 提案中
- **日期**: 2026-06-12
- **作者**: 架构团队
- **替代**: 无（叠加在 v2.0 + v2.1 之上）

## 背景

v2.0 (DAG 并行流水线) 和 v2.1 (单源真相 + 类型化事件 + DI) 解决了"性能 + 架构骨架"，但**视频解说生成的核心链路仍停留在 v1.x 的线性编排器模式**：

```python
# src/scenefab/services/video/monologue_maker.py (现状)
maker = MonologueMaker()
project = maker.create_project(video, context, emotion, ...)
maker.generate_script(project)        # 单次 LLM 调用
maker.generate_voice(project)         # Edge-TTS 顺序调用
maker.generate_captions(project)      # 字幕
maker.export_to_jianying(project, dir)
```

### 暴露的 5 大问题

调研 2025-2026 行业实践（火山引擎《高效视频理解新路径》、阿里《AI Agent 实战》、LangGraph 1.0 GA、华泰《2025 多模态大模型商业化进程》、中国文艺评论《2025 影视 AI 体系革新》），结合 scene-fab 现有 v2.1.1 用户的实际使用反馈（CHANGELOG + 测试覆盖），定位到：

1. **上下文断裂** — `ScriptGenerator` 拿到的是"场景列表 + 关键帧"，**没有剧情理解上下文**（谁是主角、起承转合、前文已说）。LLM 生成的解说稿容易"前后矛盾 + 重复叙述"。
2. **多版本无对比** — SPEC.md 承诺"每段生成 2-3 个版本供选择"，但实现是 `generate()` 单次返回。创作者横向择优做不到。
3. **短剧桥段未回灌** — `core/short_drama.py` 已实现 7 桥段识别（身份揭露/打脸/救场/背叛/心动/对峙/反转），但**没有反向回灌到 ScriptGenerator 的 prompt** → 文案生成时不会主动触发桥段。
4. **缺乏 Hook 优化** — 短视频"前 3 秒决定 80% 完播"，但当前没有"开场 Hook 改写"步骤。`viral/content_scorers.py` 有评分器但没接生成链路。
5. **音画时长误差累积** — 文案按"字数估算时长"对齐视频，**Edge-TTS 实际语速改变句子时长 200-500ms**，累积后音画不同步。

### 行业参照

| 来源 | 启示 |
|---|---|
| **LangGraph 1.0 GA**（Uber/LinkedIn/Klarna 已生产） | LLM 应用从 Chain 进化到 Cyclic Graph；"文案→评估→Hook 改写→再评估→接受/拒绝"是 LLM 应用的 2025 默认范式 |
| **华泰 2025 多模态报告** | 4 类上下文（指令/数据/历史/工具）决定 LLM 应用质量，比 prompt 长度更重要 |
| **火山引擎《高效视频理解新路径》** | "TTS 长度反馈压缩文案"消除 80% 音画不同步 |
| **PolyU VideoMind 2025** | 长视频多模态智能体要先建剧情图谱再生成 |
| **中国文艺评论 周雯 2025** | 影视 AI 进入"赛博工友"阶段，单 Agent 已能解决 90% 质量问题，多 Agent 留到 v3.x |

## 决策

**v2.2 在 v2.1 的 DAG 引擎之上，新增"解说生成状态机"层**，与现有 PipelineEngine 集成而非替换：

### 1. 引入 `NarrationStateMachine` 状态机

```
INGEST → UNDERSTAND → STORYGRAPH → DRAFT → HOOK_REWRITE
                                       ↑          │
                                       │          ↓
                                  REJECT ←─ EVALUATE → ACCEPT
                                                     │
                                                     ↓
                                              TTS_LENGTH_ADJUST → TTS → ASSEMBLE
```

实现位置：`src/scenefab/pipeline/narration_state_machine.py`（新增）

- 用 `enum + dataclass(slots=True)` 实现状态机
- 每个状态是一个 `Step` 函数 `(ctx: NarrationContext) -> StepResult`
- 状态转移由 `NarrationEvaluator` 决定（ACCEPT/REJECT 走 `core/unified_event_bus` 发 `NarrationStageChanged` 事件）
- 与 `core/pipeline_engine.py` 现有 DAG 引擎**集成**而非替换：状态机的每个 Node 就是一个 DAG Step

### 2. 4 类上下文（Context Engineering）

`src/scenefab/pipeline/narration_context.py`（新增）：

```python
@dataclass(slots=True)
class NarrationContext:
    # ① 指令上下文（人设 + 风格 + 平台）
    persona: Persona          # 短剧/电影/纪录片
    style: NarrationStyle    # 悬疑/甜宠/解说/吐槽...
    platform: Platform       # 抖音/B站 → 影响字数/语速

    # ② 数据上下文（剧情理解）
    story_graph: StoryGraph  # ← 来自 LongVideoUnderstanding（v2.2 打通！）
    scenes: list[SceneInfo]  # 当前集的场景列表
    bridges: list[Bridge]    # 短剧 7 桥段识别结果

    # ③ 历史上下文（防止重复/矛盾）
    history: list[Segment]   # 之前说过的桥段/角色名/关键剧情

    # ④ 工具上下文（Few-shot + 桥段模板）
    few_shots: list[FewShot] # 风格对应的范例
    bridge_templates: dict   # 7 桥段的 prompt 模板
```

### 3. 解说质量评估器 `NarrationEvaluator`

`src/scenefab/pipeline/narration_evaluator.py`（新增）：

用 **Qwen3.7-flash**（低成本）评估解说稿质量，5 项加权：

| 维度 | 权重 | 评估方式 |
|---|---|---|
| Hook 强度（前 2 句留人） | 25% | LLM judge + 关键词命中 |
| 桥段触发（短剧 7 桥段覆盖） | 20% | 与 `short_drama.detect_bridges()` 对齐 |
| 前后一致性（与 StoryGraph 对齐） | 20% | 角色名/剧情点重复检测 |
| 字数/语速/平台适配 | 20% | 硬规则（字数范围 + TTS 估算时长） |
| Few-shot 风格匹配 | 15% | Embedding 相似度 |

**决策**：`score ≥ 7.5` → ACCEPT；`< 7.5` → 回到 DRAFT（带 `suggestion` 注入 prompt），**最多重试 2 次**避免死循环。

### 4. TTS 反向约束文案（关键工程优化）

`HOOK_REWRITE` 后插入 `TTS_LENGTH_ADJUST` 状态：

1. 先 TTS 出 `voice_audio` + 真实时长 `t_real`
2. 算出实际配音时长
3. 调 LLM "把文案压缩/扩展到 `t_real ± 5%` 时长"
4. 再 TTS 一次

行业参考：这种"TTS 长度反馈"在短视频解说场景下能**消除 80% 的音画不同步**（火山引擎实战数据）。

### 5. 不引入 LangGraph

考虑过 LangGraph 但**否决**：

| 维度 | LangGraph | 自研状态机（v2.2 方案） |
|---|---|---|
| 依赖 | langchain-core + langgraph 50+ 间接依赖 | 0 新依赖（用现有 `unified_event_bus`） |
| 学习成本 | 团队需学 StateGraph API | Python 原生 enum + dataclass |
| 与现有 DAG 集成 | 需重写或包装 | 状态机的每个 Node 就是 DAG Step，天然集成 |
| 长期可维护 | LangChain 版本升级频繁 | scene-fab 内部 100% 可控 |

## 实施路径

| 阶段 | 范围 | 周期 | PR |
|---|---|---|---|
| Phase 0 | **本 ADR-007** | 0.5 天 | 单 PR (docs) |
| Phase 1 | `narration_context.py` + `narration_state_machine.py` 骨架 | 1.5 天 | 单 PR (feat) |
| Phase 2 | UNDERSTAND → STORYGRAPH → DRAFT 三状态 | 1.5 天 | 单 PR (feat) |
| Phase 3 | EVALUATE 评估器 + HOOK_REWRITE 循环 | 1.5 天 | 单 PR (feat) |
| Phase 4 | TTS_LENGTH_ADJUST 反向约束 | 1 天 | 单 PR (feat) |

**总计**: ~5-6 天 / 5 个 PR / 严格 mega-commit 单仓库风格（沿用 frame-fab/story-fab 已建立的偏好）

## 兼容性

- **零破坏**: 现有 `MonologueMaker.generate_script/voice/captions` 全部保留，状态机作为**可选增强路径**（`use_state_machine: bool = True`）
- **v1.x 公开 API**: 100% 兼容
- **配置层**: 新增 `[narration]` 配置组（`config_v2.py`），旧 `Settings` 字段不变

## 验证标准

1. **单元测试**: 状态机各状态转移条件正确（≥ 20 个用例）
2. **集成测试**: 完整跑通 1 部 30min 短剧 1 集，输出解说稿 + 配音 + 字幕 + 剪映草稿
3. **质量评估**: 与 v2.1 线性版本对比，5 维加权评分平均提升 ≥ 15%
4. **音画同步**: 字幕与配音时间戳偏差 ≤ 50ms 的片段占比 ≥ 90%
5. **CI**: ruff / mypy / pytest 全绿，新增测试零失败

## 不在 v2.2 范围

- ❌ 接入 World Model / 视频生成模型（2026 H1 一致性仍差）
- ❌ 多智能体协同（v3.x）
- ❌ 替换现有 MonologueMaker 完整流程（只增强不破坏）

## 关联

- **ADR-003**: 事件驱动 + IoC 容器架构（v2.2 复用 event_bus）
- **ADR-004**: DAG 并行 vs 串行流水线（v2.2 状态机集成到 DAG）
- **ADR-006**: v2.1 架构升级（v2.2 在其基础上叠加）
