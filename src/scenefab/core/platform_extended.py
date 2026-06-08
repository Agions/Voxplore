"""
多平台参数包扩展模块

扩展功能：
1. 平台标签建议
2. 弹幕触发点建议
3. 三连引导话术
4. 封面文字规范
5. 关键词建议
6. 发布时间建议

技术栈：
- 平台规则库：JSON 配置文件
- 关键词提取：基于 LLM 的智能推荐
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PlatformTagSuggestion:
    """平台标签建议"""
    platform: str
    tags: list[str] = field(default_factory=list)
    trending_tags: list[str] = field(default_factory=list)
    category_tags: list[str] = field(default_factory=list)
    recommendation: str = ""


@dataclass
class DanmakuTriggerPoint:
    """弹幕触发点"""
    timestamp: float  # 秒
    trigger_type: str  # "question", "climax", "humor", "suspense"
    suggested_text: str  # 建议的弹幕内容
    confidence: float  # 0.0 - 1.0


@dataclass
class CallToAction:
    """行动号召"""
    platform: str
    cta_type: str  # "like", "share", "subscribe", "comment"
    text: str  # CTA 文本
    position: str  # "start", "middle", "end"
    timing: float  # 秒


@dataclass
class CoverTextSpec:
    """封面文字规范"""
    platform: str
    max_lines: int
    max_chars_per_line: int
    font_size_range: tuple[int, int]  # (min, max)
    recommended_fonts: list[str] = field(default_factory=list)
    text_position: str = "center"  # "top", "center", "bottom"
    text_color: str = "#FFFFFF"
    background_overlay: bool = True


@dataclass
class PlatformExtendedConfig:
    """平台扩展配置"""
    platform: str
    display_name: str
    tag_suggestion: PlatformTagSuggestion
    danmaku_triggers: list[DanmakuTriggerPoint] = field(default_factory=list)
    call_to_actions: list[CallToAction] = field(default_factory=list)
    cover_text_spec: CoverTextSpec | None = None
    best_posting_times: list[str] = field(default_factory=list)
    content_guidelines: list[str] = field(default_factory=list)
    seo_keywords: list[str] = field(default_factory=list)


class PlatformExtendedManager:
    """
    平台扩展管理器

    管理各平台的扩展参数，提供智能推荐功能。

    使用方法：
        manager = PlatformExtendedManager()
        config = manager.get_config("douyin")
        tags = manager.suggest_tags("douyin", "电影解说")
        ctas = manager.get_ctas("bilibili")
    """

    # 平台扩展配置
    PLATFORM_CONFIGS: dict[str, PlatformExtendedConfig] = {}

    def __init__(self, config_dir: str | None = None):
        """
        初始化平台扩展管理器

        Args:
            config_dir: 配置文件目录（可选）
        """
        self.config_dir = Path(config_dir) if config_dir else None
        self._load_default_configs()
        logger.info("PlatformExtendedManager 初始化完成")

    def _load_default_configs(self):
        """加载默认配置"""
        # 抖音配置
        self.PLATFORM_CONFIGS["douyin"] = PlatformExtendedConfig(
            platform="douyin",
            display_name="抖音",
            tag_suggestion=PlatformTagSuggestion(
                platform="douyin",
                tags=["电影解说", "影视推荐", "好剧推荐", "追剧"],
                trending_tags=["2026必看", "高分电影", "催泪神作", "烧脑悬疑"],
                category_tags=["动作片", "喜剧片", "爱情片", "科幻片", "悬疑片"],
                recommendation="建议使用 3-5 个标签，包含 1-2 个热门标签",
            ),
            danmaku_triggers=[
                DanmakuTriggerPoint(
                    timestamp=3.0,
                    trigger_type="question",
                    suggested_text="你觉得主角会怎么做？",
                    confidence=0.8,
                ),
                DanmakuTriggerPoint(
                    timestamp=60.0,
                    trigger_type="climax",
                    suggested_text="高能预警！",
                    confidence=0.9,
                ),
            ],
            call_to_actions=[
                CallToAction(
                    platform="douyin",
                    cta_type="like",
                    text="觉得好看就点个赞吧！",
                    position="end",
                    timing=0,
                ),
                CallToAction(
                    platform="douyin",
                    cta_type="share",
                    text="分享给你的朋友一起看！",
                    position="end",
                    timing=5,
                ),
            ],
            cover_text_spec=CoverTextSpec(
                platform="douyin",
                max_lines=2,
                max_chars_per_line=10,
                font_size_range=(24, 48),
                recommended_fonts=["思源黑体", "阿里巴巴普惠体"],
                text_position="center",
                text_color="#FFFFFF",
                background_overlay=True,
            ),
            best_posting_times=["12:00", "18:00", "21:00"],
            content_guidelines=[
                "视频时长建议 1-3 分钟",
                "前 3 秒必须有钩子",
                "竖屏 9:16 比例",
                "字幕位置居中偏下",
            ],
            seo_keywords=["电影解说", "影视推荐", "好剧推荐"],
        )

        # B站配置
        self.PLATFORM_CONFIGS["bilibili"] = PlatformExtendedConfig(
            platform="bilibili",
            display_name="B站",
            tag_suggestion=PlatformTagSuggestion(
                platform="bilibili",
                tags=["影视杂谈", "电影", "电视剧", "动漫"],
                trending_tags=["2026新番", "高分神作", "冷门佳作", "经典重温"],
                category_tags=["番剧", "电影", "电视剧", "纪录片", "动画"],
                recommendation="建议使用 5-10 个标签，包含分区标签和内容标签",
            ),
            danmaku_triggers=[
                DanmakuTriggerPoint(
                    timestamp=5.0,
                    trigger_type="question",
                    suggested_text="前方高能预警！",
                    confidence=0.9,
                ),
                DanmakuTriggerPoint(
                    timestamp=120.0,
                    trigger_type="humor",
                    suggested_text="哈哈哈哈哈",
                    confidence=0.7,
                ),
                DanmakuTriggerPoint(
                    timestamp=180.0,
                    trigger_type="climax",
                    suggested_text="名场面！",
                    confidence=0.8,
                ),
            ],
            call_to_actions=[
                CallToAction(
                    platform="bilibili",
                    cta_type="like",
                    text="觉得不错就点个赞吧！",
                    position="end",
                    timing=0,
                ),
                CallToAction(
                    platform="bilibili",
                    cta_type="subscribe",
                    text="关注UP主，获取更多精彩内容！",
                    position="end",
                    timing=3,
                ),
                CallToAction(
                    platform="bilibili",
                    cta_type="share",
                    text="一键三连支持一下！",
                    position="end",
                    timing=5,
                ),
            ],
            cover_text_spec=CoverTextSpec(
                platform="bilibili",
                max_lines=3,
                max_chars_per_line=15,
                font_size_range=(20, 40),
                recommended_fonts=["思源黑体", "阿里巴巴普惠体", "站酷快乐体"],
                text_position="center",
                text_color="#FFFFFF",
                background_overlay=True,
            ),
            best_posting_times=["12:00", "18:00", "20:00", "22:00"],
            content_guidelines=[
                "视频时长建议 5-15 分钟",
                "横屏 16:9 比例",
                "字幕位置居中偏下",
                "可以适当加入梗和吐槽",
                "封面要有吸引力",
            ],
            seo_keywords=["影视杂谈", "电影解说", "电视剧解说"],
        )

        # 小红书配置
        self.PLATFORM_CONFIGS["xiaohongshu"] = PlatformExtendedConfig(
            platform="xiaohongshu",
            display_name="小红书",
            tag_suggestion=PlatformTagSuggestion(
                platform="xiaohongshu",
                tags=["电影推荐", "好剧推荐", "追剧日记", "影视推荐"],
                trending_tags=["必看电影", "高分推荐", "治愈系", "下饭剧"],
                category_tags=["电影", "电视剧", "综艺", "纪录片", "动漫"],
                recommendation="建议使用 5-8 个标签，包含 2-3 个热门标签",
            ),
            danmaku_triggers=[],
            call_to_actions=[
                CallToAction(
                    platform="xiaohongshu",
                    cta_type="like",
                    text="觉得有用就点个赞吧！",
                    position="end",
                    timing=0,
                ),
                CallToAction(
                    platform="xiaohongshu",
                    cta_type="comment",
                    text="评论区告诉我你最喜欢哪部！",
                    position="end",
                    timing=3,
                ),
                CallToAction(
                    platform="xiaohongshu",
                    cta_type="share",
                    text="收藏起来慢慢看！",
                    position="end",
                    timing=5,
                ),
            ],
            cover_text_spec=CoverTextSpec(
                platform="xiaohongshu",
                max_lines=2,
                max_chars_per_line=8,
                font_size_range=(28, 56),
                recommended_fonts=["思源黑体", "阿里巴巴普惠体"],
                text_position="center",
                text_color="#FFFFFF",
                background_overlay=True,
            ),
            best_posting_times=["07:00", "12:00", "18:00", "21:00"],
            content_guidelines=[
                "视频时长建议 1-5 分钟",
                "3:4 竖屏比例",
                "封面文字要大且清晰",
                "内容要精致有质感",
                "标题要有吸引力",
            ],
            seo_keywords=["电影推荐", "好剧推荐", "追剧日记"],
        )

        # YouTube 配置
        self.PLATFORM_CONFIGS["youtube"] = PlatformExtendedConfig(
            platform="youtube",
            display_name="YouTube",
            tag_suggestion=PlatformTagSuggestion(
                platform="youtube",
                tags=["movie review", "film analysis", "cinema", "entertainment"],
                trending_tags=["2026 movies", "best films", "must watch", "top 10"],
                category_tags=["Movies", "Entertainment", "Education", "People & Blogs"],
                recommendation="Use 5-15 tags, include both broad and specific tags",
            ),
            danmaku_triggers=[],
            call_to_actions=[
                CallToAction(
                    platform="youtube",
                    cta_type="like",
                    text="If you enjoyed this video, give it a thumbs up!",
                    position="end",
                    timing=0,
                ),
                CallToAction(
                    platform="youtube",
                    cta_type="subscribe",
                    text="Subscribe for more content like this!",
                    position="end",
                    timing=3,
                ),
                CallToAction(
                    platform="youtube",
                    cta_type="share",
                    text="Share this video with your friends!",
                    position="end",
                    timing=5,
                ),
            ],
            cover_text_spec=CoverTextSpec(
                platform="youtube",
                max_lines=3,
                max_chars_per_line=20,
                font_size_range=(24, 48),
                recommended_fonts=["Arial", "Helvetica", "Montserrat"],
                text_position="center",
                text_color="#FFFFFF",
                background_overlay=True,
            ),
            best_posting_times=["09:00", "12:00", "15:00", "18:00"],
            content_guidelines=[
                "Video length: 8-20 minutes recommended",
                "16:9 aspect ratio",
                "Add end screens and cards",
                "Use custom thumbnails",
                "Include timestamps in description",
            ],
            seo_keywords=["movie review", "film analysis", "cinema"],
        )

        # TikTok 配置
        self.PLATFORM_CONFIGS["tiktok"] = PlatformExtendedConfig(
            platform="tiktok",
            display_name="TikTok",
            tag_suggestion=PlatformTagSuggestion(
                platform="tiktok",
                tags=["moviereview", "film", "movie", "entertainment"],
                trending_tags=["fyp", "viral", "2026movies", "mustwatch"],
                category_tags=["Movies", "Entertainment", "Comedy", "Drama"],
                recommendation="Use 3-5 hashtags, include trending ones",
            ),
            danmaku_triggers=[],
            call_to_actions=[
                CallToAction(
                    platform="tiktok",
                    cta_type="like",
                    text="Like if you enjoyed!",
                    position="end",
                    timing=0,
                ),
                CallToAction(
                    platform="tiktok",
                    cta_type="share",
                    text="Share with a friend!",
                    position="end",
                    timing=3,
                ),
            ],
            cover_text_spec=CoverTextSpec(
                platform="tiktok",
                max_lines=2,
                max_chars_per_line=10,
                font_size_range=(28, 56),
                recommended_fonts=["Arial", "Helvetica"],
                text_position="center",
                text_color="#FFFFFF",
                background_overlay=True,
            ),
            best_posting_times=["07:00", "12:00", "19:00", "22:00"],
            content_guidelines=[
                "Video length: 15-60 seconds",
                "9:16 vertical aspect ratio",
                "Hook in first 3 seconds",
                "Use trending sounds",
                "Keep it fast-paced",
            ],
            seo_keywords=["moviereview", "film", "movie"],
        )

    def get_config(self, platform: str) -> PlatformExtendedConfig | None:
        """
        获取平台扩展配置

        Args:
            platform: 平台名称

        Returns:
            PlatformExtendedConfig: 平台配置
        """
        return self.PLATFORM_CONFIGS.get(platform)

    def suggest_tags(
        self,
        platform: str,
        content_type: str = "",
        custom_keywords: list[str] | None = None,
    ) -> PlatformTagSuggestion:
        """
        建议标签

        Args:
            platform: 平台名称
            content_type: 内容类型
            custom_keywords: 自定义关键词

        Returns:
            PlatformTagSuggestion: 标签建议
        """
        config = self.get_config(platform)
        if config is None:
            return PlatformTagSuggestion(platform=platform)

        # 基础标签
        tags = list(config.tag_suggestion.tags)

        # 添加内容类型标签
        if content_type:
            tags.append(content_type)

        # 添加自定义关键词
        if custom_keywords:
            tags.extend(custom_keywords)

        # 去重
        tags = list(set(tags))

        return PlatformTagSuggestion(
            platform=platform,
            tags=tags,
            trending_tags=config.tag_suggestion.trending_tags,
            category_tags=config.tag_suggestion.category_tags,
            recommendation=config.tag_suggestion.recommendation,
        )

    def get_danmaku_triggers(
        self,
        platform: str,
        video_duration: float = 0,
    ) -> list[DanmakuTriggerPoint]:
        """
        获取弹幕触发点

        Args:
            platform: 平台名称
            video_duration: 视频时长（秒）

        Returns:
            list: 弹幕触发点列表
        """
        config = self.get_config(platform)
        if config is None:
            return []

        triggers = config.danmaku_triggers

        # 如果视频时长已知，过滤掉超出范围的触发点
        if video_duration > 0:
            triggers = [t for t in triggers if t.timestamp < video_duration]

        return triggers

    def get_ctas(
        self,
        platform: str,
        position: str | None = None,
    ) -> list[CallToAction]:
        """
        获取行动号召

        Args:
            platform: 平台名称
            position: 位置（start, middle, end）

        Returns:
            list: 行动号召列表
        """
        config = self.get_config(platform)
        if config is None:
            return []

        ctas = config.call_to_actions

        # 如果指定了位置，过滤
        if position:
            ctas = [c for c in ctas if c.position == position]

        return ctas

    def get_cover_text_spec(self, platform: str) -> CoverTextSpec | None:
        """
        获取封面文字规范

        Args:
            platform: 平台名称

        Returns:
            CoverTextSpec: 封面文字规范
        """
        config = self.get_config(platform)
        if config is None:
            return None

        return config.cover_text_spec

    def get_best_posting_times(self, platform: str) -> list[str]:
        """
        获取最佳发布时间

        Args:
            platform: 平台名称

        Returns:
            list: 最佳发布时间列表
        """
        config = self.get_config(platform)
        if config is None:
            return []

        return config.best_posting_times

    def get_content_guidelines(self, platform: str) -> list[str]:
        """
        获取内容指南

        Args:
            platform: 平台名称

        Returns:
            list: 内容指南列表
        """
        config = self.get_config(platform)
        if config is None:
            return []

        return config.content_guidelines

    def get_seo_keywords(self, platform: str) -> list[str]:
        """
        获取 SEO 关键词

        Args:
            platform: 平台名称

        Returns:
            list: SEO 关键词列表
        """
        config = self.get_config(platform)
        if config is None:
            return []

        return config.seo_keywords


def get_platform_extended_manager(config_dir: str | None = None) -> PlatformExtendedManager:
    """
    便捷函数：获取平台扩展管理器

    Args:
        config_dir: 配置文件目录

    Returns:
        PlatformExtendedManager: 平台扩展管理器
    """
    return PlatformExtendedManager(config_dir=config_dir)
