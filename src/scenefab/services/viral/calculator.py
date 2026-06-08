"""
SceneFab 爆款评分计算器核心逻辑

基于五维模型（钩子、情绪曲线、信息密度、节奏匹配、互动设计）
评估视频的爆款潜力并生成综合评分。
"""

import logging
from typing import Any

from scenefab.services.viral.content_scorers import ContentScorersMixin
from scenefab.services.viral.engagement_scorers import EngagementScorersMixin
from scenefab.services.viral.models import ViralScoreResult

logger = logging.getLogger(__name__)


class ViralScoreCalculator(ContentScorersMixin, EngagementScorersMixin):
    """
    爆款评分计算器

    基于五维模型评估视频的爆款潜力。

    使用方法：
        calculator = ViralScoreCalculator()
        result = calculator.calculate(
            script_text="解说文案...",
            emotion_data=[...],
            rhythm_data={...},
            platform="douyin",
        )
        print(f"总分: {result.total_score}")
        print(f"等级: {result.grade}")
    """

    # 五维权重
    WEIGHTS = {
        "hook": 0.30,
        "emotion_curve": 0.25,
        "information_density": 0.20,
        "rhythm_match": 0.15,
        "interaction_design": 0.10,
    }

    # 等级阈值
    GRADE_THRESHOLDS = {
        "S": 90,
        "A": 80,
        "B": 70,
        "C": 60,
        "D": 0,
    }

    # 平台最优 BPM
    PLATFORM_OPTIMAL_BPM = {
        "douyin": {"fast": 140, "medium": 110, "slow": 80},
        "bilibili": {"fast": 130, "medium": 100, "slow": 70},
        "xiaohongshu": {"fast": 120, "medium": 90, "slow": 60},
        "youtube": {"fast": 130, "medium": 100, "slow": 70},
        "tiktok": {"fast": 140, "medium": 110, "slow": 80},
    }

    def __init__(self, llm_provider=None):
        """
        初始化爆款评分计算器

        Args:
            llm_provider: LLM 提供商（用于文案分析）
        """
        self.llm_provider = llm_provider
        logger.info("ViralScoreCalculator 初始化完成")

    def calculate(
        self,
        script_text: str,
        emotion_data: list[dict[str, Any]] | None = None,
        rhythm_data: dict[str, Any] | None = None,
        platform: str = "douyin",
        video_duration: float = 0,
    ) -> ViralScoreResult:
        """
        计算爆款评分

        Args:
            script_text: 解说文案
            emotion_data: 情绪数据
            rhythm_data: 节奏数据
            platform: 目标平台
            video_duration: 视频时长（秒）

        Returns:
            ViralScoreResult: 评分结果
        """
        logger.info(f"开始计算爆款评分，平台: {platform}")

        # 1. 开篇钩子评分
        hook_score = self._calculate_hook_score(script_text, platform)

        # 2. 情绪曲线评分
        emotion_curve_score = self._calculate_emotion_curve_score(
            emotion_data or [], video_duration
        )

        # 3. 信息密度评分
        information_density_score = self._calculate_information_density_score(
            script_text, video_duration
        )

        # 4. 节奏匹配评分
        rhythm_match_score = self._calculate_rhythm_match_score(
            rhythm_data or {}, platform
        )

        # 5. 互动设计评分
        interaction_design_score = self._calculate_interaction_design_score(
            script_text
        )

        # 计算总分
        total_score = (
            hook_score.score * self.WEIGHTS["hook"]
            + emotion_curve_score.score * self.WEIGHTS["emotion_curve"]
            + information_density_score.score * self.WEIGHTS["information_density"]
            + rhythm_match_score.score * self.WEIGHTS["rhythm_match"]
            + interaction_design_score.score * self.WEIGHTS["interaction_design"]
        )

        # 确定等级
        grade = self._determine_grade(total_score)

        # 生成建议
        recommendations = self._generate_recommendations(
            hook_score,
            emotion_curve_score,
            information_density_score,
            rhythm_match_score,
            interaction_design_score,
            grade,
        )

        result = ViralScoreResult(
            total_score=round(total_score, 2),
            hook_score=hook_score,
            emotion_curve_score=emotion_curve_score,
            information_density_score=information_density_score,
            rhythm_match_score=rhythm_match_score,
            interaction_design_score=interaction_design_score,
            grade=grade,
            recommendations=recommendations,
        )

        logger.info(f"爆款评分计算完成: 总分={total_score:.2f}, 等级={grade}")
        return result

    def _determine_grade(self, total_score: float) -> str:
        """
        确定等级

        Args:
            total_score: 总分

        Returns:
            str: 等级
        """
        for grade, threshold in self.GRADE_THRESHOLDS.items():
            if total_score >= threshold:
                return grade
        return "D"

    def _generate_recommendations(
        self,
        hook_score,
        emotion_curve_score,
        information_density_score,
        rhythm_match_score,
        interaction_design_score,
        grade: str,
    ) -> list[str]:
        """
        生成建议

        Args:
            hook_score: 钩子评分
            emotion_curve_score: 情绪曲线评分
            information_density_score: 信息密度评分
            rhythm_match_score: 节奏匹配评分
            interaction_design_score: 互动设计评分
            grade: 等级

        Returns:
            list: 建议列表
        """
        recommendations = []

        # 整体建议
        if grade == "S":
            recommendations.append("🎉 优秀！这是一个高潜力爆款视频")
        elif grade == "A":
            recommendations.append("👍 良好！视频质量较高，有爆款潜力")
        elif grade == "B":
            recommendations.append("✅ 中等！视频质量尚可，建议优化以下方面")
        else:
            recommendations.append("⚠️ 需要改进！建议重点关注以下方面")

        # 各维度建议
        all_suggestions = []
        all_suggestions.extend(hook_score.suggestions)
        all_suggestions.extend(emotion_curve_score.suggestions)
        all_suggestions.extend(information_density_score.suggestions)
        all_suggestions.extend(rhythm_match_score.suggestions)
        all_suggestions.extend(interaction_design_score.suggestions)

        # 去重并添加
        seen = set()
        for suggestion in all_suggestions:
            if suggestion not in seen:
                recommendations.append(suggestion)
                seen.add(suggestion)

        return recommendations


def calculate_viral_score(
    script_text: str,
    emotion_data: list[dict[str, Any]] | None = None,
    rhythm_data: dict[str, Any] | None = None,
    platform: str = "douyin",
    video_duration: float = 0,
    llm_provider=None,
) -> ViralScoreResult:
    """
    便捷函数：计算爆款评分

    Args:
        script_text: 解说文案
        emotion_data: 情绪数据
        rhythm_data: 节奏数据
        platform: 目标平台
        video_duration: 视频时长
        llm_provider: LLM 提供商

    Returns:
        ViralScoreResult: 评分结果
    """
    calculator = ViralScoreCalculator(llm_provider=llm_provider)
    return calculator.calculate(
        script_text=script_text,
        emotion_data=emotion_data,
        rhythm_data=rhythm_data,
        platform=platform,
        video_duration=video_duration,
    )
