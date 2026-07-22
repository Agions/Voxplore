#!/usr/bin/env python3
"""
v2.2 Phase 3 — NarrationEvaluator 5 维加权评估器

按 ADR-007 设计的 5 维评估 (Hook 25% + 桥段 20% + 一致性 20% + 适配 20% + 风格 15%):
- 总分 0-10, ≥ 7.5 接受 (ACCEPT), 否则拒绝 (REJECT)
- 所有维度均为轻量规则评分, 0 网络依赖
- 降级: LLM judge 失败 → 用硬规则评估

设计原则:
- 0 LLM 调用 (5 维都是规则评分), 评估本身不消耗 token
- 短剧连续生产时强制检查题材标签、人物关系和下一集钩子

v2.2 决策: docs/adr/007-narration-state-machine.md
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from ..fp_workflow import FIRST_PERSON_QUALITY_GATES
from .context import (
    BridgeType,
    NarrationContext,
)

logger = logging.getLogger(__name__)


# ============================================
# 5 维评分数据类
# ============================================


@dataclass(slots=True)
class DimensionScore:
    """单维度评分 (0-10)"""

    name: str  # "hook" / "bridge" / "consistency" / "platform" / "style"
    score: float  # 0-10
    weight: float  # 0-1 (本维度在总分中的权重)
    issues: list[str] = field(default_factory=list)  # 具体问题描述
    suggestions: list[str] = field(default_factory=list)  # 改写建议

    @property
    def weighted(self) -> float:
        """加权后的分数"""
        return self.score * self.weight


@dataclass(slots=True)
class EvalResult:
    """5 维加权评估结果"""

    total_score: float  # 0-10 加权总分
    dimension_scores: list[DimensionScore] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)  # 全部问题汇总
    suggestion: str = ""  # 改写总建议 (注入下一轮 DRAFT 的 prompt)
    accept: bool = False  # 总分达到接受阈值时为 True
    reason: str = ""  # 决策原因

    def __post_init__(self) -> None:
        if not self.reason:
            self.reason = (
                f"总分 {self.total_score:.1f} → {'ACCEPT' if self.accept else 'REJECT'}"
            )


# ============================================
# 维度权重 (ADR-007 锁定)
# ============================================


# 总和必须 = 1.0
DIMENSION_WEIGHTS: dict[str, float] = {
    "hook": 0.25,  # 前 2 句留人 — Hook 强度
    "bridge": 0.20,  # 短剧 7 桥段覆盖
    "consistency": 0.20,  # 与 StoryGraph 一致性
    "platform": 0.20,  # 字数/语速/平台适配
    "style": 0.15,  # Few-shot 风格匹配
}


# ============================================
# 评估器主体
# ============================================


class NarrationEvaluator:
    """v2.2 解说稿质量评估器

    使用示例:
        evaluator = NarrationEvaluator()
        result = evaluator.evaluate(ctx)
        if result.accept:
            # ACCEPT → 继续 HOOK_REWRITE
        else:
            # REJECT → 回到 DRAFT, 注入 result.suggestion
    """

    def __init__(self, accept_threshold: float = 7.5) -> None:
        """
        Args:
            accept_threshold: 总分接受阈值 (默认 7.5, 与
                NarrationConfig.eval_accept_threshold 默认值一致)
        """
        self.accept_threshold = accept_threshold

    def evaluate(self, ctx: NarrationContext) -> EvalResult:
        """5 维加权评估当前 ctx.current_draft

        Args:
            ctx: 解说上下文 (含 current_draft / scenes / bridges / story_graph / few_shots)

        Returns:
            EvalResult: 总分 + 5 维分 + 问题 + 建议 + accept 决策
        """
        draft = ctx.current_draft
        if not draft:
            return EvalResult(
                total_score=0.0,
                accept=False,
                reason="无 draft 可评估",
                issues=["current_draft 为空"],
                suggestion="需要先生成初稿",
            )

        # 1. 5 维并行评估
        hook_score = self._eval_hook(draft, ctx)
        bridge_score = self._eval_bridge(draft, ctx)
        consistency_score = self._eval_consistency(draft, ctx)
        platform_score = self._eval_platform(draft, ctx)
        style_score = self._eval_style(draft, ctx)

        dimensions = [
            hook_score,
            bridge_score,
            consistency_score,
            platform_score,
            style_score,
        ]

        # 2. 加权总分
        total = sum(d.weighted for d in dimensions)

        # 3. 汇总 issues + suggestion
        all_issues: list[str] = []
        all_suggestions: list[str] = []
        for d in dimensions:
            all_issues.extend(d.issues)
            all_suggestions.extend(d.suggestions)

        # 4. 决策
        threshold = self.accept_threshold
        accept = total >= threshold

        # 5. 组装总建议
        suggestion = self._build_suggestion(dimensions, ctx) if not accept else ""

        return EvalResult(
            total_score=total,
            dimension_scores=dimensions,
            issues=all_issues,
            suggestion=suggestion,
            accept=accept,
            reason=f"总分 {total:.1f} {'≥' if accept else '<'} {threshold}",
        )

    # ============================================================
    # 维度 1: Hook 强度 (25%)
    # ============================================================

    def _eval_hook(self, draft: str, ctx: NarrationContext) -> DimensionScore:
        """Hook 强度: 前 30 字符是否包含冲突、悬念、结果前置等信号。"""
        issues: list[str] = []
        suggestions: list[str] = []

        score = self._score_hook_keywords(draft)
        if score < 6.0:
            issues.append("Hook 缺少冲突/悬念/结果前置关键词")
            suggestions.append("前 2 句加入'没想到'/'真相是'/'最后一刻'等钩子词")
        score = self._apply_first_person_hook_gate(
            score, draft, ctx, issues, suggestions
        )

        return DimensionScore(
            name="hook",
            score=score,
            weight=DIMENSION_WEIGHTS["hook"],
            issues=issues,
            suggestions=suggestions,
        )

    def _score_hook_keywords(self, draft: str) -> float:
        """Hook 评分: 前 30 字符含钩子关键词数。"""
        if not draft:
            return 0.0
        first_30 = draft.split("\n", 1)[0][:30]

        # 钩子关键词 (与 v2.1 _HOOK_PATTERNS 对齐)
        keywords = {
            "conflict": ["没想到", "竟然", "居然", "突然", "意外", "但是", "然而"],
            "suspense": ["秘密", "真相", "背后", "隐藏", "谜团", "悬念", "最后"],
            "result_first": ["结局", "最后", "最终", "结果", "后来"],
            "question": ["为什么", "怎么", "如何", "是什么", "哪里", "谁"],
            "shock": ["震惊", "可怕", "恐怖", "惊人", "难以置信"],
        }

        hits = 0
        for kws in keywords.values():
            if any(kw in first_30 for kw in kws):
                hits += 1

        # 5 钩子类型, 命中 1 个 = 6 分, 2 个 = 8 分, 3+ = 10 分
        return min(10.0, 4.0 + hits * 2.0)

    # ============================================================
    # 维度 2: 桥段触发 (20%)
    # ============================================================

    def _eval_bridge(self, draft: str, ctx: NarrationContext) -> DimensionScore:
        """桥段触发: 检查 draft 是否反映 ctx.bridges 中的桥段关键词

        评分: 触发的桥段数 / 总桥段数 * 10
        """
        issues: list[str] = []
        suggestions: list[str] = []

        bridges = ctx.bridges
        if not bridges:
            # 无桥段要求 → 默认 8 分 (不扣分)
            return DimensionScore(
                name="bridge",
                score=8.0,
                weight=DIMENSION_WEIGHTS["bridge"],
                issues=[],
                suggestions=[],
            )

        # 桥段 → 关键词映射
        bridge_keywords: dict[BridgeType, list[str]] = {
            BridgeType.IDENTITY_REVEAL: [
                "身份",
                "真实",
                "原来",
                "太子",
                "总裁",
                "boss",
                "真凶",
            ],
            BridgeType.SLAP_FACE: [
                "打脸",
                "碾压",
                "跪",
                "认错",
                "求饶",
                "道歉",
                "后悔",
            ],
            BridgeType.RESCUE: ["救", "从天而降", "及时赶到", "英雄救美", "出手"],
            BridgeType.BETRAYAL: ["背叛", "出卖", "背后捅刀", "陷害", "污蔑"],
            BridgeType.HEART_FLUTTER: [
                "告白",
                "亲吻",
                "拥抱",
                "心动",
                "脸红",
                "壁咚",
                "公主抱",
            ],
            BridgeType.CONFRONTATION: ["对峙", "质问", "怒斥", "指责", "对质"],
            BridgeType.PLOT_TWIST: ["反转", "真相", "竟然", "万万没想到", "大跌眼镜"],
        }

        triggered = 0
        for bridge in bridges:
            kws = bridge_keywords.get(bridge.bridge_type, [])
            if any(kw in draft for kw in kws):
                triggered += 1
            else:
                issues.append(f"未触发桥段: {bridge.bridge_type.value}")
                # 给出改写建议
                if kws:
                    suggestions.append(
                        f"建议在 {bridge.bridge_type.value} 处加入: {'/'.join(kws[:3])}"
                    )

        # 触发率 → 0-10 分
        trigger_rate = triggered / len(bridges) if bridges else 1.0
        score = trigger_rate * 10.0
        score = self._apply_content_tag_gate(score, draft, ctx, issues, suggestions)

        return DimensionScore(
            name="bridge",
            score=score,
            weight=DIMENSION_WEIGHTS["bridge"],
            issues=issues,
            suggestions=suggestions,
        )

    # ============================================================
    # 维度 3: 前后一致性 (20%)
    # ============================================================

    def _eval_consistency(self, draft: str, ctx: NarrationContext) -> DimensionScore:
        """前后一致性: 角色名/剧情点是否与 story_graph + history 对齐

        评分: 一致项 / 总项 * 10 (缺数据时默认 8 分)
        """
        issues: list[str] = []
        suggestions: list[str] = []

        if not ctx.story_graph or not ctx.story_graph.characters:
            return DimensionScore(
                name="consistency",
                score=8.0,
                weight=DIMENSION_WEIGHTS["consistency"],
            )

        # 1. 角色名一致性
        char_names = [c.name for c in ctx.story_graph.characters if c.name]
        mentioned_chars = [n for n in char_names if n in draft]

        if char_names:
            mention_rate = len(mentioned_chars) / len(char_names)
        else:
            mention_rate = 1.0

        # 2. 与 history 的角色不重复
        if ctx.history:
            # 当前 draft 提到了历史角色, 不扣分 (应该提)
            for char in char_names:
                if char not in draft:
                    issues.append(f"主要角色 '{char}' 未在文案中提及")
                    suggestions.append(f"考虑在合适场景提及角色 '{char}'")

        # 3. plot_events 至少 1 个相关
        if ctx.story_graph.plot_events:
            plot_keywords: list[str] = []
            for evt in ctx.story_graph.plot_events[:3]:
                if evt.description:
                    # 提取关键中文词 (2-4 字)
                    plot_keywords.extend(
                        re.findall(r"[\u4e00-\u9fa5]{2,4}", evt.description)[:5]
                    )
            if plot_keywords:
                plot_hits = sum(1 for kw in plot_keywords if kw in draft)
                if plot_hits == 0:
                    issues.append("文案未体现 StoryGraph 中的关键剧情点")
                    suggestions.append(
                        f"建议加入剧情关键词: {'/'.join(plot_keywords[:3])}"
                    )

        # 评分: 0.7 * 角色提及率 + 0.3 * 剧情体现 (粗略)
        score = 10.0 * (0.7 * mention_rate + 0.3)
        if not issues:
            score = min(10.0, score + 0.5)  # 无问题小奖励
        score = self._apply_relationship_gate(score, draft, ctx, issues, suggestions)

        return DimensionScore(
            name="consistency",
            score=score,
            weight=DIMENSION_WEIGHTS["consistency"],
            issues=issues,
            suggestions=suggestions,
        )

    # ============================================================
    # 维度 4: 字数/语速/平台适配 (20%)
    # ============================================================

    def _eval_platform(self, draft: str, ctx: NarrationContext) -> DimensionScore:
        """平台适配: 字数 / 语速 / 平台规格

        评分规则:
        - 字数在 [0.7 * target, 1.3 * target] → 10 分
        - 字数偏离 ±30% → 8 分
        - 字数偏离 ±50% → 5 分
        - 极端偏离 → 2 分
        """
        issues: list[str] = []
        suggestions: list[str] = []

        char_count = len(draft)
        spec = ctx.platform_spec
        target_chars = int(spec.char_per_second * spec.target_duration_sec)

        if target_chars == 0:
            return DimensionScore(
                name="platform",
                score=5.0,
                weight=DIMENSION_WEIGHTS["platform"],
                issues=["平台规格未配置"],
            )

        # 计算偏离度
        ratio = char_count / target_chars
        deviation = abs(ratio - 1.0)  # 0=完美, 0.3=偏离 30%

        if deviation <= 0.15:  # ±15%
            score = 10.0
        elif deviation <= 0.30:  # ±30%
            score = 8.0
        elif deviation <= 0.50:  # ±50%
            score = 5.0
        else:
            score = 2.0

        # 详细 issues
        if ratio > 1.3:
            issues.append(
                f"文案过长 ({char_count} 字, 目标 {target_chars} 字, "
                f"超出 {(ratio - 1) * 100:.0f}%)"
            )
            suggestions.append(
                f"建议压缩到 {int(target_chars * 0.9)}-{target_chars} 字"
            )
        elif ratio < 0.7:
            issues.append(
                f"文案过短 ({char_count} 字, 目标 {target_chars} 字, "
                f"缺少 {(1 - ratio) * 100:.0f}%)"
            )
            suggestions.append(
                f"建议扩展到 {target_chars}-{int(target_chars * 1.1)} 字"
            )

        # Hook 字符数检查
        first_line = draft.split("\n", 1)[0] if draft else ""
        if len(first_line) < spec.min_hook_chars * 0.5:
            issues.append(
                f"Hook 过短 ({len(first_line)} 字, 建议 ≥ {spec.min_hook_chars} 字)"
            )
            suggestions.append(f"开场前 {spec.min_hook_chars} 字内应包含强钩子")

        return DimensionScore(
            name="platform",
            score=score,
            weight=DIMENSION_WEIGHTS["platform"],
            issues=issues,
            suggestions=suggestions,
        )

    # ============================================================
    # 维度 5: Few-shot 风格匹配 (15%)
    # ============================================================

    def _eval_style(self, draft: str, ctx: NarrationContext) -> DimensionScore:
        """风格匹配: 与 ctx.few_shots 关键词重合度

        评分: 重合词数 / 风格关键词数 * 10
        """
        issues: list[str] = []
        suggestions: list[str] = []

        if not ctx.few_shots:
            # 无 few_shots → 默认 8 分
            score = self._apply_next_hook_gate(8.0, draft, ctx, issues, suggestions)
            score = self._apply_first_person_viewpoint_gate(
                score, draft, ctx, issues, suggestions
            )
            return DimensionScore(
                name="style",
                score=score,
                weight=DIMENSION_WEIGHTS["style"],
                issues=issues,
                suggestions=suggestions,
            )

        # 提取 few_shots 风格关键词
        style_words: set[str] = set()
        for fs in ctx.few_shots:
            if fs.style != ctx.style:
                continue  # 只匹配当前风格的 few_shot
            # 提取 2-4 字中文词
            words = re.findall(r"[\u4e00-\u9fa5]{2,4}", fs.narration)
            style_words.update(words[:10])

        if not style_words:
            return DimensionScore(
                name="style",
                score=8.0,
                weight=DIMENSION_WEIGHTS["style"],
            )

        # 命中统计
        hits = sum(1 for w in style_words if w in draft)
        hit_rate = hits / len(style_words) if style_words else 0
        score = min(10.0, hit_rate * 20.0)  # 5% 命中 = 1 分, 50% = 10 分

        if score < 6.0:
            issues.append(
                f"风格匹配度低 ({score:.1f}/10, 命中 {hits}/{len(style_words)} 关键词)"
            )
            suggestions.append(f"建议融入风格关键词: {'/'.join(list(style_words)[:5])}")
        score = self._apply_next_hook_gate(score, draft, ctx, issues, suggestions)
        score = self._apply_first_person_viewpoint_gate(
            score, draft, ctx, issues, suggestions
        )

        return DimensionScore(
            name="style",
            score=score,
            weight=DIMENSION_WEIGHTS["style"],
            issues=issues,
            suggestions=suggestions,
        )

    # ============================================================
    # 工具
    # ============================================================

    def _is_short_drama_production(self, ctx: NarrationContext) -> bool:
        """是否进入连续短剧生产语境。"""
        return (
            ctx.short_drama_style is not None
            or ctx.episode_index is not None
            or bool(ctx.content_tags)
            or bool(ctx.relationship_notes)
            or bool(ctx.previous_episode_summary)
            or bool(ctx.next_hook_hint)
        )

    def _apply_first_person_hook_gate(
        self,
        score: float,
        draft: str,
        ctx: NarrationContext,
        issues: list[str],
        suggestions: list[str],
    ) -> float:
        if not self._is_short_drama_production(ctx):
            return score

        opening = draft.split("\n", 1)[0][:30]
        first_person_terms = ("我", "我的", "我被", "我要", "我想", "我怕")
        trigger_terms = (
            "想要",
            "必须",
            "失去",
            "危机",
            "危险",
            "真相",
            "结果",
            "结局",
            "代价",
            "反转",
            "复仇",
            "逆袭",
            "活下去",
            "救",
        )
        has_viewpoint = any(term in opening for term in first_person_terms)
        has_trigger = any(term in opening for term in trigger_terms)

        if has_viewpoint and has_trigger:
            return score

        issues.append(f"第一人称 Hook 未满足: {FIRST_PERSON_QUALITY_GATES[0]}")
        suggestions.append("3 秒内用我视角交代我是谁、我要什么、我会失去什么")
        return min(score, 6.5)

    def _apply_content_tag_gate(
        self,
        score: float,
        draft: str,
        ctx: NarrationContext,
        issues: list[str],
        suggestions: list[str],
    ) -> float:
        if not self._is_short_drama_production(ctx):
            return score
        if not ctx.content_tags:
            issues.append("短剧生产缺少题材/爽点标签")
            suggestions.append("补充重生/复仇/甜宠/逆袭等题材标签并写入桥段表达")
            return min(score, 6.5)
        if not self._contains_context_terms(draft, ctx.content_tags):
            issues.append("文案未体现短剧题材/爽点标签")
            suggestions.append(
                f"建议显式承接爽点标签: {'/'.join(ctx.content_tags[:3])}"
            )
            return max(0.0, score - 1.5)
        return score

    def _apply_relationship_gate(
        self,
        score: float,
        draft: str,
        ctx: NarrationContext,
        issues: list[str],
        suggestions: list[str],
    ) -> float:
        if not self._is_short_drama_production(ctx):
            return score
        if not ctx.relationship_notes:
            issues.append("短剧生产缺少人物关系说明")
            suggestions.append("补充主角、反派、盟友和情感/利益冲突关系")
            return min(score, 6.5)
        if not self._contains_context_terms(draft, ctx.relationship_notes):
            issues.append("文案未承接人物关系说明")
            suggestions.append("在文案中明确角色关系和冲突立场")
            return max(0.0, score - 1.5)
        return score

    def _apply_next_hook_gate(
        self,
        score: float,
        draft: str,
        ctx: NarrationContext,
        issues: list[str],
        suggestions: list[str],
    ) -> float:
        if not self._is_short_drama_production(ctx):
            return score
        if not ctx.next_hook_hint:
            issues.append("短剧生产缺少下一集钩子提示")
            suggestions.append("补充下一集反转、真凶、误会或后果提示")
            return min(score, 6.5)

        tail = draft[-100:]
        if not self._contains_context_terms(tail, [ctx.next_hook_hint]):
            issues.append("结尾未承接下一集钩子")
            suggestions.append("在最后 1-2 句植入下一集悬念")
            return max(0.0, score - 1.5)
        return score

    def _apply_first_person_viewpoint_gate(
        self,
        score: float,
        draft: str,
        ctx: NarrationContext,
        issues: list[str],
        suggestions: list[str],
    ) -> float:
        if not self._is_short_drama_production(ctx):
            return score

        first_person_hits = len(re.findall(r"我(?:的|被|要|想|怕|会|才|也)?", draft))
        if first_person_hits >= 2:
            return score

        issues.append(f"第一人称视角不稳定: {FIRST_PERSON_QUALITY_GATES[2]}")
        suggestions.append("改成稳定我视角, 明确我是谁、我想要什么、我怕失去什么")
        return min(score, 6.5)

    def _contains_context_terms(self, text: str, values: list[str]) -> bool:
        terms: set[str] = set()
        for value in values:
            normalized = value.strip()
            if not normalized:
                continue
            terms.add(normalized)
            terms.update(re.findall(r"[\u4e00-\u9fa5A-Za-z0-9]{2,8}", normalized))
        return any(term in text for term in terms)

    def _build_suggestion(
        self,
        dimensions: list[DimensionScore],
        ctx: NarrationContext,
    ) -> str:
        """汇总各维度 suggestions, 组装成下一轮 DRAFT 的 prompt 注入"""
        lines: list[str] = []
        lines.append("【v2.2 评估反馈 (待改进)】")

        for d in dimensions:
            if d.score < 7.5 and d.suggestions:
                lines.append(f"### {d.name} ({d.score:.1f}/10)")
                for sug in d.suggestions[:2]:
                    lines.append(f"- {sug}")

        if len(lines) == 1:
            lines.append("整体表现良好, 但有改进空间")

        return "\n".join(lines)
