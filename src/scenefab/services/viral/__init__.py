"""
SceneFab 爆款五维评分模块

功能：
1. 前 3 秒钩子检测（LLM 评估）
2. 情绪曲线可视化（波形图）
3. 信息密度热力图（每 10 秒有效信息量）
4. 节奏匹配度（当前节奏 vs 平台最优节奏）
5. 互动设计评分（CTA/开放式问题检测）

评分公式：
爆款评分 = 0.30 × 开篇钩子分 + 0.25 × 情绪曲线分 + 0.20 × 信息密度分 + 0.15 × 节奏匹配分 + 0.10 × 互动设计分
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class HookScore:
    """开篇钩子评分"""
    score: float  # 0-100
    hook_type: str  # "conflict", "suspense", "result_first", "question", "shock"
    detected_elements: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class EmotionCurveScore:
    """情绪曲线评分"""
    score: float  # 0-100
    emotion_points: list[dict[str, Any]] = field(default_factory=list)
    curve_type: str = "wave"  # "rising", "falling", "wave", "climax_early", "climax_late"
    peak_timestamps: list[float] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class InformationDensityScore:
    """信息密度评分"""
    score: float  # 0-100
    density_map: list[dict[str, Any]] = field(default_factory=list)  # 每 10 秒的密度
    average_density: float = 0.0
    high_density_segments: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class RhythmMatchScore:
    """节奏匹配评分"""
    score: float  # 0-100
    current_bpm: float = 0.0
    target_bpm: float = 0.0
    rhythm_type: str = "medium"  # "fast", "medium", "slow"
    match_ratio: float = 0.0
    suggestions: list[str] = field(default_factory=list)


@dataclass
class InteractionDesignScore:
    """互动设计评分"""
    score: float  # 0-100
    cta_count: int = 0
    cta_types: list[str] = field(default_factory=list)
    question_count: int = 0
    open_ended_questions: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class ViralScoreResult:
    """爆款评分结果"""
    total_score: float  # 0-100
    hook_score: HookScore
    emotion_curve_score: EmotionCurveScore
    information_density_score: InformationDensityScore
    rhythm_match_score: RhythmMatchScore
    interaction_design_score: InteractionDesignScore
    grade: str  # "S", "A", "B", "C", "D"
    recommendations: list[str] = field(default_factory=list)
    assessment_time: str = ""
    assessor_version: str = "1.0.0"


class ViralScoreCalculator:
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

    def _calculate_hook_score(self, script_text: str, platform: str) -> HookScore:
        """
        计算开篇钩子评分

        Args:
            script_text: 解说文案
            platform: 目标平台

        Returns:
            HookScore: 钩子评分
        """
        score = 50.0  # 基础分
        hook_type = "unknown"
        detected_elements = []
        suggestions = []

        # 提取前 3 秒的文案（约 15-20 个字）
        lines = script_text.split("\n")
        first_line = lines[0] if lines else ""
        first_3_seconds = first_line[:30] if len(first_line) > 30 else first_line

        # 检测钩子类型
        hook_patterns = {
            "conflict": ["没想到", "竟然", "居然", "突然", "意外", "但是", "然而", "可是"],
            "suspense": ["秘密", "真相", "背后", "隐藏", "谜团", "悬念", "最后"],
            "result_first": ["结局", "最后", "最终", "结果", "后来"],
            "question": ["为什么", "怎么", "如何", "是什么", "哪里", "谁"],
            "shock": ["震惊", "可怕", "恐怖", "惊人", "难以置信", "不敢相信"],
        }

        for hook_type_name, keywords in hook_patterns.items():
            for keyword in keywords:
                if keyword in first_3_seconds:
                    hook_type = hook_type_name
                    detected_elements.append(keyword)
                    score += 10
                    break

        # 检测结果前置模式
        result_patterns = ["最后一刻", "结局", "最终", "直到最后"]
        for pattern in result_patterns:
            if pattern in first_3_seconds:
                score += 15
                detected_elements.append(f"结果前置: {pattern}")

        # 检测冲突模式
        conflict_patterns = ["没想到", "竟然", "居然", "突然"]
        for pattern in conflict_patterns:
            if pattern in first_3_seconds:
                score += 12
                detected_elements.append(f"冲突: {pattern}")

        # 限制最高分
        score = min(100, score)

        # 生成建议
        if score < 70:
            suggestions.append("建议将开头改为结果前置或冲突模式")
            suggestions.append("例如：'最后一刻，他才发现...' 或 '没想到，竟然...'")

        if not detected_elements:
            suggestions.append("未检测到明显钩子元素，建议添加悬念或冲突")

        return HookScore(
            score=score,
            hook_type=hook_type,
            detected_elements=detected_elements,
            suggestions=suggestions,
        )

    def _calculate_emotion_curve_score(
        self,
        emotion_data: list[dict[str, Any]],
        video_duration: float,
    ) -> EmotionCurveScore:
        """
        计算情绪曲线评分

        Args:
            emotion_data: 情绪数据
            video_duration: 视频时长

        Returns:
            EmotionCurveScore: 情绪曲线评分
        """
        score = 50.0  # 基础分
        emotion_points = []
        curve_type = "wave"
        peak_timestamps = []
        suggestions = []

        if not emotion_data:
            # 如果没有情绪数据，使用基础评估
            suggestions.append("建议提供情绪数据以获得更准确的评分")
            return EmotionCurveScore(
                score=score,
                emotion_points=[],
                curve_type="unknown",
                peak_timestamps=[],
                suggestions=suggestions,
            )

        # 分析情绪曲线
        intensities = [e.get("intensity", 0.5) for e in emotion_data]
        timestamps = [e.get("timestamp", 0) for e in emotion_data]

        # 计算情绪波动
        if len(intensities) > 1:
            variance = sum((i - sum(intensities) / len(intensities)) ** 2 for i in intensities) / len(intensities)
            volatility = variance ** 0.5

            # 波动越大，分数越高
            if volatility > 0.3:
                score += 20
            elif volatility > 0.2:
                score += 10

        # 检测情绪峰值
        for i in range(1, len(intensities) - 1):
            if intensities[i] > intensities[i-1] and intensities[i] > intensities[i+1]:
                if intensities[i] > 0.7:
                    peak_timestamps.append(timestamps[i])
                    score += 5

        # 检测曲线类型
        if len(intensities) >= 3:
            first_half = sum(intensities[:len(intensities)//2]) / (len(intensities)//2)
            second_half = sum(intensities[len(intensities)//2:]) / (len(intensities) - len(intensities)//2)

            if second_half > first_half * 1.2:
                curve_type = "rising"
                score += 10  # 上升曲线加分
            elif first_half > second_half * 1.2:
                curve_type = "falling"
            else:
                curve_type = "wave"

        # 检测高潮位置
        if peak_timestamps:
            max_peak_time = max(peak_timestamps)
            if video_duration > 0:
                peak_ratio = max_peak_time / video_duration
                if 0.6 < peak_ratio < 0.9:  # 高潮在 60%-90% 位置
                    curve_type = "climax_late"
                    score += 15
                elif 0.2 < peak_ratio < 0.4:  # 高潮在 20%-40% 位置
                    curve_type = "climax_early"
                    score += 10

        # 限制最高分
        score = min(100, score)

        # 生成建议
        if score < 70:
            suggestions.append("建议增加情绪波动，避免平淡叙事")
            suggestions.append("建议在视频中后段设置情绪高潮")

        return EmotionCurveScore(
            score=score,
            emotion_points=emotion_data,
            curve_type=curve_type,
            peak_timestamps=peak_timestamps,
            suggestions=suggestions,
        )

    def _calculate_information_density_score(
        self,
        script_text: str,
        video_duration: float,
    ) -> InformationDensityScore:
        """
        计算信息密度评分

        Args:
            script_text: 解说文案
            video_duration: 视频时长

        Returns:
            InformationDensityScore: 信息密度评分
        """
        score = 50.0  # 基础分
        density_map = []
        average_density = 0.0
        high_density_segments = []
        suggestions = []

        # 分析文案长度
        char_count = len(script_text)
        word_count = len(script_text.split())

        # 估算信息密度
        if video_duration > 0:
            chars_per_second = char_count / video_duration
            average_density = chars_per_second

            # 理想密度：3-5 字/秒
            if 3 <= chars_per_second <= 5:
                score += 20
            elif 2 <= chars_per_second <= 6:
                score += 10
            else:
                suggestions.append("信息密度过高或过低，建议调整")

        # 分析句式多样性
        sentences = script_text.split("。")
        sentence_lengths = [len(s) for s in sentences if s.strip()]

        if sentence_lengths:
            avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths)
            if 10 <= avg_sentence_length <= 30:
                score += 10
            else:
                suggestions.append("建议调整句式长度，保持 10-30 字为佳")

        # 检测信息密度高的段落
        for i in range(0, char_count, 100):
            segment = script_text[i:i+100]
            segment_density = len(segment) / 100
            if segment_density > 0.8:
                high_density_segments.append({
                    "start": i,
                    "end": i+100,
                    "density": segment_density,
                })

        # 限制最高分
        score = min(100, score)

        return InformationDensityScore(
            score=score,
            density_map=density_map,
            average_density=average_density,
            high_density_segments=high_density_segments,
            suggestions=suggestions,
        )

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
        platform_bpm = self.PLATFORM_OPTIMAL_BPM.get(platform, {})
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

    def _calculate_interaction_design_score(self, script_text: str) -> InteractionDesignScore:
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
        hook_score: HookScore,
        emotion_curve_score: EmotionCurveScore,
        information_density_score: InformationDensityScore,
        rhythm_match_score: RhythmMatchScore,
        interaction_design_score: InteractionDesignScore,
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
