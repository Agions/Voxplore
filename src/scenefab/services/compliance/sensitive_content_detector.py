"""
敏感内容检测模块

功能：
1. 暴力内容检测
2. 裸露内容检测
3. 政治敏感内容检测
4. 违禁内容检测

技术栈：
- NSFW 模型：轻量级内容分类
- 关键词匹配：基础文本检测
- 视觉分析：图像内容分类
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SensitiveContentResult:
    """敏感内容检测结果"""
    is_sensitive: bool
    sensitivity_level: str  # "safe", "warning", "danger"
    detected_categories: list[str] = field(default_factory=list)
    confidence_scores: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    check_time: str = ""
    checker_version: str = "1.0.0"


class SensitiveContentDetector:
    """
    敏感内容检测器

    用于检测视频中的敏感内容，包括暴力、裸露、政治敏感等。

    使用方法：
        detector = SensitiveContentDetector()
        result = detector.detect("path/to/video.mp4")
        print(result.is_sensitive)
        print(result.warnings)
    """

    # 敏感关键词列表
    SENSITIVE_KEYWORDS = {
        "violence": [
            "暴力", "血腥", "杀戮", "枪战", "爆炸", "死亡", "伤害",
            "violence", "blood", "kill", "shoot", "explode", "death",
        ],
        "nudity": [
            "裸露", "色情", "成人", "性暗示",
            "nudity", "porn", "adult", "sexual",
        ],
        "political": [
            "政治", "敏感", "违禁", "反动", "颠覆",
            "political", "sensitive", "banned", "subversive",
        ],
        "illegal": [
            "违法", "犯罪", "毒品", "赌博", "诈骗",
            "illegal", "crime", "drug", "gambling", "fraud",
        ],
    }

    def __init__(self, use_ai_detection: bool = False):
        """
        初始化敏感内容检测器

        Args:
            use_ai_detection: 是否使用 AI 模型进行检测（需要 GPU）
        """
        self.use_ai_detection = use_ai_detection
        logger.info("SensitiveContentDetector 初始化完成")

    def detect(
        self,
        video_path: str | None = None,
        text: str | None = None,
        image_paths: list[str] | None = None,
    ) -> SensitiveContentResult:
        """
        执行敏感内容检测

        Args:
            video_path: 视频文件路径（可选）
            text: 文本内容（可选）
            image_paths: 图片路径列表（可选）

        Returns:
            SensitiveContentResult: 检测结果
        """
        logger.info("开始敏感内容检测")

        detected_categories = []
        confidence_scores = {}
        warnings = []

        # 1. 文本关键词检测
        if text:
            text_result = self._detect_text_keywords(text)
            if text_result["detected"]:
                detected_categories.extend(text_result["categories"])
                confidence_scores.update(text_result["scores"])
                warnings.extend(text_result["warnings"])

        # 2. 文件名检测
        if video_path:
            filename_result = self._detect_filename(video_path)
            if filename_result["detected"]:
                detected_categories.extend(filename_result["categories"])
                warnings.extend(filename_result["warnings"])

        # 3. AI 视觉检测（如果启用）
        if self.use_ai_detection and image_paths:
            ai_result = self._detect_with_ai(image_paths)
            if ai_result["detected"]:
                detected_categories.extend(ai_result["categories"])
                confidence_scores.update(ai_result["scores"])
                warnings.extend(ai_result["warnings"])

        # 去重
        detected_categories = list(set(detected_categories))

        # 确定敏感等级
        sensitivity_level = self._determine_sensitivity_level(
            detected_categories, confidence_scores
        )

        # 生成建议
        recommendations = self._generate_recommendations(
            detected_categories, sensitivity_level
        )

        result = SensitiveContentResult(
            is_sensitive=len(detected_categories) > 0,
            sensitivity_level=sensitivity_level,
            detected_categories=detected_categories,
            confidence_scores=confidence_scores,
            warnings=warnings,
            recommendations=recommendations,
        )

        logger.info(f"敏感内容检测完成: 敏感={result.is_sensitive}, 等级={sensitivity_level}")
        return result

    def _detect_text_keywords(self, text: str) -> dict[str, Any]:
        """
        检测文本中的敏感关键词

        Args:
            text: 文本内容

        Returns:
            dict: 检测结果
        """
        detected = False
        categories = []
        scores = {}
        warnings = []

        text_lower = text.lower()

        for category, keywords in self.SENSITIVE_KEYWORDS.items():
            matched_keywords = []
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    matched_keywords.append(keyword)

            if matched_keywords:
                detected = True
                categories.append(category)
                scores[category] = min(len(matched_keywords) / 3.0, 1.0)
                warnings.append(f"检测到 {category} 相关关键词: {', '.join(matched_keywords[:3])}")

        return {
            "detected": detected,
            "categories": categories,
            "scores": scores,
            "warnings": warnings,
        }

    def _detect_filename(self, video_path: str) -> dict[str, Any]:
        """
        检测文件名中的敏感信息

        Args:
            video_path: 视频文件路径

        Returns:
            dict: 检测结果
        """
        from pathlib import Path

        detected = False
        categories = []
        warnings = []

        filename = Path(video_path).name.lower()

        # 检测盗版关键词
        piracy_keywords = [
            "cam", "ts", "tc", "枪版", "盗版", "抢先版",
            "bluray", "bdrip", "hdrip", "dvdrip", "webrip",
        ]

        for keyword in piracy_keywords:
            if keyword in filename:
                detected = True
                categories.append("piracy")
                warnings.append(f"文件名包含盗版关键词: {keyword}")
                break

        return {
            "detected": detected,
            "categories": categories,
            "warnings": warnings,
        }

    def _detect_with_ai(self, image_paths: list[str]) -> dict[str, Any]:
        """
        使用 AI 模型检测图片内容

        Args:
            image_paths: 图片路径列表

        Returns:
            dict: 检测结果
        """
        # 这里可以集成 NSFW 模型
        # 目前返回空结果，后续可扩展
        logger.info("AI 视觉检测功能待实现")

        return {
            "detected": False,
            "categories": [],
            "scores": {},
            "warnings": [],
        }

    def _determine_sensitivity_level(
        self,
        categories: list[str],
        scores: dict[str, float],
    ) -> str:
        """
        确定敏感等级

        Args:
            categories: 检测到的敏感类别
            scores: 置信度分数

        Returns:
            str: 敏感等级
        """
        if not categories:
            return "safe"

        # 高风险类别
        high_risk_categories = {"violence", "nudity", "illegal"}

        # 检查是否有高风险类别
        if any(cat in high_risk_categories for cat in categories):
            return "danger"

        # 检查置信度
        max_score = max(scores.values()) if scores else 0
        if max_score > 0.7:
            return "danger"
        elif max_score > 0.4:
            return "warning"
        else:
            return "safe"

    def _generate_recommendations(
        self,
        categories: list[str],
        sensitivity_level: str,
    ) -> list[str]:
        """
        生成处理建议

        Args:
            categories: 检测到的敏感类别
            sensitivity_level: 敏感等级

        Returns:
            list: 建议列表
        """
        recommendations = []

        if sensitivity_level == "danger":
            recommendations.append("⚠️ 检测到高风险内容，强烈建议不要使用")
            recommendations.append("如需使用，请确保已获得相关授权")
            recommendations.append("建议添加内容警告标识")
        elif sensitivity_level == "warning":
            recommendations.append("⚠️ 检测到潜在敏感内容，请谨慎使用")
            recommendations.append("建议添加内容分级标识")
        else:
            recommendations.append("✅ 未检测到明显敏感内容")

        # 基于类别的建议
        if "violence" in categories:
            recommendations.append("暴力内容建议添加内容警告")
        if "nudity" in categories:
            recommendations.append("成人内容建议设置年龄限制")
        if "piracy" in categories:
            recommendations.append("检测到盗版特征，建议使用正版素材")

        return recommendations


def detect_sensitive_content(
    video_path: str | None = None,
    text: str | None = None,
    image_paths: list[str] | None = None,
) -> SensitiveContentResult:
    """
    便捷函数：执行敏感内容检测

    Args:
        video_path: 视频文件路径（可选）
        text: 文本内容（可选）
        image_paths: 图片路径列表（可选）

    Returns:
        SensitiveContentResult: 检测结果
    """
    detector = SensitiveContentDetector()
    return detector.detect(
        video_path=video_path,
        text=text,
        image_paths=image_paths,
    )
