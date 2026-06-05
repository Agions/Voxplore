"""
SceneFab 多语言时长适配模块

功能：
1. 多语言翻译（DeepL API）
2. 时长感知的脚本压缩/扩展
3. 语速模型（各语言平均语速）
4. 画面调整建议

语言支持：
- 中文（zh）- 基准
- 英文（en）- 比中文长 20%-30%
- 日文（ja）- 比中文短 10%-15%
- 韩文（ko）- 比中文短 10%-15%
- 西班牙文（es）- 比中文长 15%-25%

技术栈：
- DeepL API: 翻译
- 自定义 length regulator: 时长调节
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class Language(str, Enum):
    """支持的语言"""
    ZH = "zh"  # 中文
    EN = "en"  # 英文
    JA = "ja"  # 日文
    KO = "ko"  # 韩文
    ES = "es"  # 西班牙文


@dataclass
class LanguageConfig:
    """语言配置"""
    language: Language
    display_name: str
    speed_coefficient: float  # 相对于中文的语速系数
    chars_per_second: float  # 平均每秒字符数
    deepl_code: str  # DeepL 语言代码
    tts_voice: str = ""  # TTS 语音名称


@dataclass
class TranslationResult:
    """翻译结果"""
    original_text: str
    translated_text: str
    source_language: Language
    target_language: Language
    original_duration: float  # 原始时长（秒）
    estimated_duration: float  # 预估时长（秒）
    duration_difference: float  # 时长差异（秒）
    duration_difference_percent: float  # 时长差异百分比
    needs_adjustment: bool  # 是否需要调整
    adjustment_suggestions: list[str] = field(default_factory=list)


@dataclass
class DurationAdjustment:
    """时长调整"""
    original_text: str
    adjusted_text: str
    target_duration: float  # 目标时长（秒）
    original_duration: float  # 原始时长（秒）
    adjustment_type: str  # "compress", "expand", "none"
    adjustment_ratio: float  # 调整比例
    frame_adjustments: list[dict[str, Any]] = field(default_factory=list)  # 画面调整建议


@dataclass
class MultiLanguageResult:
    """多语言适配结果"""
    original_script: str
    original_language: Language
    translations: dict[str, TranslationResult] = field(default_factory=dict)
    adjustments: dict[str, DurationAdjustment] = field(default_factory=dict)
    processing_time: str = ""
    adapter_version: str = "1.0.0"


class MultiLanguageAdapter:
    """
    多语言时长适配器

    用于将解说稿翻译成多种语言，并自动调整时长以匹配原始视频。

    使用方法：
        adapter = MultiLanguageAdapter(deepl_api_key="your-api-key")
        result = adapter.adapt(
            script="中文解说稿...",
            target_duration=180.0,
            target_languages=[Language.EN, Language.JA, Language.KO],
        )
        for lang, translation in result.translations.items():
            print(f"{lang}: {translation.estimated_duration:.1f}秒")
    """

    # 语言配置
    LANGUAGE_CONFIGS = {
        Language.ZH: LanguageConfig(
            language=Language.ZH,
            display_name="中文",
            speed_coefficient=1.0,
            chars_per_second=4.0,
            deepl_code="ZH",
        ),
        Language.EN: LanguageConfig(
            language=Language.EN,
            display_name="英文",
            speed_coefficient=0.75,  # 英文比中文慢 25%
            chars_per_second=3.0,
            deepl_code="EN",
        ),
        Language.JA: LanguageConfig(
            language=Language.JA,
            display_name="日文",
            speed_coefficient=0.85,  # 日文比中文慢 15%
            chars_per_second=3.5,
            deepl_code="JA",
        ),
        Language.KO: LanguageConfig(
            language=Language.KO,
            display_name="韩文",
            speed_coefficient=0.85,  # 韩文比中文慢 15%
            chars_per_second=3.5,
            deepl_code="KO",
        ),
        Language.ES: LanguageConfig(
            language=Language.ES,
            display_name="西班牙文",
            speed_coefficient=0.80,  # 西班牙文比中文慢 20%
            chars_per_second=3.2,
            deepl_code="ES",
        ),
    }

    # 时长差异阈值
    DURATION_THRESHOLD = 0.10  # 10%

    def __init__(self, deepl_api_key: str | None = None):
        """
        初始化多语言适配器

        Args:
            deepl_api_key: DeepL API 密钥
        """
        self.deepl_api_key = deepl_api_key
        self._init_deepl_client()
        logger.info("MultiLanguageAdapter 初始化完成")

    def _init_deepl_client(self):
        """初始化 DeepL 客户端"""
        if self.deepl_api_key:
            try:
                import httpx
                self.deepl_client = httpx.Client(timeout=60.0)
            except Exception as e:
                logger.warning(f"DeepL 客户端初始化失败: {e}")
                self.deepl_client = None
        else:
            self.deepl_client = None

    def adapt(
        self,
        script: str,
        target_duration: float,
        source_language: Language = Language.ZH,
        target_languages: list[Language] | None = None,
    ) -> MultiLanguageResult:
        """
        适配多语言版本

        Args:
            script: 原始解说稿
            target_duration: 目标时长（秒）
            source_language: 源语言
            target_languages: 目标语言列表

        Returns:
            MultiLanguageResult: 适配结果
        """
        logger.info(f"开始多语言适配: 目标时长={target_duration}秒")

        # 默认目标语言
        if target_languages is None:
            target_languages = [Language.EN, Language.JA, Language.KO]

        # 计算原始时长
        original_duration = self._estimate_duration(script, source_language)

        # 翻译到各语言
        translations = {}
        for target_lang in target_languages:
            translation = self._translate_and_estimate(
                script, source_language, target_lang, target_duration
            )
            translations[target_lang.value] = translation

        # 生成调整建议
        adjustments = {}
        for lang, translation in translations.items():
            if translation.needs_adjustment:
                adjustment = self._generate_adjustment(
                    translation.translated_text,
                    target_duration,
                    Language(lang),
                )
                adjustments[lang] = adjustment

        result = MultiLanguageResult(
            original_script=script,
            original_language=source_language,
            translations=translations,
            adjustments=adjustments,
        )

        logger.info(f"多语言适配完成: {len(translations)} 种语言")
        return result

    def _estimate_duration(self, text: str, language: Language) -> float:
        """
        估算文本时长

        Args:
            text: 文本
            language: 语言

        Returns:
            float: 预估时长（秒）
        """
        config = self.LANGUAGE_CONFIGS.get(language, self.LANGUAGE_CONFIGS[Language.ZH])
        char_count = len(text)
        return char_count / config.chars_per_second

    def _translate_and_estimate(
        self,
        text: str,
        source_language: Language,
        target_language: Language,
        target_duration: float,
    ) -> TranslationResult:
        """
        翻译并估算时长

        Args:
            text: 原始文本
            source_language: 源语言
            target_language: 目标语言
            target_duration: 目标时长

        Returns:
            TranslationResult: 翻译结果
        """
        # 翻译
        translated_text = self._translate(text, source_language, target_language)

        # 估算时长
        original_duration = self._estimate_duration(text, source_language)
        estimated_duration = self._estimate_duration(translated_text, target_language)

        # 计算差异
        duration_difference = estimated_duration - target_duration
        duration_difference_percent = duration_difference / target_duration if target_duration > 0 else 0

        # 判断是否需要调整
        needs_adjustment = abs(duration_difference_percent) > self.DURATION_THRESHOLD

        # 生成调整建议
        adjustment_suggestions = []
        if needs_adjustment:
            if duration_difference > 0:
                adjustment_suggestions.append(f"翻译后时长超出 {abs(duration_difference_percent)*100:.1f}%，建议压缩文案")
            else:
                adjustment_suggestions.append(f"翻译后时长不足 {abs(duration_difference_percent)*100:.1f}%，建议扩展文案")

        return TranslationResult(
            original_text=text,
            translated_text=translated_text,
            source_language=source_language,
            target_language=target_language,
            original_duration=original_duration,
            estimated_duration=estimated_duration,
            duration_difference=duration_difference,
            duration_difference_percent=duration_difference_percent,
            needs_adjustment=needs_adjustment,
            adjustment_suggestions=adjustment_suggestions,
        )

    def _translate(
        self,
        text: str,
        source_language: Language,
        target_language: Language,
    ) -> str:
        """
        翻译文本

        Args:
            text: 原始文本
            source_language: 源语言
            target_language: 目标语言

        Returns:
            str: 翻译后的文本
        """
        if not self.deepl_client or not self.deepl_api_key:
            logger.warning("DeepL API 未配置，返回模拟翻译")
            return self._mock_translate(text, target_language)

        try:
            source_config = self.LANGUAGE_CONFIGS[source_language]
            target_config = self.LANGUAGE_CONFIGS[target_language]

            # 调用 DeepL API
            url = "https://api-free.deepl.com/v2/translate"
            headers = {
                "Authorization": f"DeepL-Auth-Key {self.deepl_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "text": [text],
                "source_lang": source_config.deepl_code,
                "target_lang": target_config.deepl_code,
            }

            response = self.deepl_client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

            return result["translations"][0]["text"]

        except Exception as e:
            logger.error(f"DeepL 翻译失败: {e}")
            return self._mock_translate(text, target_language)

    def _mock_translate(self, text: str, target_language: Language) -> str:
        """
        模拟翻译（DeepL API 不可用时）

        Args:
            text: 原始文本
            target_language: 目标语言

        Returns:
            str: 模拟翻译结果
        """
        # 简单的模拟翻译
        if target_language == Language.EN:
            return f"[English translation of: {text[:50]}...]"
        elif target_language == Language.JA:
            return f"[日本語翻訳: {text[:50]}...]"
        elif target_language == Language.KO:
            return f"[한국어 번역: {text[:50]}...]"
        elif target_language == Language.ES:
            return f"[Traducción al español: {text[:50]}...]"
        else:
            return text

    def _generate_adjustment(
        self,
        text: str,
        target_duration: float,
        language: Language,
    ) -> DurationAdjustment:
        """
        生成时长调整

        Args:
            text: 文本
            target_duration: 目标时长
            language: 语言

        Returns:
            DurationAdjustment: 时长调整
        """
        original_duration = self._estimate_duration(text, language)
        duration_difference = original_duration - target_duration

        # 判断调整类型
        if abs(duration_difference) < self.DURATION_THRESHOLD * target_duration:
            adjustment_type = "none"
            adjustment_ratio = 1.0
            adjusted_text = text
        elif duration_difference > 0:
            # 需要压缩
            adjustment_type = "compress"
            adjustment_ratio = target_duration / original_duration
            adjusted_text = self._compress_text(text, adjustment_ratio)
        else:
            # 需要扩展
            adjustment_type = "expand"
            adjustment_ratio = target_duration / original_duration
            adjusted_text = self._expand_text(text, adjustment_ratio)

        # 生成画面调整建议
        frame_adjustments = self._generate_frame_adjustments(
            original_duration, target_duration, adjustment_type
        )

        return DurationAdjustment(
            original_text=text,
            adjusted_text=adjusted_text,
            target_duration=target_duration,
            original_duration=original_duration,
            adjustment_type=adjustment_type,
            adjustment_ratio=adjustment_ratio,
            frame_adjustments=frame_adjustments,
        )

    def _compress_text(self, text: str, ratio: float) -> str:
        """
        压缩文本

        Args:
            text: 原始文本
            ratio: 压缩比例

        Returns:
            str: 压缩后的文本
        """
        # 简单的压缩策略：删除部分句子
        sentences = text.split("。")
        keep_count = max(1, int(len(sentences) * ratio))
        compressed_sentences = sentences[:keep_count]
        return "。".join(compressed_sentences)

    def _expand_text(self, text: str, ratio: float) -> str:
        """
        扩展文本

        Args:
            text: 原始文本
            ratio: 扩展比例

        Returns:
            str: 扩展后的文本
        """
        # 简单的扩展策略：添加连接词
        sentences = text.split("。")
        expanded_sentences = []
        connectors = ["此外", "同时", "另外", "而且", "并且"]

        for i, sentence in enumerate(sentences):
            expanded_sentences.append(sentence)
            if i < len(sentences) - 1:
                connector = connectors[i % len(connectors)]
                expanded_sentences.append(f"，{connector}")

        return "。".join(expanded_sentences)

    def _generate_frame_adjustments(
        self,
        original_duration: float,
        target_duration: float,
        adjustment_type: str,
    ) -> list[dict[str, Any]]:
        """
        生成画面调整建议

        Args:
            original_duration: 原始时长
            target_duration: 目标时长
            adjustment_type: 调整类型

        Returns:
            list: 画面调整建议
        """
        adjustments = []

        if adjustment_type == "compress":
            # 压缩建议
            speed_ratio = original_duration / target_duration
            adjustments.append({
                "type": "speed_up",
                "ratio": speed_ratio,
                "description": f"将视频加速 {speed_ratio:.2f} 倍",
            })
        elif adjustment_type == "expand":
            # 扩展建议
            speed_ratio = original_duration / target_duration
            adjustments.append({
                "type": "slow_down",
                "ratio": speed_ratio,
                "description": f"将视频减速至 {speed_ratio:.2f} 倍",
            })
            adjustments.append({
                "type": "add_pause",
                "description": "在关键节点添加停顿",
            })

        return adjustments


def adapt_multilanguage(
    script: str,
    target_duration: float,
    source_language: Language = Language.ZH,
    target_languages: list[Language] | None = None,
    deepl_api_key: str | None = None,
) -> MultiLanguageResult:
    """
    便捷函数：多语言时长适配

    Args:
        script: 原始解说稿
        target_duration: 目标时长（秒）
        source_language: 源语言
        target_languages: 目标语言列表
        deepl_api_key: DeepL API 密钥

    Returns:
        MultiLanguageResult: 适配结果
    """
    adapter = MultiLanguageAdapter(deepl_api_key=deepl_api_key)
    return adapter.adapt(
        script=script,
        target_duration=target_duration,
        source_language=source_language,
        target_languages=target_languages,
    )
