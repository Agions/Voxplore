"""
安全的字幕提取模块
使用安全工具确保命令执行安全
"""

import os
import logging
from typing import Optional

from .subtitle_extractor import (
    SubtitleExtractionResult,
    OCRSubtitleExtractor,
    SpeechSubtitleExtractor
)
from ...utils.security import (
    SecureExecutor,
    PathValidator,
    InputSanitizer,
    SecurityError,
    ALLOWED_VIDEO_EXTENSIONS
)

logger = logging.getLogger(__name__)


class SecureSubtitleExtractor:
    """安全的字幕提取器 - 包装基础提取器并添加安全检查"""

    def __init__(self, base_dir: str = None):
        """
        初始化安全字幕提取器

        Args:
            base_dir: 允许访问的基础目录
        """
        self.base_dir = base_dir or os.path.expanduser("~/Videos")
        self.sanitizer = InputSanitizer()

        # 初始化安全执行器
        self.executor = SecureExecutor(
            allowed_base_dirs=[self.base_dir],
            allowed_commands=['ffmpeg', 'ffprobe']
        )

        # 路径验证器
        self.path_validator = PathValidator([self.base_dir])

    def _validate_video_path(self, video_path: str) -> str:
        """
        验证视频路径安全性

        Args:
            video_path: 视频路径

        Returns:
            验证通过的文件路径

        Raises:
            SecurityError: 路径验证失败
        """
        # 清理输入
        clean_path = self.sanitizer.sanitize_path(video_path)

        # 验证路径
        result = self.path_validator.validate(clean_path)
        if not result.passed:
            raise SecurityError(f"视频路径验证失败: {result.message}")

        # 验证扩展名
        ext_result = self.path_validator.validate_extension(
            clean_path,
            ALLOWED_VIDEO_EXTENSIONS
        )
        if not ext_result.passed:
            raise SecurityError(f"视频格式不支持: {ext_result.message}")

        # 检查文件存在
        if not os.path.exists(clean_path):
            raise SecurityError(f"视频文件不存在: {clean_path}")

        return clean_path

    def extract(
        self,
        video_path: str,
        method: str = "whisper",
        language: str = "zh",
        api_key: Optional[str] = None
    ) -> SubtitleExtractionResult:
        """
        安全提取字幕

        Args:
            video_path: 视频路径
            method: 提取方法 ("whisper" / "ocr" / "both")
            language: 目标语言
            api_key: API 密钥

        Returns:
            字幕提取结果

        Raises:
            SecurityError: 安全验证失败
        """
        # 安全验证
        safe_path = self._validate_video_path(video_path)

        # 清理语言参数
        language = self.sanitizer.sanitize_text(language, max_length=10)

        # 调用基础提取器
        base_extractor = SpeechSubtitleExtractor(api_key=api_key)

        try:
            result = base_extractor.extract(
                video_path=safe_path,
                language=language
            )
            logger.info(f"字幕提取成功: {safe_path}")
            return result

        except SecurityError:
            raise
        except Exception as e:
            logger.error(f"字幕提取失败: {e}")
            raise SecurityError(f"字幕提取失败: {e}")

    def extract_with_ocr(
        self,
        video_path: str,
        api_key: Optional[str] = None
    ) -> SubtitleExtractionResult:
        """安全的 OCR 字幕提取"""
        safe_path = self._validate_video_path(video_path)

        base_extractor = OCRSubtitleExtractor(api_key=api_key)

        try:
            return base_extractor.extract(video_path=safe_path)
        except Exception as e:
            logger.error(f"OCR 字幕提取失败: {e}")
            raise SecurityError(f"OCR 提取失败: {e}")

    def extract_both(
        self,
        video_path: str,
        whisper_api_key: Optional[str] = None,
        ocr_api_key: Optional[str] = None,
        language: str = "zh"
    ) -> SubtitleExtractionResult:
        """安全地结合 OCR 和语音识别"""
        safe_path = self._validate_video_path(video_path)

        # 提取 OCR 字幕
        ocr_result = self.extract_with_ocr(safe_path, ocr_api_key)

        # 提取语音字幕
        whisper_result = self.extract(safe_path, "whisper", language, whisper_api_key)

        # 合并结果（简单的合并策略）
        all_segments = ocr_result.segments + whisper_result.segments
        all_segments.sort(key=lambda x: x.start)

        return SubtitleExtractionResult(
            video_path=safe_path,
            duration=whisper_result.duration,
            segments=all_segments,
            full_text=whisper_result.full_text,
            language=language,
            method="both"
        )


# 便捷函数
def create_secure_extractor(base_dir: str = None) -> SecureSubtitleExtractor:
    """创建安全的字幕提取器"""
    return SecureSubtitleExtractor(base_dir=base_dir)
