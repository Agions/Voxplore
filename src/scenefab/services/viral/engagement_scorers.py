"""
SceneFab 互动与节奏评分混入

提供节奏匹配度和互动设计两个维度的评分计算方法。
"""

import logging
from typing import Any

from scenefab.services.viral.models import InteractionDesignScore, RhythmMatchScore

logger = logging.getLogger(__name__)


class EngagementScorersMixin:
    """互动与节奏评分混入类"""

    def _calculate_rhythm_match_score(
        self,
        rhythm_data: dict[str, Any],
        platform: str,
    ) -> RhythmMatchScore:
        """
        计算节奏匹配评分

        Args:
            rhythm_data: 节奏数据
            platform: 目标平台

        Returns:
            RhythmMatchScore: 节奏匹配评分
        """
        score = 50.0  # 基础分
        current_bpm = rhythm_data.get("bpm", 0)
        rhythm_type = rhythm_data.get("rhythm_type", "medium")
        suggestions = []

        # 获取平台最优 BPM
        platform_bpm = self.PLATFORM_OPTIMAL_BPM.get(platform, {})  # type: ignore[attr-defined]
        target_bpm = platform_bpm.get(rhythm_type, 100)

        # 计算匹配度
        if current_bpm > 0:
            bpm_diff = abs(current_bpm - target_bpm)
            match_ratio = max(0, 1 - bpm_diff / target_bpm)

            if match_ratio > 0.9:
                score += 30
            elif match_ratio > 0.7:
                score += 20
            elif match_ratio > 0.5:
                score += 10
            else:
                suggestions.append(f"建议调整节奏至 {target_bpm} BPM 左右")
        else:
            match_ratio = 0
            suggestions.append("未检测到节奏数据，建议提供 BPM 信息")

        # 限制最高分
        score = min(100, score)

        return RhythmMatchScore(
            score=score,
            current_bpm=current_bpm,
            target_bpm=target_bpm,
            rhythm_type=rhythm_type,
            match_ratio=match_ratio,
            suggestions=suggestions,
        )

    def _calculate_interaction_design_score(
        self, script_text: str
    ) -> InteractionDesignScore:
        """
        计算互动设计评分

        Args:
            script_text: 解说文案

        Returns:
            InteractionDesignScore: 互动设计评分
        """
        score = 50.0  # 基础分
        cta_count = 0
        cta_types = []
        question_count = 0
        open_ended_questions = []
        suggestions = []

        # 检测 CTA（行动号召）
        cta_patterns = {
            "like": ["点赞", "点个赞", "双击", "给个赞"],
            "share": ["分享", "转发", "告诉朋友"],
            "subscribe": ["关注", "订阅", "加入"],
            "comment": ["评论", "留言", "说说你的看法"],
        }

        for cta_type, keywords in cta_patterns.items():
            for keyword in keywords:
                if keyword in script_text:
                    cta_count += 1
                    cta_types.append(cta_type)
                    score += 10
                    break

        # 检测问题
        question_markers = ["？", "?", "吗", "呢", "吧"]
        for marker in question_markers:
            question_count += script_text.count(marker)

        # 检测开放式问题
        open_patterns = ["你觉得", "你认为", "你怎么看", "如果是你"]
        for pattern in open_patterns:
            if pattern in script_text:
                open_ended_questions.append(pattern)
                score += 5

        # 限制最高分
        score = min(100, score)

        # 生成建议
        if cta_count == 0:
            suggestions.append("建议在视频结尾添加行动号召（点赞/分享/关注）")
        if question_count == 0:
            suggestions.append("建议添加互动问题，引导用户评论")
        if not open_ended_questions:
            suggestions.append("建议添加开放式问题，如'你觉得呢？'")

        return InteractionDesignScore(
            score=score,
            cta_count=cta_count,
            cta_types=cta_types,
            question_count=question_count,
            open_ended_questions=open_ended_questions,
            suggestions=suggestions,
        )
