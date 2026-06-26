---
title: ADR 007 解说状态机分阶段实现 (Phase 1/2/3/4)
status: Accepted
date: 2026-06-25
deciders: 何进, 喵酱
---

# ADR 007: 解说状态机分阶段实现

## 背景

SceneFab v2.2.0 引入了 `NarrationStateMachine`（见 `src/scenefab/pipeline/narration_state_machine.py`），
配套 11 个 Step 函数（见 `src/scenefab/pipeline/narration_steps.py`）覆盖从素材理解到剪映导出的全流程。

受限于 v2.2.0 PR #88 的范围（删除 ~15000 行死代码 + 收敛 5 个 LLM provider），**Phase 1 仅实现骨架，
8 个 Step 函数以"stub"形式返回 default 占位结果**——目的是先验证状态机流转，再分阶段接入真实实现。

## 决策

采用**四阶段渐进式实现**：

| Phase | 范围 | 触发条件 |
|---|---|---|
| **Phase 1 (v2.2.0 ✅)** | 11 个 Step 函数骨架, 状态机流转验证 | PR #88 合并 |
| **Phase 2** | UNDERSTAND / STORYGRAPH / DRAFT 真实接入 | SceneAnalyzer + LongVideoUnderstanding + DeepSeek-V4/Qwen3.7 LLM adapter 稳定后 |
| **Phase 3** | EVALUATE / HOOK_REWRITE 接入 | NarrationEvaluator 五维评分 + Hook 改写 LLM 评估稳定后 |
| **Phase 4** | TTS_LENGTH_ADJUST / TTS / ASSEMBLE 真实化 | TTS 长度自适应算法 + Edge-TTS 性能 + 剪映导出联调稳定后 |

## Phase 1 (当前 v2.2.0) stub 函数状态

**已真实实现** (4 个):

| Step | 函数 | 行为 |
|---|---|---|
| ① INGEST | `ingest_step` | 校验源视频 + 创建工作目录 |
| ④ DRAFT | `draft_step` | 模拟文案写入 `ctx.current_draft` (Phase 2 接 LLM) |
| ⑥ EVALUATE | `evaluate_step` | 默认 `eval_score=9.0` (Phase 3 接评估器) |
| ⑩ TTS | `tts_step` | Edge-TTS 真实调用 |
| ⑪ ASSEMBLE | `assemble_step` | 剪映草稿生成 |

**真 stub (Phase 2/3/4 接入)** (5 个):

| Step | 函数 | Phase | 接入目标 |
|---|---|---|---|
| ② UNDERSTAND | `understand_step` | Phase 2 | SceneAnalyzer |
| ③ STORYGRAPH | `storygraph_step` | Phase 2 | LongVideoUnderstanding |
| ⑤ HOOK_REWRITE | `hook_rewrite_step` | Phase 3 | LLM Hook 改写 |
| ⑦ ACCEPT / ⑧ REJECT | — | Phase 3 | 评估器决策 (待实现) |
| ⑨ TTS_LENGTH_ADJUST | `tts_length_adjust_step` | Phase 4 | TTS 长度自适应算法 |

## 后果

### 正面

- **状态机流转已验证**: Phase 1 让 11 个 Step 都能跑通 DAG, 验证 orchestration 正确
- **分阶段降低风险**: 每 Phase 独立可测可回滚, 不影响已稳定功能
- **stub 注释清晰**: 每个 stub 函数 docstring + message 都明确写"Phase N stub — Phase M 接入 X",
  读代码者不需要 grep 也能知道接入计划

### 负面

- **stub 行为对调用方有误导**: DRAFT 返回模拟文案, 下游 (TTS) 可能被喂假数据
- **测试覆盖率**: stub 函数测试是默认返回值断言, 不能验证真实逻辑
- **CHANGELOG 未记录分阶段计划**: v2.2.0 CHANGELOG 只写 "v2.2.0 骨架版", 未列 Phase 2/3/4 路线

### 缓解措施

1. **stub message 字段加 `data={"stub": True}`**: 调用方可通过 `result.data["stub"]` 判定
2. **DRAFT stub 显式标注 `[Phase 1 Stub]` 前缀**: 文案搜索可识别 stub
3. **新增 ROADMAP 速查块** (本 ADR): 集中索引 Phase 2/3/4 接入目标

## 备选方案

### 备选 A: v2.2.0 一次性实现全部 11 个 Step

**否决**: PR #88 范围已超 15000 行删除, 再加 11 个真实 Step 会让单 PR 不可审。
且多个上游模块 (SceneAnalyzer/LongVideoUnderstanding) 未稳定, 一次性接入风险高。

### 备选 B: 不实现骨架, 状态机直接等 Phase 2 一起做

**否决**: 状态机 orchestration 本身就需要验证, 没有 Step stub 跑不通 DAG。
且 Phase 2 多模块并行需要先稳定 orchestration 框架。

## 相关文档

- `src/scenefab/pipeline/narration_state_machine.py` — 状态机实现
- `src/scenefab/pipeline/narration_steps.py` — 11 个 Step 实现 (本 ADR 主体)
- `src/scenefab/pipeline/narration_context.py` — 上下文对象
- `docs/architecture.md` §"状态机流转" — 整体架构视角
- v2.2.0 CHANGELOG — PR #88 重构记录