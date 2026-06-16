#!/usr/bin/env python3
"""
评估阶段 Step — 真实 EVALUATE / HOOK_REWRITE Step
(原 narration_steps_phase3，P5 重命名)

把骨架 stub + 理解阶段的简单 evaluate_step 替换为完整 5 维评估 + Hook 改写:

- evaluate_step   → 调 NarrationEvaluator.evaluate() 填充 ctx.eval_*
- hook_rewrite_step → 当 EVALUATE ACCEPT 后, 调用 LLM 改写开场 Hook
                     (生成 5 风格候选择优)

降级策略:
- 评估器: 永远可用 (5 维都是规则评分, 无 LLM 依赖)
- Hook 改写: 需 LLM, 失败时保留原 draft (Phase 1 行为)

v2.2 决策: docs/adr/007-narration-state-machine.md
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from .narration_context import (
    NarrationContext,
    NarrationStyle,
)
from .narration_state_machine import NarrationState, StepResult

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ============================================
# EVALUATE — 真实 5 维加权评估
# ============================================


def evaluate_step(ctx: NarrationContext) -> StepResult:
    """⑥ EVALUATE: 5 维加权评估 (Hook + 桥段 + 一致性 + 平台 + 风格)

    真实实现 (Phase 3):
    1. 调 NarrationEvaluator.evaluate(ctx)
    2. 填充 ctx.eval_score / ctx.eval_issues / ctx.eval_suggestion
    3. 不需要 LLM (5 维规则评分, 0 token 消耗)
    """
    start = time.time()

    try:
        from .narration_evaluator import NarrationEvaluator

        evaluator = NarrationEvaluator()
        result = evaluator.evaluate(ctx)

        # 填充 ctx
        ctx.eval_score = result.total_score
        ctx.eval_issues = result.issues
        ctx.eval_suggestion = result.suggestion

        duration_ms = (time.time() - start) * 1000
        return StepResult(
            success=True,
            state=NarrationState.EVALUATE,
            duration_ms=duration_ms,
            message=(
                f"evaluate: {result.total_score:.1f}/10 ({result.reason}), "
                f"{len(result.dimension_scores)} 维, "
                f"{len(result.issues)} issues"
            ),
            data={
                "total_score": result.total_score,
                "accept": result.accept,
                "dimension_scores": [
                    {
                        "name": d.name,
                        "score": d.score,
                        "weight": d.weight,
                        "issues": d.issues,
                    }
                    for d in result.dimension_scores
                ],
            },
        )
    except Exception as e:  # noqa: BLE001
        # 评估失败不应该阻塞状态机, 用最低分兜底
        logger.error(f"[{ctx.trace_id[:8]}] 评估器异常: {e}")
        ctx.eval_score = 5.0
        ctx.eval_issues = [f"评估器异常: {e}"]
        ctx.eval_suggestion = ""

        duration_ms = (time.time() - start) * 1000
        return StepResult(
            success=True,  # 评估器失败不阻塞, 给个低分
            state=NarrationState.EVALUATE,
            duration_ms=duration_ms,
            message=f"evaluate 异常降级: {e}",
            data={"fallback_score": 5.0},
        )


# ============================================
# HOOK_REWRITE — 开场 Hook 改写
# ============================================


# 5 种 Hook 改写风格，与评估器 Hook 关键词维度保持一致。
HOOK_REWRITE_STYLES: list[str] = ["conflict", "suspense", "result_first", "question", "shock"]


def hook_rewrite_step(ctx: NarrationContext) -> StepResult:
    """⑤ HOOK_REWRITE: 开场 Hook 改写 (前 2 句强化留人)

    真实实现 (Phase 3):
    1. 提取 ctx.current_draft 前 2 句
    2. 调 LLM 生成 5 种 Hook 风格候选 (conflict/suspense/...)
    3. 用 Phase 3 评估器 (Hook 维度) 选最佳
    4. 替换 draft 前 2 句

    降级: LLM 不可用 → 用规则生成 5 候选 + 评估器择优
    """
    start = time.time()

    if not ctx.current_draft:
        return StepResult(
            success=False,
            state=NarrationState.HOOK_REWRITE,
            error="current_draft 为空, 无法改写 Hook",
        )

    original_draft = ctx.current_draft
    original_hook = _extract_hook(original_draft)

    # 1. 生成 5 风格候选
    candidates: list[tuple[str, str]] = []  # (style_name, hook_text)
    try:
        candidates = _generate_hook_candidates_via_llm(ctx, original_hook)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"[{ctx.trace_id[:8]}] LLM Hook 改写失败, 降级规则: {e}"
        )
        candidates = _generate_hook_candidates_fallback(ctx, original_hook)

    if not candidates:
        # 极端降级: 保留原 draft
        duration_ms = (time.time() - start) * 1000
        return StepResult(
            success=True,
            state=NarrationState.HOOK_REWRITE,
            duration_ms=duration_ms,
            message="hook_rewrite: 候选为空, 保留原 draft",
            data={"candidates": 0, "kept_original": True},
        )

    # 2. 评估器打分选最佳
    best_hook, best_score, best_style = _select_best_hook(
        candidates, original_draft, ctx
    )

    # 3. 替换 draft 前 2 句
    new_draft = _replace_hook_in_draft(original_draft, best_hook)
    ctx.current_draft = new_draft

    duration_ms = (time.time() - start) * 1000
    return StepResult(
        success=True,
        state=NarrationState.HOOK_REWRITE,
        duration_ms=duration_ms,
        message=(
            f"hook_rewrite: 5 候选中选 '{best_style}' (Hook={best_score:.1f}/10), "
            f"draft {len(original_draft)} → {len(new_draft)} 字"
        ),
        data={
            "candidates": len(candidates),
            "best_style": best_style,
            "best_hook_score": best_score,
            "original_chars": len(original_draft),
            "new_chars": len(new_draft),
        },
    )


# ============================================
# 辅助函数
# ============================================


def _extract_hook(draft: str, max_chars: int = 60) -> str:
    """提取 draft 前 2 句作为 Hook (≤ 60 字)"""
    import re

    # 按 。！？ 切分前 2 句
    sentences = re.split(r"([。！？])", draft, maxsplit=4)
    # re.split 保留分隔符, 重组
    parts: list[str] = []
    for i in range(0, len(sentences) - 1, 2):
        parts.append(sentences[i] + sentences[i + 1])
    if len(sentences) % 2 == 1 and sentences[-1]:
        parts.append(sentences[-1])

    hook = "".join(parts[:2])  # 前 2 句
    if len(hook) > max_chars:
        hook = hook[:max_chars]
    return hook.strip()


def _generate_hook_candidates_via_llm(
    ctx: NarrationContext, original_hook: str
) -> list[tuple[str, str]]:
    """通过 LLM 生成 5 风格 Hook 候选

    返回 [(style_name, hook_text), ...]

    Raises:
        RuntimeError: LLM 不可用时
    """
    from scenefab.services.ai.script_generator import ScriptGenerator
    from scenefab.services.ai.script_models import ScriptConfig, ScriptStyle, VoiceTone

    style_to_script = {
        NarrationStyle.SUSPENSE: ScriptStyle.MONOLOGUE,
        NarrationStyle.ROMANCE: ScriptStyle.MONOLOGUE,
        NarrationStyle.REVENGE: ScriptStyle.COMMENTARY,
        NarrationStyle.UNDERDOG: ScriptStyle.COMMENTARY,
        NarrationStyle.COMEDY: ScriptStyle.VIRAL,
        NarrationStyle.LITERARY: ScriptStyle.NARRATION,
        NarrationStyle.NEUTRAL: ScriptStyle.COMMENTARY,
    }

    generator = ScriptGenerator()
    candidates: list[tuple[str, str]] = []

    # 单次调用让 LLM 一次生成 5 候选 (省 token)
    prompt = _build_hook_rewrite_prompt(ctx, original_hook)
    config = ScriptConfig(
        style=style_to_script.get(ctx.style, ScriptStyle.COMMENTARY),
        tone=VoiceTone.EXCITED,
        target_duration=5.0,  # Hook 只要 5s
        words_per_second=ctx.platform_spec.char_per_second,
        language="zh-CN",
        include_hook=True,
    )

    # 单次返回含 5 风格的脚本
    script = generator.generate(topic=prompt, config=config)
    # 解析 [STYLE:xxx] xxx 格式
    import re

    for match in re.finditer(
        r"\[STYLE:(\w+)\]\s*(.+?)(?=\[STYLE:|$)", script.content, re.DOTALL
    ):
        style_name = match.group(1)
        hook_text = match.group(2).strip()
        if style_name in HOOK_REWRITE_STYLES and hook_text:
            candidates.append((style_name, hook_text))

    if not candidates:
        raise RuntimeError("LLM 返回无法解析为 5 风格候选")

    return candidates


def _build_hook_rewrite_prompt(ctx: NarrationContext, original_hook: str) -> str:
    """构造 Hook 改写 prompt (5 风格一次生成)"""
    return f"""你是资深影视解说文案专家。请把以下开场 Hook 改写为 5 种风格, 每种 ≤ 30 字。

【原 Hook】
{original_hook}

【风格要求】
1. [STYLE:conflict] 冲突型 — 突出矛盾/对立 (如"没想到…", "然而…")
2. [STYLE:suspense] 悬念型 — 制造好奇/疑问 (如"真相是…", "背后隐藏…")
3. [STYLE:result_first] 结果前置 — 先抛结果/结局 (如"最后她…", "结局是…")
4. [STYLE:question] 提问型 — 设问引发思考 (如"为什么…", "怎么会…")
5. [STYLE:shock] 震惊型 — 强烈情绪冲击 (如"震惊!", "令人难以置信…")

【平台】{ctx.platform.value} (字数限制: Hook ≤ 30 字)
【风格基调】{ctx.style.value}

输出格式 (严格遵守, 用换行分隔):
[STYLE:conflict] <30 字以内>
[STYLE:suspense] <30 字以内>
[STYLE:result_first] <30 字以内>
[STYLE:question] <30 字以内>
[STYLE:shock] <30 字以内>"""


def _generate_hook_candidates_fallback(
    ctx: NarrationContext, original_hook: str
) -> list[tuple[str, str]]:
    """降级: 用规则模板生成 5 风格候选 (无 LLM)"""
    # 提取原 hook 的主体 (去掉句号)
    body = original_hook.rstrip("。！？.!?")[:30]
    if not body:
        body = "接下来我要讲的故事"

    candidates: list[tuple[str, str]] = [
        ("conflict", f"没想到, {body}的背后竟然如此反转。"),
        ("suspense", f"关于{body}, 真相可能跟你想的不一样。"),
        ("result_first", f"最后, {body}迎来了意料之外的结局。"),
        ("question", f"为什么{body}? 答案可能让你震惊。"),
        ("shock", f"震惊! {body}的真相竟然是这样。"),
    ]
    return candidates


def _select_best_hook(
    candidates: list[tuple[str, str]],
    original_draft: str,
    ctx: NarrationContext,
) -> tuple[str, float, str]:
    """从 5 候选中选 Hook 维度评分最高的

    Returns: (best_hook_text, best_hook_score, best_style_name)
    """
    from .narration_evaluator import NarrationEvaluator

    evaluator = NarrationEvaluator()
    best_hook = candidates[0][1]
    best_score = 0.0
    best_style = candidates[0][0]

    for style_name, hook_text in candidates:
        # 构造临时 draft (只替换 hook 评估)
        temp_draft = _replace_hook_in_draft(original_draft, hook_text)
        # 评估 hook 维度 (复用 Phase 3 评估器)
        # 简单做法: 用 evaluator._eval_hook
        hook_score = evaluator._eval_hook(temp_draft, ctx)
        score = hook_score.score

        if score > best_score:
            best_score = score
            best_hook = hook_text
            best_style = style_name

    return best_hook, best_score, best_style


def _replace_hook_in_draft(original_draft: str, new_hook: str) -> str:
    """把 new_hook 替换 original_draft 的前 2 句"""
    import re

    # 找到前 2 句的结束位置
    sentences = re.split(r"([。！？])", original_draft, maxsplit=4)
    parts: list[str] = []
    for i in range(0, len(sentences) - 1, 2):
        parts.append(sentences[i] + sentences[i + 1])
    if len(sentences) % 2 == 1 and sentences[-1]:
        parts.append(sentences[-1])

    # 前 2 句之后的剩余内容
    consumed_chars = sum(len(p) for p in parts[:2])
    rest = original_draft[consumed_chars:]

    # 拼接: new_hook + rest
    if not new_hook.endswith(("。", "！", "?")):
        new_hook += "。"
    return new_hook + rest


# ============================================
# 注册函数
# ============================================


def register_evaluation_steps(sm) -> None:
    """注册 Phase 3 真实实现 (替换 Phase 1+2 的 evaluate_step + hook_rewrite_step)

    使用示例:
        sm = NarrationStateMachine()
        register_default_steps(sm)
        register_understanding_steps(sm)
        register_evaluation_steps(sm)  # 替换 EVALUATE/HOOK_REWRITE
    """
    from .narration_state_machine import NarrationStateMachine

    assert isinstance(sm, NarrationStateMachine)

    sm.register_step(NarrationState.EVALUATE, evaluate_step)
    sm.register_step(NarrationState.HOOK_REWRITE, hook_rewrite_step)
