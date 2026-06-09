"""SceneFab core processing pipeline V2 — orchestrates all stages."""

import logging
import os
from collections.abc import Callable

from ..models.narration import EmotionType, NarrationStyle
from ..models.project import VideoProject
from .config import PipelineConfig
from .emotion_detector import EmotionPeakDetector
from .first_person_extractor import FirstPersonExtractor
from .script_generator import ScriptGenerator
from .tts_generator import TTSGenerator

logger = logging.getLogger(__name__)


class SceneFabPipeline:
    """
    SceneFab 核心处理流水线 V2
    整合所有处理步骤，支持并行和流式处理
    支持依赖注入 vision_provider
    """

    def __init__(
        self,
        config: PipelineConfig = None,  # type: ignore[assignment]
        vision_provider=None,
        tts_service=None,
        llm_service=None,
    ):
        self.config = config or PipelineConfig()
        self.extractor = FirstPersonExtractor(config, vision_provider)
        self.emotion_detector = EmotionPeakDetector(config)
        self.script_generator = ScriptGenerator(llm_service)
        self.tts_generator = TTSGenerator(tts_service)

    @staticmethod
    def _resolve_output_dir(video_path: str) -> str:
        """Derive a default output directory next to the source video."""
        return os.path.join(os.path.dirname(video_path) or ".", "output")  # type: ignore[unreachable]

    @staticmethod
    def _build_project(
        video_path: str,
        style: NarrationStyle,
        emotion: EmotionType,
    ) -> VideoProject:
        """Create a fresh VideoProject for the given source video."""
        return VideoProject(
            name=os.path.basename(video_path),
            source_videos=[video_path],
            style=style,
            emotion=emotion,
        )

    @staticmethod
    def _make_reporter(progress_callback: Callable | None) -> Callable[[float, str], None]:
        """Wrap the optional progress callback in a safe reporter closure."""

        def report(progress: float, message: str) -> None:
            if progress_callback:
                progress_callback(progress, message)

        return report

    def _extract_segments(
        self,
        video_path: str,
        report: Callable[[float, str], None],
    ):
        """Step 1: extract first-person segments from the video."""
        report(0.05, "正在分析视频...")
        segments = self.extractor.extract(
            video_path,
            use_cache=True,
            progress_callback=lambda c, t: report(
                0.05 + 0.20 * c / t if t > 0 else 0.25, "正在提取第一人称片段..."
            ),
        )
        report(0.25, f"找到 {len(segments)} 个片段")
        return segments

    def _detect_peaks(
        self,
        segments,
        report: Callable[[float, str], None],
    ):
        """Step 2: detect emotion peaks over the extracted segments."""
        report(0.30, "正在分析情感峰值...")
        peaks = self.emotion_detector.detect(
            segments,
            progress_callback=lambda c, t: report(
                0.30 + 0.15 * c / t if t > 0 else 0.45, "正在分析情感..."
            ),
        )
        report(0.45, f"找到 {len(peaks)} 个情感峰值")
        return peaks

    def _generate_narrations(
        self,
        segments,
        context: str,
        emotion: EmotionType,
        style: NarrationStyle,
        report: Callable[[float, str], None],
    ):
        """Step 3: generate narration script for the segments."""
        report(0.50, "正在生成解说文案...")
        narrations = self.script_generator.generate(
            segments,
            context=context,
            emotion=emotion,
            style=style,
            progress_callback=lambda c, t: report(
                0.50 + 0.25 * c / t if t > 0 else 0.75, "正在撰写文案..."
            ),
        )
        report(0.75, "文案生成完成")
        return narrations

    def _generate_audio(
        self,
        narrations,
        output_dir: str,
        voice: str,
        report: Callable[[float, str], None],
    ):
        """Step 4: synthesize the voiceover audio track."""
        report(0.80, "正在生成配音...")
        audio_track = self.tts_generator.generate(
            narrations,
            output_dir=output_dir,
            voice=voice,
            progress_callback=lambda c, t: report(
                0.80 + 0.15 * c / t if t > 0 else 0.95, "正在合成语音..."
            ),
        )
        report(0.95, "配音生成完成")
        return audio_track

    def process(
        self,
        video_path: str,
        context: str = "",
        emotion: EmotionType = EmotionType.NEUTRAL,
        style: NarrationStyle = NarrationStyle.DOCUMENTARY,
        voice: str = "zh-CN-XiaoxiaoNeural",
        progress_callback: Callable | None = None,
        output_dir: str = None,  # type: ignore[assignment]
    ) -> VideoProject:
        if output_dir is None:
            output_dir = self._resolve_output_dir(video_path)

        project = self._build_project(video_path, style, emotion)
        report = self._make_reporter(progress_callback)

        try:
            # Step 1: 提取第一人称片段
            segments = self._extract_segments(video_path, report)
            project.segments = segments

            if not segments:
                logger.warning("No first-person segments found")
                return project

            # Step 2: 检测情感峰值
            project.emotion_peaks = self._detect_peaks(segments, report)

            # Step 3: 生成解说文案
            narrations = self._generate_narrations(
                segments, context, emotion, style, report
            )
            project.narration_blocks = narrations

            # Step 4: 生成配音
            audio_track = self._generate_audio(narrations, output_dir, voice, report)
            if audio_track:
                project.audio_track = audio_track

            report(1.0, "处理完成！")

        except Exception as e:
            logger.error(f"Pipeline processing failed: {e}")
            raise

        return project