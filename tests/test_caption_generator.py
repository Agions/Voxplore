#!/usr/bin/env python3
"""Test Caption Generator"""


from app.services.video_tools.caption_generator import (
    CaptionStyle,
    EmotionLevel,
    Word,
    Caption,
    CaptionConfig,
    CaptionGenerator,
)


class TestCaptionStyle:
    """Test caption style enum"""

    def test_all_styles(self):
        """Test all styles"""
        styles = [
            CaptionStyle.VIRAL,
            CaptionStyle.MINIMAL,
            CaptionStyle.SUBTITLE,
            CaptionStyle.FLOATING,
        ]
        
        assert len(styles) == 4
        assert CaptionStyle.VIRAL.value == "viral"


class TestEmotionLevel:
    """Test emotion level enum"""

    def test_levels(self):
        """Test all levels"""
        assert EmotionLevel.NEUTRAL.value == 0
        assert EmotionLevel.LOW.value == 1
        assert EmotionLevel.MEDIUM.value == 2
        assert EmotionLevel.HIGH.value == 3


class TestWord:
    """Test word dataclass"""

    def test_creation(self):
        """Test creation"""
        word = Word(
            text="测试",
            start_time=0.0,
            end_time=0.5,
            is_keyword=True,
            emotion=EmotionLevel.HIGH,
        )
        
        assert word.text == "测试"
        assert word.start_time == 0.0
        assert word.end_time == 0.5
        assert word.is_keyword is True
        assert word.emotion == EmotionLevel.HIGH


class TestCaption:
    """Test caption dataclass"""

    def test_creation(self):
        """Test creation"""
        words = [
            Word("测试", 0.0, 0.5, False, EmotionLevel.NEUTRAL),
        ]
        
        caption = Caption(
            text="测试",
            start_time=0.0,
            end_time=0.5,
            words=words,
            style=CaptionStyle.VIRAL,
            position="bottom",
        )
        
        assert caption.text == "测试"
        assert len(caption.words) == 1
        assert caption.style == CaptionStyle.VIRAL
        assert caption.position == "bottom"


class TestCaptionConfig:
    """Test caption config"""

    def test_default_config(self):
        """Test default config"""
        config = CaptionConfig()
        
        assert config.style == CaptionStyle.VIRAL
        assert config.font_family == "PingFang SC"
        assert config.base_font_size == 48

    def test_custom_config(self):
        """Test custom config"""
        config = CaptionConfig(
            style=CaptionStyle.MINIMAL,
            base_font_size=24,
            primary_color="#FFFFFF",
        )
        
        assert config.style == CaptionStyle.MINIMAL
        assert config.base_font_size == 24
        assert config.primary_color == "#FFFFFF"


class TestCaptionGenerator:
    """Test caption generator"""

    def test_init(self):
        """Test initialization"""
        generator = CaptionGenerator()
        
        assert generator.config.style == CaptionStyle.VIRAL

    def test_init_custom_config(self):
        """Test custom config initialization"""
        config = CaptionConfig(
            style=CaptionStyle.SUBTITLE,
            base_font_size=28,
        )
        
        generator = CaptionGenerator(config)
        
        assert generator.config.style == CaptionStyle.SUBTITLE
        assert generator.config.base_font_size == 28

    def test_word_segmentation(self):
        """Test word segmentation"""
        generator = CaptionGenerator()
        
        words = generator._segment_words("你好世界")
        
        assert isinstance(words, list)
