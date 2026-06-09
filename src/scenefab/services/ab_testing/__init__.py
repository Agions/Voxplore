"""
SceneFab A/B 文案变生成功能

功能：
1. 同一素材自动生成 2-3 个不同版本的解说稿
2. 不同开头钩子（结果前置/冲突/悬念）
3. 不同结尾 CTA
4. 爆款评分对比
5. GUI 对比预览

技术栈：
- LLM: 文案生成
- 爆款评分: 质量评估
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class HookType(str, Enum):
    """钩子类型"""

    RESULT_FIRST = "result_first"  # 结果前置
    CONFLICT = "conflict"  # 冲突开头
    SUSPENSE = "suspense"  # 悬念钩子
    QUESTION = "question"  # 问题开头
    SHOCK = "shock"  # 震惊开头


class CTAType(str, Enum):
    """CTA 类型"""

    LIKE = "like"  # 点赞
    SHARE = "share"  # 分享
    SUBSCRIBE = "subscribe"  # 关注
    COMMENT = "comment"  # 评论
    COLLECT = "collect"  # 收藏


@dataclass
class ScriptVariant:
    """解说稿变体"""

    variant_id: str
    hook_type: HookType
    hook_text: str  # 开头钩子文案
    main_content: str  # 主要内容
    cta_type: CTAType
    cta_text: str  # CTA 文案
    full_script: str  # 完整解说稿
    viral_score: float = 0.0  # 爆款评分 0-100
    hook_strength: float = 0.0  # 钩子强度 0-10
    completion_rate_estimate: float = 0.0  # 预估完播率 0-100
    interaction_potential: float = 0.0  # 互动潜力 0-10
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ABTestResult:
    """A/B 测试结果"""

    original_script: str  # 原始解说稿
    variants: list[ScriptVariant] = field(default_factory=list)
    best_variant: ScriptVariant | None = None
    comparison_table: list[dict[str, Any]] = field(default_factory=list)
    generation_time: str = ""
    generator_version: str = "1.0.0"


class ABScriptGenerator:
    """
    A/B 文案变体生成器

    用于生成多个版本的解说稿，便于对比选择。

    使用方法：
        generator = ABScriptGenerator()
        result = generator.generate(
            original_script="原始解说稿...",
            num_variants=3,
            platform="douyin",
        )
        for variant in result.variants:
            print(f"版本 {variant.variant_id}: {variant.hook_text}")
            print(f"  爆款评分: {variant.viral_score}")
    """

    # 钩子模板
    HOOK_TEMPLATES = {
        HookType.RESULT_FIRST: [
            "结局太意外了！{content}",
            "最后一刻，他才发现{content}",
            "最终的结果让人意想不到{content}",
            "看完结局我沉默了{content}",
        ],
        HookType.CONFLICT: [
            "没想到，竟然{content}",
            "居然发生了这种事{content}",
            "突然的变故让所有人震惊{content}",
            "但是，意外发生了{content}",
        ],
        HookType.SUSPENSE: [
            "这个秘密你知道吗？{content}",
            "背后的真相让人震惊{content}",
            "隐藏的真相终于揭晓{content}",
            "谜团终于解开了{content}",
        ],
        HookType.QUESTION: [
            "为什么他会这样做？{content}",
            "你能猜到结局吗？{content}",
            "如果是你，你会怎么选择？{content}",
            "这个问题困扰了很多人{content}",
        ],
        HookType.SHOCK: [
            "太震惊了！{content}",
            "难以置信！{content}",
            "惊人的一幕发生了{content}",
            "所有人都惊呆了{content}",
        ],
    }

    # CTA 模板
    CTA_TEMPLATES = {
        CTAType.LIKE: [
            "觉得好看就点个赞吧！",
            "双击屏幕给我一个赞！",
            "喜欢的话别忘了点赞哦！",
        ],
        CTAType.SHARE: [
            "分享给你的朋友一起看！",
            "转发给身边的朋友！",
            "好东西要分享！",
        ],
        CTAType.SUBSCRIBE: [
            "关注我，更多精彩内容！",
            "订阅频道，不错过更新！",
            "加入我们，一起追剧！",
        ],
        CTAType.COMMENT: [
            "评论区告诉我你的看法！",
            "你觉得结局怎么样？",
            "说说你的想法！",
        ],
        CTAType.COLLECT: [
            "收藏起来慢慢看！",
            "先收藏，有空再看！",
            "好剧值得收藏！",
        ],
    }

    def __init__(self, llm_provider=None):
        """
        初始化 A/B 文案生成器

        Args:
            llm_provider: LLM 提供商
        """
        self.llm_provider = llm_provider
        logger.info("ABScriptGenerator 初始化完成")

    def generate(
        self,
        original_script: str,
        num_variants: int = 3,
        platform: str = "douyin",
        hook_types: list[HookType] | None = None,
        cta_types: list[CTAType] | None = None,
    ) -> ABTestResult:
        """
        生成 A/B 文案变体

        Args:
            original_script: 原始解说稿
            num_variants: 变体数量
            platform: 目标平台
            hook_types: 钩子类型列表（可选）
            cta_types: CTA 类型列表（可选）

        Returns:
            ABTestResult: A/B 测试结果
        """
        logger.info(f"开始生成 A/B 文案变体: {num_variants} 个版本")

        # 默认钩子类型
        if hook_types is None:
            hook_types = [
                HookType.RESULT_FIRST,
                HookType.CONFLICT,
                HookType.SUSPENSE,
            ]

        # 默认 CTA 类型
        if cta_types is None:
            cta_types = [
                CTAType.LIKE,
                CTAType.SHARE,
                CTAType.COMMENT,
            ]

        # 生成变体
        variants = []
        for i in range(num_variants):
            hook_type = hook_types[i % len(hook_types)]
            cta_type = cta_types[i % len(cta_types)]

            variant = self._generate_variant(
                original_script=original_script,
                variant_id=f"v{i + 1}",
                hook_type=hook_type,
                cta_type=cta_type,
                platform=platform,
            )
            variants.append(variant)

        # 选择最佳变体
        best_variant = max(variants, key=lambda x: x.viral_score) if variants else None

        # 生成对比表
        comparison_table = self._generate_comparison_table(variants)

        result = ABTestResult(
            original_script=original_script,
            variants=variants,
            best_variant=best_variant,
            comparison_table=comparison_table,
        )

        logger.info(f"A/B 文案变体生成完成: {len(variants)} 个版本")
        return result

    def _generate_variant(
        self,
        original_script: str,
        variant_id: str,
        hook_type: HookType,
        cta_type: CTAType,
        platform: str,
    ) -> ScriptVariant:
        """
        生成单个变体

        Args:
            original_script: 原始解说稿
            variant_id: 变体 ID
            hook_type: 钩子类型
            cta_type: CTA 类型
            platform: 目标平台

        Returns:
            ScriptVariant: 解说稿变体
        """
        # 提取主要内容（去除开头和结尾）
        main_content = self._extract_main_content(original_script)

        # 生成钩子
        hook_text = self._generate_hook(hook_type, main_content)

        # 生成 CTA
        cta_text = self._generate_cta(cta_type, platform)

        # 组合完整脚本
        full_script = self._combine_script(hook_text, main_content, cta_text)

        # 计算评分
        viral_score = self._calculate_viral_score(full_script, platform)
        hook_strength = self._calculate_hook_strength(hook_text)
        completion_rate_estimate = self._estimate_completion_rate(full_script)
        interaction_potential = self._calculate_interaction_potential(cta_text)

        return ScriptVariant(
            variant_id=variant_id,
            hook_type=hook_type,
            hook_text=hook_text,
            main_content=main_content,
            cta_type=cta_type,
            cta_text=cta_text,
            full_script=full_script,
            viral_score=viral_score,
            hook_strength=hook_strength,
            completion_rate_estimate=completion_rate_estimate,
            interaction_potential=interaction_potential,
        )

    def _extract_main_content(self, script: str) -> str:
        """
        提取主要内容

        Args:
            script: 原始解说稿

        Returns:
            str: 主要内容
        """
        # 分割句子
        sentences = script.split("。")

        # 去除第一句（通常是开头）和最后一句（通常是结尾）
        if len(sentences) > 2:
            main_sentences = sentences[1:-1]
        elif len(sentences) > 1:
            main_sentences = sentences[1:]
        else:
            main_sentences = sentences

        return "。".join(main_sentences)

    def _generate_hook(self, hook_type: HookType, content: str) -> str:
        """
        生成钩子

        Args:
            hook_type: 钩子类型
            content: 内容

        Returns:
            str: 钩子文案
        """
        import random

        templates = self.HOOK_TEMPLATES.get(hook_type, [])
        if not templates:
            return content[:20]

        template = random.choice(templates)

        # 提取内容的关键部分
        key_content = content[:15] if len(content) > 15 else content

        return template.format(content=key_content)

    def _generate_cta(self, cta_type: CTAType, platform: str) -> str:
        """
        生成 CTA

        Args:
            cta_type: CTA 类型
            platform: 目标平台

        Returns:
            str: CTA 文案
        """
        import random

        templates = self.CTA_TEMPLATES.get(cta_type, [])
        if not templates:
            return "感谢观看！"

        return random.choice(templates)

    def _combine_script(self, hook: str, main_content: str, cta: str) -> str:
        """
        组合完整脚本

        Args:
            hook: 钩子文案
            main_content: 主要内容
            cta: CTA 文案

        Returns:
            str: 完整脚本
        """
        # 组合脚本
        parts = []

        # 钩子
        parts.append(hook)

        # 主要内容
        if main_content:
            parts.append(main_content)

        # CTA
        parts.append(cta)

        return "。".join(parts)

    def _calculate_viral_score(self, script: str, platform: str) -> float:
        """
        计算爆款评分

        Args:
            script: 解说稿
            platform: 目标平台

        Returns:
            float: 爆款评分 0-100
        """
        score = 50.0

        # 检测钩子元素
        hook_patterns = ["没想到", "竟然", "居然", "最后", "结局", "真相", "秘密"]
        for pattern in hook_patterns:
            if pattern in script[:30]:
                score += 10
                break

        # 检测 CTA
        cta_patterns = ["点赞", "关注", "分享", "评论", "收藏"]
        for pattern in cta_patterns:
            if pattern in script[-50:]:
                score += 5
                break

        # 检测问题
        if "？" in script or "?" in script:
            score += 5

        # 限制分数范围
        return min(100, max(0, score))

    def _calculate_hook_strength(self, hook: str) -> float:
        """
        计算钩子强度

        Args:
            hook: 钩子文案

        Returns:
            float: 钩子强度 0-10
        """
        strength = 5.0

        # 检测强钩子元素
        strong_patterns = ["太意外", "震惊", "难以置信", "没想到", "竟然"]
        for pattern in strong_patterns:
            if pattern in hook:
                strength += 2
                break

        # 检测悬念元素
        suspense_patterns = ["秘密", "真相", "背后", "隐藏"]
        for pattern in suspense_patterns:
            if pattern in hook:
                strength += 1.5
                break

        return min(10, max(0, strength))

    def _estimate_completion_rate(self, script: str) -> float:
        """
        估算完播率

        Args:
            script: 解说稿

        Returns:
            float: 预估完播率 0-100
        """
        rate = 50.0

        # 基于脚本长度估算
        char_count = len(script)
        if char_count < 500:
            rate += 10  # 短视频完播率高
        elif char_count > 1000:
            rate -= 10  # 长视频完播率低

        # 检测悬念元素
        suspense_patterns = ["但是", "然而", "突然", "意外", "没想到"]
        for pattern in suspense_patterns:
            if pattern in script:
                rate += 5
                break

        return min(100, max(0, rate))

    def _calculate_interaction_potential(self, cta: str) -> float:
        """
        计算互动潜力

        Args:
            cta: CTA 文案

        Returns:
            float: 互动潜力 0-10
        """
        potential = 5.0

        # 检测互动元素
        interaction_patterns = ["评论", "留言", "说说", "你觉得", "你怎么看"]
        for pattern in interaction_patterns:
            if pattern in cta:
                potential += 2
                break

        # 检测情感元素
        emotional_patterns = ["喜欢", "好看", "感动", "有趣"]
        for pattern in emotional_patterns:
            if pattern in cta:
                potential += 1
                break

        return min(10, max(0, potential))

    def _generate_comparison_table(
        self,
        variants: list[ScriptVariant],
    ) -> list[dict[str, Any]]:
        """
        生成对比表

        Args:
            variants: 变体列表

        Returns:
            list: 对比表数据
        """
        table = []
        for variant in variants:
            table.append(
                {
                    "variant_id": variant.variant_id,
                    "hook_type": variant.hook_type.value,
                    "hook_text": variant.hook_text[:30],
                    "cta_type": variant.cta_type.value,
                    "viral_score": variant.viral_score,
                    "hook_strength": variant.hook_strength,
                    "completion_rate": variant.completion_rate_estimate,
                    "interaction_potential": variant.interaction_potential,
                }
            )
        return table


def generate_ab_variants(
    original_script: str,
    num_variants: int = 3,
    platform: str = "douyin",
    llm_provider=None,
) -> ABTestResult:
    """
    便捷函数：生成 A/B 文案变体

    Args:
        original_script: 原始解说稿
        num_variants: 变体数量
        platform: 目标平台
        llm_provider: LLM 提供商

    Returns:
        ABTestResult: A/B 测试结果
    """
    generator = ABScriptGenerator(llm_provider=llm_provider)
    return generator.generate(
        original_script=original_script,
        num_variants=num_variants,
        platform=platform,
    )
