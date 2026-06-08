"""
SceneFab 封面文案生成混入

提供标题、副标题、钩子文案生成以及关键词提取和元数据生成等方法。
"""

import logging

from scenefab.services.cover.models import CoverText, VideoMetadata

logger = logging.getLogger(__name__)


class TextUtilsMixin:
    """封面文案生成混入类"""

    def _generate_cover_texts(
        self,
        script_text: str,
        platform: str,
        num_texts: int,
    ) -> list[CoverText]:
        """
        生成封面文案

        Args:
            script_text: 解说文案
            platform: 目标平台
            num_texts: 文案数量

        Returns:
            list: 封面文案列表
        """
        cover_texts = []

        # 获取平台热搜词
        trending_keywords = self.PLATFORM_TRENDING_KEYWORDS.get(platform, [])

        # 提取文案中的关键词
        script_keywords = self._extract_keywords(script_text)

        # 生成多个文案版本
        for i in range(num_texts):
            # 标题生成策略
            if i == 0:
                # 策略 1: 结果前置
                title = self._generate_title_result_first(script_text)
            elif i == 1:
                # 策略 2: 冲突开头
                title = self._generate_title_conflict(script_text)
            else:
                # 策略 3: 悬念钩子
                title = self._generate_title_suspense(script_text)

            # 添加热搜词
            if trending_keywords:
                keyword = trending_keywords[i % len(trending_keywords)]
                title = f"{keyword}！{title}"

            # 生成副标题
            subtitle = self._generate_subtitle(script_text)

            # 生成钩子文案
            hook = self._generate_hook(script_text)

            # 合并关键词
            all_keywords = list(set(script_keywords + trending_keywords[:3]))

            cover_texts.append(CoverText(
                title=title[:20],  # 限制标题长度
                subtitle=subtitle,
                hook=hook,
                keywords=all_keywords,
            ))

        return cover_texts

    def _extract_keywords(self, text: str) -> list[str]:
        """
        提取关键词

        Args:
            text: 文本

        Returns:
            list: 关键词列表
        """
        # 简单的关键词提取（实际应该用 NLP 技术）
        keywords = []

        # 常见电影相关关键词
        movie_keywords = [
            "电影", "剧情", "解说", "推荐", "高分", "神作",
            "悬疑", "动作", "喜剧", "爱情", "科幻", "恐怖",
        ]

        for keyword in movie_keywords:
            if keyword in text:
                keywords.append(keyword)

        return keywords[:5]

    def _generate_title_result_first(self, script_text: str) -> str:
        """
        生成结果前置标题

        Args:
            script_text: 解说文案

        Returns:
            str: 标题
        """
        # 提取第一句话
        first_sentence = script_text.split("。")[0] if script_text else ""

        # 转换为结果前置格式
        if "最后" in first_sentence or "结局" in first_sentence:
            return first_sentence[:15]
        else:
            return f"结局太意外！{first_sentence[:10]}"

    def _generate_title_conflict(self, script_text: str) -> str:
        """
        生成冲突开头标题

        Args:
            script_text: 解说文案

        Returns:
            str: 标题
        """
        # 提取冲突元素
        conflict_words = ["没想到", "竟然", "居然", "突然", "意外"]
        for word in conflict_words:
            if word in script_text:
                idx = script_text.index(word)
                return script_text[max(0, idx-5):idx+10][:15]

        return f"太震惊了！{script_text[:10]}"

    def _generate_title_suspense(self, script_text: str) -> str:
        """
        生成悬念钩子标题

        Args:
            script_text: 解说文案

        Returns:
            str: 标题
        """
        suspense_words = ["秘密", "真相", "背后", "隐藏", "谜团"]
        for word in suspense_words:
            if word in script_text:
                idx = script_text.index(word)
                return script_text[max(0, idx-5):idx+10][:15]

        return f"这个秘密你知道吗？{script_text[:8]}"

    def _generate_subtitle(self, script_text: str) -> str:
        """
        生成副标题

        Args:
            script_text: 解说文案

        Returns:
            str: 副标题
        """
        # 提取核心内容
        if len(script_text) > 50:
            return script_text[:50] + "..."
        return script_text

    def _generate_hook(self, script_text: str) -> str:
        """
        生成钩子文案

        Args:
            script_text: 解说文案

        Returns:
            str: 钩子文案
        """
        hooks = [
            "看完你就明白了",
            "结局让人意想不到",
            "全程高能",
            "不容错过",
            "建议收藏",
        ]

        # 根据文案内容选择钩子
        if "悬疑" in script_text or "烧脑" in script_text:
            return "烧脑神作，看完你就明白了"
        elif "感动" in script_text or "催泪" in script_text:
            return "催泪神作，准备好纸巾"
        else:
            return hooks[0]

    def _generate_metadata(
        self,
        script_text: str,
        platform: str,
        cover,
    ) -> VideoMetadata:
        """
        生成视频元数据

        Args:
            script_text: 解说文案
            platform: 目标平台
            cover: 封面帧

        Returns:
            VideoMetadata: 视频元数据
        """
        # 提取关键词
        keywords = self._extract_keywords(script_text)

        # 获取平台热搜词
        trending_keywords = self.PLATFORM_TRENDING_KEYWORDS.get(platform, [])

        # 合并标签
        tags = list(set(keywords + trending_keywords[:3]))

        # 生成标题
        title = self._generate_title_result_first(script_text)

        # 生成描述
        description = self._generate_subtitle(script_text)

        return VideoMetadata(
            title=title,
            description=description,
            tags=tags,
            category="电影解说",
            language="zh-CN",
            thumbnail_path=cover.frame_path if cover else "",
        )
