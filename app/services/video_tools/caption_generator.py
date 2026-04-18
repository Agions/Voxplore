"""
Caption Generator - 动态字幕生成器
生成具有"爆款特征"的动态字幕

特性:
- 逐词高亮（Karaoke 风格）
- 关键词自动放大和变色
- 情绪词自动识别和强调
- 支持多种字幕样式预设
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class CaptionStyle(Enum):
    """字幕样式预设"""
    VIRAL = "viral"           # 爆款风格：大字、高亮、动态
    MINIMAL = "minimal"       # 简约风格：小字、纯色
    SUBTITLE = "subtitle"     # 传统字幕：底部居中
    FLOATING = "floating"     # 浮动风格：跟随主体


class EmotionLevel(Enum):
    """情绪等级"""
    NEUTRAL = 0    # 中性
    LOW = 1        # 低强度
    MEDIUM = 2     # 中等强度
    HIGH = 3       # 高强度


@dataclass
class Word:
    """单词/字符数据"""
    text: str           # 文本内容
    start_time: float   # 开始时间（秒）
    end_time: float     # 结束时间（秒）
    is_keyword: bool    # 是否为关键词
    emotion: EmotionLevel  # 情绪等级


@dataclass
class Caption:
    """字幕条目"""
    text: str                # 完整文本
    start_time: float        # 开始时间
    end_time: float          # 结束时间
    words: List[Word]        # 分词列表
    style: CaptionStyle      # 样式
    position: str            # 位置（'top', 'center', 'bottom'）


@dataclass
class CaptionConfig:
    """字幕配置"""
    style: CaptionStyle = CaptionStyle.VIRAL
    font_family: str = "PingFang SC"
    base_font_size: int = 48
    keyword_font_size: int = 64
    primary_color: str = "#FFFFFF"
    keyword_color: str = "#F43F5E"  # 玫瑰红
    emotion_color: str = "#10B981"  # 翠绿色
    stroke_color: str = "#000000"
    stroke_width: int = 3
    position: str = "center"
    enable_word_highlight: bool = True  # 启用逐词高亮


class CaptionGenerator:
    """
    字幕生成器
    
    自动生成具有爆款特征的动态字幕
    """
    
    # 关键词词库（中文）
    KEYWORDS_CN = {
        '爆款', '惊人', '震惊', '必看', '超级', '绝对', '完美',
        '史上最', '第一', '最强', '顶级', '神级', '牛逼', '炸裂',
        '重要', '关键', '核心', '秘密', '揭秘', '真相', '内幕'
    }
    
    # 情绪词词库
    EMOTION_WORDS_HIGH = {
        '哇', '天啊', '卧槽', '牛逼', '绝了', '太强了', '无敌',
        '震撼', '惊艳', '炸裂', '爆炸', '疯狂'
    }
    
    EMOTION_WORDS_MEDIUM = {
        '厉害', '不错', '很好', '赞', '棒', '强',
        '惊讶', '意外', '有趣'
    }
    
    def __init__(self, config: Optional[CaptionConfig] = None):
        """
        初始化字幕生成器
        
        Args:
            config: 字幕配置（如果为 None，使用默认爆款风格）
        """
        self.config = config or CaptionConfig()
    
    def generate_from_text(
        self,
        text: str,
        start_time: float = 0.0,
        duration: Optional[float] = None
    ) -> Caption:
        """
        从文本生成字幕
        
        Args:
            text: 文本内容
            start_time: 开始时间
            duration: 持续时长（如果为 None，自动计算）
            
        Returns:
            字幕对象
        """
        # 分词
        words = self._segment_words(text)
        
        # 计算时长
        if duration is None:
            # 按照平均语速估算：180 字/分钟 (中文)
            chars_per_second = 3.0
            duration = len(text) / chars_per_second
        
        # 为每个词分配时间
        word_objects = self._assign_timestamps(
            words,
            start_time,
            start_time + duration
        )
        
        # 识别关键词和情绪词
        word_objects = self._mark_keywords_and_emotions(word_objects)
        
        return Caption(
            text=text,
            start_time=start_time,
            end_time=start_time + duration,
            words=word_objects,
            style=self.config.style,
            position=self.config.position
        )
    
    def generate_from_transcript(
        self,
        transcript: List[Dict[str, any]]
    ) -> List[Caption]:
        """
        从转录结果生成字幕
        
        Args:
            transcript: 转录数据，格式：
                [
                    {
                        'text': '你好',
                        'start': 0.0,
                        'end': 0.5,
                        'words': [
                            {'word': '你', 'start': 0.0, 'end': 0.25},
                            {'word': '好', 'start': 0.25, 'end': 0.5}
                        ]
                    },
                    ...
                ]
                
        Returns:
            字幕列表
        """
        captions = []
        
        for segment in transcript:
            words = []
            
            # 如果有逐词时间戳
            if 'words' in segment and segment['words']:
                for word_data in segment['words']:
                    word = Word(
                        text=word_data['word'],
                        start_time=word_data['start'],
                        end_time=word_data['end'],
                        is_keyword=False,
                        emotion=EmotionLevel.NEUTRAL
                    )
                    words.append(word)
            else:
                # 如果没有逐词时间戳，均分
                words = self._assign_timestamps(
                    list(segment['text']),
                    segment['start'],
                    segment['end']
                )
            
            # 标记关键词和情绪
            words = self._mark_keywords_and_emotions(words)
            
            caption = Caption(
                text=segment['text'],
                start_time=segment['start'],
                end_time=segment['end'],
                words=words,
                style=self.config.style,
                position=self.config.position
            )
            
            captions.append(caption)
        
        return captions
    
    def to_ass_format(self, captions: List[Caption], output_path: str) -> None:
        """
        导出为 ASS 字幕格式（支持高级样式）
        
        Args:
            captions: 字幕列表
            output_path: 输出文件路径
        """
        output_path = Path(output_path)
        
        # ASS 文件头
        ass_content = self._generate_ass_header()
        
        # 添加字幕条目
        for caption in captions:
            if self.config.enable_word_highlight:
                # 逐词高亮版本
                ass_content += self._generate_ass_karaoke(caption)
            else:
                # 普通版本
                ass_content += self._generate_ass_simple(caption)
        
        # 写入文件
        output_path.write_text(ass_content, encoding='utf-8-sig')
    
    def to_srt_format(self, captions: List[Caption], output_path: str) -> None:
        """
        导出为 SRT 字幕格式（基础格式）
        
        Args:
            captions: 字幕列表
            output_path: 输出文件路径
        """
        output_path = Path(output_path)
        
        srt_content = []
        
        for i, caption in enumerate(captions, start=1):
            # 序号
            srt_content.append(str(i))
            
            # 时间轴
            start = self._format_srt_time(caption.start_time)
            end = self._format_srt_time(caption.end_time)
            srt_content.append(f"{start} --> {end}")
            
            # 文本
            srt_content.append(caption.text)
            
            # 空行
            srt_content.append("")
        
        output_path.write_text('\n'.join(srt_content), encoding='utf-8')
    
    def _segment_words(self, text: str) -> List[str]:
        """
        分词（简化版中文分词）
        
        实际使用时建议集成 jieba 或其他分词库
        """
        # 简化版：按字符分割
        return list(text)
    
    def _assign_timestamps(
        self,
        words: List[str],
        start_time: float,
        end_time: float
    ) -> List[Word]:
        """为每个词分配时间戳"""
        duration = end_time - start_time
        word_count = len(words)
        
        if word_count == 0:
            return []
        
        time_per_word = duration / word_count
        
        word_objects = []
        for i, word_text in enumerate(words):
            word_start = start_time + i * time_per_word
            word_end = word_start + time_per_word
            
            word = Word(
                text=word_text,
                start_time=word_start,
                end_time=word_end,
                is_keyword=False,
                emotion=EmotionLevel.NEUTRAL
            )
            word_objects.append(word)
        
        return word_objects
    
    def _mark_keywords_and_emotions(self, words: List[Word]) -> List[Word]:
        """标记关键词和情绪词"""
        full_text = ''.join(w.text for w in words)
        
        for word in words:
            # 检查是否为关键词
            if word.text in self.KEYWORDS_CN:
                word.is_keyword = True
            
            # 检查是否为情绪词
            if word.text in self.EMOTION_WORDS_HIGH:
                word.emotion = EmotionLevel.HIGH
            elif word.text in self.EMOTION_WORDS_MEDIUM:
                word.emotion = EmotionLevel.MEDIUM
            
            # 检查是否在关键词短语中
            for keyword in self.KEYWORDS_CN:
                if keyword in full_text and word.text in keyword:
                    word.is_keyword = True
        
        return words
    
    def _generate_ass_header(self) -> str:
        """生成 ASS 文件头"""
        return f"""[Script Info]
Title: Viral Caption
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{self.config.font_family},{self.config.base_font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{self.config.stroke_width},0,2,10,10,10,1
Style: Keyword,{self.config.font_family},{self.config.keyword_font_size},&H00{self._hex_to_ass(self.config.keyword_color)},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{self.config.stroke_width},0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    def _generate_ass_karaoke(self, caption: Caption) -> str:
        """生成带逐词高亮的 ASS 字幕"""
        lines = []
        
        for word in caption.words:
            start = self._format_ass_time(word.start_time)
            end = self._format_ass_time(word.end_time)
            
            # 选择样式
            style = "Keyword" if word.is_keyword else "Default"
            
            # 选择颜色
            color = self._get_word_color(word)
            
            # 构建文本（带颜色标记）
            text = f"{{\\c&H{self._hex_to_ass(color)}&}}{word.text}"
            
            lines.append(f"Dialogue: 0,{start},{end},{style},,0,0,0,,{text}\n")
        
        return ''.join(lines)
    
    def _generate_ass_simple(self, caption: Caption) -> str:
        """生成简单版 ASS 字幕"""
        start = self._format_ass_time(caption.start_time)
        end = self._format_ass_time(caption.end_time)
        
        return f"Dialogue: 0,{start},{end},Default,,0,0,0,,{caption.text}\n"
    
    def _get_word_color(self, word: Word) -> str:
        """获取词的颜色"""
        if word.is_keyword:
            return self.config.keyword_color
        elif word.emotion in [EmotionLevel.HIGH, EmotionLevel.MEDIUM]:
            return self.config.emotion_color
        else:
            return self.config.primary_color
    
    def _format_ass_time(self, seconds: float) -> str:
        """格式化 ASS 时间：h:mm:ss.cc"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centiseconds = int((seconds % 1) * 100)
        
        return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"
    
    def _format_srt_time(self, seconds: float) -> str:
        """格式化 SRT 时间：hh:mm:ss,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    def _hex_to_ass(self, hex_color: str) -> str:
        """
        将 HEX 颜色转换为 ASS 格式（BGR）
        
        Example: #F43F5E -> 5E3FF4
        """
        hex_color = hex_color.lstrip('#')
        
        # HEX: RRGGBB -> ASS: BBGGRR
        r = hex_color[0:2]
        g = hex_color[2:4]
        b = hex_color[4:6]
        
        return f"{b}{g}{r}".upper()


# 使用示例
if __name__ == '__main__':
    # 创建字幕生成器
    generator = CaptionGenerator()
    
    # 示例1：从文本生成
    caption = generator.generate_from_text(
        "这个方法太牛逼了！震惊全网的爆款技巧揭秘",
        start_time=0.0
    )
    
    print(f"字幕文本: {caption.text}")
    print(f"关键词数量: {sum(1 for w in caption.words if w.is_keyword)}")
    
    # 示例2：导出字幕
    # generator.to_srt_format([caption], 'output.srt')
    # generator.to_ass_format([caption], 'output.ass')
