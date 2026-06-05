"""
合理使用建议模块

功能：
1. 合理使用原则评估
2. 使用时长建议
3. 转换性使用评估
4. 合规性建议生成

参考：
- 美国版权法第 107 条合理使用原则
- 中国著作权法第 24 条合理使用规定
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FairUseAssessment:
    """合理使用评估结果"""
    is_fair_use: bool
    confidence: float  # 0.0 - 1.0
    factors: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    safe_duration: float = 0.0  # 建议的安全使用时长（秒）
    assessment_time: str = ""
    assessor_version: str = "1.0.0"


class FairUseAdvisor:
    """
    合理使用顾问

    用于评估视频素材的合理使用情况，提供合规建议。

    使用方法：
        advisor = FairUseAdvisor()
        result = advisor.assess(
            source_duration=7200,
            usage_duration=120,
            purpose="commentary",
            is_transformative=True,
        )
        print(result.is_fair_use)
        print(result.recommendations)
    """

    # 合理使用四要素权重
    FACTOR_WEIGHTS = {
        "purpose": 0.30,  # 使用目的
        "nature": 0.20,   # 作品性质
        "amount": 0.30,   # 使用数量
        "effect": 0.20,   # 市场影响
    }

    # 安全阈值
    SAFE_DURATION_ABSOLUTE = 120  # 2 分钟
    SAFE_DURATION_PERCENTAGE = 0.10  # 10%
    SAFE_DURATION_MINIMUM = 30  # 最少 30 秒

    def __init__(self):
        """初始化合理使用顾问"""
        logger.info("FairUseAdvisor 初始化完成")

    def assess(
        self,
        source_duration: float,
        usage_duration: float,
        purpose: str = "commentary",
        is_transformative: bool = True,
        is_commercial: bool = False,
        has_copyright_notice: bool = True,
    ) -> FairUseAssessment:
        """
        评估合理使用

        Args:
            source_duration: 原始素材时长（秒）
            usage_duration: 使用时长（秒）
            purpose: 使用目的（commentary, criticism, education, news, parody）
            is_transformative: 是否具有转换性
            is_commercial: 是否用于商业目的
            has_copyright_notice: 是否包含版权声明

        Returns:
            FairUseAssessment: 评估结果
        """
        logger.info("开始合理使用评估")

        # 计算四要素得分
        factors = {}

        # 要素 1：使用目的
        factors["purpose"] = self._assess_purpose(
            purpose, is_transformative, is_commercial
        )

        # 要素 2：作品性质
        factors["nature"] = self._assess_nature(source_duration)

        # 要素 3：使用数量
        factors["amount"] = self._assess_amount(
            source_duration, usage_duration
        )

        # 要素 4：市场影响
        factors["effect"] = self._assess_effect(
            is_transformative, is_commercial, has_copyright_notice
        )

        # 计算综合得分
        total_score = sum(
            factors[key] * self.FACTOR_WEIGHTS[key]
            for key in factors
        )

        # 判断是否构成合理使用
        is_fair_use = total_score >= 0.6
        confidence = total_score

        # 计算安全使用时长
        safe_duration = self._calculate_safe_duration(
            source_duration, usage_duration
        )

        # 生成建议
        recommendations = self._generate_recommendations(
            factors, is_fair_use, safe_duration
        )

        result = FairUseAssessment(
            is_fair_use=is_fair_use,
            confidence=confidence,
            factors=factors,
            recommendations=recommendations,
            safe_duration=safe_duration,
        )

        logger.info(f"合理使用评估完成: 合理使用={is_fair_use}, 置信度={confidence:.2f}")
        return result

    def _assess_purpose(
        self,
        purpose: str,
        is_transformative: bool,
        is_commercial: bool,
    ) -> float:
        """
        评估使用目的

        Args:
            purpose: 使用目的
            is_transformative: 是否具有转换性
            is_commercial: 是否用于商业目的

        Returns:
            float: 得分（0.0 - 1.0）
        """
        score = 0.5  # 基础分

        # 转换性使用加分
        if is_transformative:
            score += 0.3

        # 目的加分
        purpose_scores = {
            "commentary": 0.2,   # 评论
            "criticism": 0.2,    # 批评
            "education": 0.15,   # 教育
            "news": 0.15,        # 新闻
            "parody": 0.2,       # 模仿
            "research": 0.1,     # 研究
            "personal": 0.05,    # 个人使用
        }
        score += purpose_scores.get(purpose, 0.0)

        # 商业使用减分
        if is_commercial:
            score -= 0.2

        return max(0.0, min(1.0, score))

    def _assess_nature(self, source_duration: float) -> float:
        """
        评估作品性质

        Args:
            source_duration: 原始素材时长

        Returns:
            float: 得分（0.0 - 1.0）
        """
        # 基于时长推断作品类型
        if source_duration > 7200:  # 2 小时以上，可能是电影
            return 0.3  # 电影等创造性作品，得分较低
        elif source_duration > 3600:  # 1 小时以上，可能是剧集
            return 0.4
        elif source_duration > 600:  # 10 分钟以上，可能是短视频
            return 0.6
        else:  # 短片段
            return 0.8

    def _assess_amount(
        self,
        source_duration: float,
        usage_duration: float,
    ) -> float:
        """
        评估使用数量

        Args:
            source_duration: 原始素材时长
            usage_duration: 使用时长

        Returns:
            float: 得分（0.0 - 1.0）
        """
        if source_duration <= 0:
            return 0.5

        # 计算使用比例
        usage_ratio = usage_duration / source_duration

        # 计算得分
        if usage_ratio <= 0.05:  # 5% 以内
            return 0.9
        elif usage_ratio <= 0.10:  # 10% 以内
            return 0.7
        elif usage_ratio <= 0.20:  # 20% 以内
            return 0.5
        elif usage_ratio <= 0.30:  # 30% 以内
            return 0.3
        else:
            return 0.1

    def _assess_effect(
        self,
        is_transformative: bool,
        is_commercial: bool,
        has_copyright_notice: bool,
    ) -> float:
        """
        评估市场影响

        Args:
            is_transformative: 是否具有转换性
            is_commercial: 是否用于商业目的
            has_copyright_notice: 是否包含版权声明

        Returns:
            float: 得分（0.0 - 1.0）
        """
        score = 0.5

        # 转换性使用减少市场影响
        if is_transformative:
            score += 0.3

        # 商业使用增加市场影响
        if is_commercial:
            score -= 0.2

        # 版权声明减少市场影响
        if has_copyright_notice:
            score += 0.1

        return max(0.0, min(1.0, score))

    def _calculate_safe_duration(
        self,
        source_duration: float,
        usage_duration: float,
    ) -> float:
        """
        计算安全使用时长

        Args:
            source_duration: 原始素材时长
            usage_duration: 使用时长

        Returns:
            float: 建议的安全使用时长（秒）
        """
        # 计算基于比例的安全时长
        safe_by_percentage = source_duration * self.SAFE_DURATION_PERCENTAGE

        # 取绝对值和比例值的较小者
        safe_duration = min(self.SAFE_DURATION_ABSOLUTE, safe_by_percentage)

        # 确保最少时长
        safe_duration = max(safe_duration, self.SAFE_DURATION_MINIMUM)

        return safe_duration

    def _generate_recommendations(
        self,
        factors: dict[str, float],
        is_fair_use: bool,
        safe_duration: float,
    ) -> list[str]:
        """
        生成建议

        Args:
            factors: 四要素得分
            is_fair_use: 是否构成合理使用
            safe_duration: 安全使用时长

        Returns:
            list: 建议列表
        """
        recommendations = []

        if is_fair_use:
            recommendations.append("✅ 当前使用方式可能构成合理使用")
        else:
            recommendations.append("⚠️ 当前使用方式可能存在版权风险")

        # 基于各要素的建议
        if factors.get("purpose", 0) < 0.5:
            recommendations.append("建议增加转换性内容（如评论、分析、批评）")

        if factors.get("amount", 0) < 0.5:
            recommendations.append(f"建议将使用时长控制在 {safe_duration:.1f} 秒以内")

        if factors.get("effect", 0) < 0.5:
            recommendations.append("建议添加版权声明，注明原始素材来源")

        # 通用建议
        recommendations.append("建议在视频描述中标注素材来源")
        recommendations.append("建议保留原始素材的购买/授权凭证")

        return recommendations


def assess_fair_use(
    source_duration: float,
    usage_duration: float,
    purpose: str = "commentary",
    is_transformative: bool = True,
) -> FairUseAssessment:
    """
    便捷函数：评估合理使用

    Args:
        source_duration: 原始素材时长（秒）
        usage_duration: 使用时长（秒）
        purpose: 使用目的
        is_transformative: 是否具有转换性

    Returns:
        FairUseAssessment: 评估结果
    """
    advisor = FairUseAdvisor()
    return advisor.assess(
        source_duration=source_duration,
        usage_duration=usage_duration,
        purpose=purpose,
        is_transformative=is_transformative,
    )
