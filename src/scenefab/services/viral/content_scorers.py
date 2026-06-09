"""
SceneFab 内容质量评分混入

提供开篇钩子、情绪曲线、信息密度三个维度的评分计算方法。
"""

import logging
from typing import Any

from scenefab.services.viral.models import (
    EmotionCurveScore,
    HookScore,
    InformationDensityScore,
)

logger = logging.getLogger(__name__)


class ContentScorersMixin:
    """内容质量评分混入类"""

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
            "conflict": [
                "没想到",
                "竟然",
                "居然",
                "突然",
                "意外",
                "但是",
                "然而",
                "可是",
            ],
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
            variance = sum(
                (i - sum(intensities) / len(intensities)) ** 2 for i in intensities
            ) / len(intensities)
            volatility = variance**0.5

            # 波动越大，分数越高
            if volatility > 0.3:
                score += 20
            elif volatility > 0.2:
                score += 10

        # 检测情绪峰值
        for i in range(1, len(intensities) - 1):
            if (
                intensities[i] > intensities[i - 1]
                and intensities[i] > intensities[i + 1]
            ):
                if intensities[i] > 0.7:
                    peak_timestamps.append(timestamps[i])
                    score += 5

        # 检测曲线类型
        if len(intensities) >= 3:
            first_half = sum(intensities[: len(intensities) // 2]) / (
                len(intensities) // 2
            )
            second_half = sum(intensities[len(intensities) // 2 :]) / (
                len(intensities) - len(intensities) // 2
            )

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
            segment = script_text[i : i + 100]
            segment_density = len(segment) / 100
            if segment_density > 0.8:
                high_density_segments.append(
                    {
                        "start": i,
                        "end": i + 100,
                        "density": segment_density,
                    }
                )

        # 限制最高分
        score = min(100, score)

        return InformationDensityScore(
            score=score,
            density_map=density_map,
            average_density=average_density,
            high_density_segments=high_density_segments,
            suggestions=suggestions,
        )
