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


class TestCaptionGeneratorMethods:
    """Test CaptionGenerator methods"""

    def test_generate_from_text_returns_captions(self):
        """Test generate_from_text returns a Caption"""
        generator = CaptionGenerator()
        caption = generator.generate_from_text("你好世界", start_time=0.0)
        assert isinstance(caption, Caption)
        assert caption.text == "你好世界"
        assert caption.start_time == 0.0

    def test_generate_from_text_with_duration(self):
        """Test generate_from_text with explicit duration"""
        generator = CaptionGenerator()
        caption = generator.generate_from_text("测试文本", start_time=5.0, duration=3.0)
        assert abs(caption.end_time - 8.0) < 0.1

    def test_generate_from_text_word_timestamps(self):
        """Test words get timestamps assigned"""
        generator = CaptionGenerator()
        caption = generator.generate_from_text("你好", start_time=0.0, duration=2.0)
        assert len(caption.words) > 0
        for w in caption.words:
            assert w.start_time < w.end_time

    def test_generate_from_transcript_returns_list(self):
        """Test generate_from_transcript returns list of captions"""
        generator = CaptionGenerator()
        transcript = [
            {"text": "第一句", "start": 0.0, "end": 1.0, "words": []},
            {"text": "第二句", "start": 1.0, "end": 2.0, "words": []},
        ]
        captions = generator.generate_from_transcript(transcript)
        assert isinstance(captions, list)
        assert len(captions) == 2
        assert captions[0].text == "第一句"
        assert captions[1].text == "第二句"

    def test_generate_from_transcript_with_word_timestamps(self):
        """Test transcript with per-word timestamps"""
        generator = CaptionGenerator()
        transcript = [
            {
                "text": "你好",
                "start": 0.0,
                "end": 0.5,
                "words": [
                    {"word": "你", "start": 0.0, "end": 0.25},
                    {"word": "好", "start": 0.25, "end": 0.5},
                ]
            }
        ]
        captions = generator.generate_from_transcript(transcript)
        assert len(captions) == 1
        assert len(captions[0].words) == 2
        assert captions[0].words[0].text == "你"
        assert captions[0].words[0].start_time == 0.0

    def test_to_srt_format(self, tmp_path):
        """Test SRT export writes valid file"""
        generator = CaptionGenerator()
        caption = generator.generate_from_text("测试", start_time=0.0, duration=1.0)
        out = tmp_path / "test.srt"
        generator.to_srt_format([caption], str(out))
        content = out.read_text(encoding="utf-8")
        assert "1" in content
        assert "00:00:00,000 --> 00:00:01,000" in content
        assert "1\n" in content  # SRT uses numbered entries

    def test_to_ass_format(self, tmp_path):
        """Test ASS export writes valid file"""
        generator = CaptionGenerator()
        caption = generator.generate_from_text("测试", start_time=0.0, duration=1.0)
        out = tmp_path / "test.ass"
        generator.to_ass_format([caption], str(out))
        content = out.read_text(encoding="utf-8-sig")
        assert "[Script Info]" in content
        assert "1\n" in content  # SRT uses numbered entries

    def test_format_srt_time(self):
        """Test _format_srt_time produces correct format"""
        generator = CaptionGenerator()
        assert generator._format_srt_time(0.0) == "00:00:00,000"
        assert generator._format_srt_time(1.5) == "00:00:01,500"
        assert generator._format_srt_time(3661.0) == "01:01:01,000"

    def test_ass_header_contains_script_info(self):
        """Test ASS header generation"""
        generator = CaptionGenerator()
        header = generator._generate_ass_header()
        assert "[Script Info]" in header
        assert "[V4+ Styles]" in header
        assert "[Events]" in header
