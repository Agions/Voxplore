"""
字幕翻译器 (Subtitle Translator)

将字幕从一种语言翻译成另一种语言，支持多种翻译引擎。

支持的翻译引擎：
1. OpenAI GPT（推荐，高质量）
2. DeepL API（高质量，适合欧洲语言）
3. Google Translate（免费，但有限制）
"""

import os
import logging
from typing import Dict, List, Optional

from .subtitle_types import SubtitleSegment, SubtitleExtractionResult


logger = logging.getLogger(__name__)


class SubtitleTranslator:
    """
    字幕翻译器

    将字幕从一种语言翻译成另一种语言，支持多种翻译引擎。
    """

    # 支持的目标语言
    SUPPORTED_LANGUAGES = {
        "zh": "中文",
        "en": "英语",
        "ja": "日语",
        "ko": "韩语",
        "fr": "法语",
        "de": "德语",
        "es": "西班牙语",
        "pt": "葡萄牙语",
        "it": "意大利语",
        "ru": "俄语",
        "ar": "阿拉伯语",
        "hi": "印地语",
        "th": "泰语",
        "vi": "越南语",
        "id": "印尼语",
        "ms": "马来语",
        "tr": "土耳其语",
        "pl": "波兰语",
        "nl": "荷兰语",
        "uk": "乌克兰语",
    }

    def __init__(self, api_key: Optional[str] = None,
                 provider: str = "openai"):
        """
        Args:
            api_key: API 密钥
            provider: 翻译引擎 "openai" / "deepl" / "google"
        """
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._deepl_key = os.getenv("DEEPL_API_KEY")
        self._provider = provider

    def translate(self,
                 subtitle_result: SubtitleExtractionResult,
                 target_lang: str = "en",
                 source_lang: str = "auto",
                 batch_size: int = 20) -> SubtitleExtractionResult:
        """
        翻译字幕

        Args:
            subtitle_result: 原始字幕结果
            target_lang: 目标语言代码
            source_lang: 源语言代码，"auto" 表示自动检测
            batch_size: 每批处理的字幕片段数

        Returns:
            翻译后的字幕结果
        """
        if not subtitle_result.segments:
            return subtitle_result

        # 创建翻译结果
        translated = SubtitleExtractionResult(
            video_path=subtitle_result.video_path,
            duration=subtitle_result.duration,
            language=target_lang,
            method=f"translated_{subtitle_result.method}",
        )

        # 分批翻译
        all_texts = [seg.text for seg in subtitle_result.segments]

        if self._provider == "openai":
            translated_texts = self._translate_openai(
                all_texts, target_lang, source_lang, batch_size
            )
        elif self._provider == "deepl":
            translated_texts = self._translate_deepl(
                all_texts, target_lang, source_lang
            )
        elif self._provider == "google":
            translated_texts = self._translate_google(
                all_texts, target_lang, source_lang
            )
        else:
            raise ValueError(f"不支持的翻译引擎: {self._provider}")

        # 构建翻译后的字幕片段
        for i, seg in enumerate(subtitle_result.segments):
            translated.segments.append(SubtitleSegment(
                start=seg.start,
                end=seg.end,
                text=translated_texts[i] if i < len(translated_texts) else seg.text,
                confidence=seg.confidence,
                source=f"translated_{seg.source}",
            ))

        translated.full_text = " ".join(t.text for t in translated.segments)
        return translated

    def _translate_openai(self, texts: List[str],
                         target_lang: str,
                         source_lang: str,
                         batch_size: int) -> List[str]:
        """使用 OpenAI GPT 翻译"""
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)
        target_name = self.SUPPORTED_LANGUAGES.get(target_lang, target_lang)
        source_name = self.SUPPORTED_LANGUAGES.get(source_lang, source_lang) if source_lang != "auto" else "源语言"

        translated = []

        # 分批处理
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            # 构建提示词
            if source_lang == "auto":
                prompt = f"""将以下{len(batch)}段字幕翻译成{target_name}。
只返回翻译后的文本，每行一段，不要加任何解释或序号。

原文:
{chr(10).join(batch)}"""
            else:
                prompt = f"""将以下{len(batch)}段从{source_name}翻译成{target_name}。
只返回翻译后的文本，每行一段，不要加任何解释或序号。

原文:
{chr(10).join(batch)}"""

            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=2000,
                )

                result_text = response.choices[0].message.content.strip()

                # 解析结果（每行一段）
                lines = result_text.split('\n')
                for line in lines:
                    line = line.strip()
                    # 去除可能的序号
                    if line and line[0].isdigit() and '.' in line[:3]:
                        line = line.split('.', 1)[-1].strip()
                    translated.append(line)

            except Exception as e:
                logger.error(f"OpenAI 翻译批次 {i//batch_size + 1} 失败: {e}")
                # 失败时返回原文
                translated.extend(batch)

        # 确保数量一致
        while len(translated) < len(texts):
            translated.append(texts[len(translated)])

        return translated[:len(texts)]

    def _translate_deepl(self, texts: List[str],
                        target_lang: str,
                        source_lang: str) -> List[str]:
        """使用 DeepL API 翻译"""
        import deepl

        # DeepL 语言代码映射
        deepl_lang_map = {
            "zh": "ZH", "en": "EN", "ja": "JA", "ko": "KO",
            "fr": "FR", "de": "DE", "es": "ES", "pt": "PT",
            "it": "IT", "ru": "RU", "pl": "PL", "nl": "NL",
        }

        target_code = deepl_lang_map.get(target_lang, target_lang.upper())

        try:
            translator = deepl.Translator(self._deepl_key)

            # DeepL 有段落数限制，需要合并
            combined_text = "\n".join(f"[{i}] {t}" for i, t in enumerate(texts))

            if source_lang == "auto":
                result = translator.translate_text(combined_text, target_lang=target_code)
            else:
                source_code = deepl_lang_map.get(source_lang, source_lang.upper())
                result = translator.translate_text(combined_text, source_lang=source_code, target_lang=target_code)

            # 解析结果
            result_text = result.text
            translated = []
            for i in range(len(texts)):
                marker = f"[{i}]"
                start = result_text.find(marker)
                if start != -1:
                    end = result_text.find(f"[{i+1}]", start) if i + 1 < len(texts) else len(result_text)
                    text = result_text[start + len(marker):end].strip()
                    translated.append(text)
                else:
                    translated.append(texts[i])

            return translated

        except Exception as e:
            logger.error(f"DeepL 翻译失败: {e}")
            return texts

    def _translate_google(self, texts: List[str],
                          target_lang: str,
                          source_lang: str) -> List[str]:
        """使用 Google Translate 翻译"""
        try:
            from googletrans import Translator
        except ImportError:
            try:
                from deep_translator import GoogleTranslator
            except ImportError:
                raise ImportError("Google 翻译需要安装: pip install googletrans 或 pip install deep-translator")

        try:
            # 尝试使用 deep_translator（googletrans 已停止维护）
            translator = GoogleTranslator(source=source_lang, target=target_lang)

            translated = []
            for text in texts:
                try:
                    result = translator.translate(text)
                    translated.append(result)
                except Exception as e:
                    logger.error(f"Google 翻译失败 '{text[:20]}...': {e}")
                    translated.append(text)

            return translated

        except ImportError:
            # 回退到 googletrans
            translator = Translator()

            translated = []
            for text in texts:
                try:
                    result = translator.translate(text, src=source_lang, dest=target_lang)
                    translated.append(result.text)
                except Exception as e:
                    logger.error(f"Google 翻译失败 '{text[:20]}...': {e}")
                    translated.append(text)

            return translated

    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表"""
        return self.SUPPORTED_LANGUAGES.copy()
