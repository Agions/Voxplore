"""
AI 第一人称独白制作器 (Monologue Maker)

功能：原视频 + AI 独白配音 + 沉浸式字幕

工作流程:
    1. 分析原视频内容（SceneAnalyzer）
    2. 生成第一人称独白文案（ScriptGenerator + DeepSeek-V4）
    3. 生成情感化 AI 配音（VoiceGenerator + Edge-TTS）
    4. 生成电影级字幕（CaptionGenerator）
    5. 导出剪映草稿

使用示例:
    from app.services.video import MonologueMaker, MonologueProject

    maker = MonologueMaker()
    project = maker.create_project(
        source_video="input.mp4",
        context="深夜独自走在街头，回忆涌上心头",
        emotion="惆怅",
    )

    # 导出到剪映
    draft_path = maker.export_to_jianying(project, "/path/to/drafts")
"""

import logging
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ...models.project import MultiVideoSource, SeriesContext  # v2.5.0
from ..ai.script_generator import ScriptGenerator, VoiceTone
from ..ai.voice_generator import VoiceConfig, VoiceGenerator
from ..ai.voice_models import VoiceStyle
from ..export.jianying_adapter import JianyingDraft
from ..video.caption_gen import CaptionGenerator
from ..video.ffmpeg_tool import FFmpegTool
from .base_maker import BaseProject, BaseVideoMaker
from .models.monologue import EmotionType, MonologueSegment, MonologueStyle
from .track_builder import CAPTION_STYLES, build_monologue_tracks

logger = logging.getLogger(__name__)


__all__ = [
    "MonologueProject",
    "MonologueMaker",
    "create_monologue",
]


@dataclass
class MonologueProject(BaseProject):
    """独白视频项目"""

    # 独白内容
    context: str = ""  # 场景/情境描述
    emotion: str = ""  # 情感基调
    full_script: str = ""  # 完整独白
    segments: list[MonologueSegment] = field(default_factory=list)

    # 配置
    style: MonologueStyle = MonologueStyle.MELANCHOLIC
    voice_config: VoiceConfig = field(default_factory=VoiceConfig)
    caption_style: str = "cinematic"  # cinematic, minimal, expressive

    # ── v2.5.0 多文件上传扩展（向后兼容） ───────────────────────
    # 保留父类 BaseProject.source_video（单视频），新增多视频字段。
    # 读：优先 source_videos，缺失回退 source_video。
    # 写：始终写 source_videos（source_video 也同步写入）。
    source_videos: list[str] = field(default_factory=list)
    multi_strategy: str = "single"  # single | concat | batch | series
    series_context: SeriesContext | None = None

    @property
    def total_duration(self) -> float:
        """总时长"""
        return sum(seg.audio_duration for seg in self.segments)

    @property
    def all_source_videos(self) -> list[str]:
        """返回当前模式下需要处理的所有视频路径（消除歧义）。

        优先级：
        1. 若 ``source_videos`` 非空，取其副本（多视频模式）
        2. 否则若 ``source_video`` 非空，包成单元素列表（单视频模式）
        3. 都没有返回空列表
        """
        if self.source_videos:
            return list(self.source_videos)
        if self.source_video:
            return [self.source_video]
        return []

    # ------------------------------------------------------------------ #
    #  持久化 (.scenefab JSON)                                          #
    # ------------------------------------------------------------------ #

    def save(self, path: str | None = None) -> str:
        """
        将项目保存为 .scenefab 文件（JSON）。

        Args:
            path: 保存路径，默认 <output_dir>/<name>.scenefab

        Returns:
            实际保存的文件路径
        """

        save_path = (
            Path(path) if path else Path(self.output_dir) / f"{self.name}.scenefab"
        )
        save_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.1",  # v2.5.0: 加入 multi_strategy / series_context
            "type": "monologue",
            "id": self.id,
            "name": self.name,
            # 向后兼容：同时写 source_video 与 source_videos
            "source_video": self.source_video,
            "source_videos": self.all_source_videos,
            "multi_strategy": self.multi_strategy,
            "series_context": self.series_context.to_dict()
            if self.series_context
            else None,
            "video_duration": self.video_duration,
            "output_dir": self.output_dir,
            "context": self.context,
            "emotion": self.emotion,
            "full_script": self.full_script,
            "style": self.style.value if isinstance(self.style, Enum) else self.style,
            "caption_style": self.caption_style,
            "segments": [
                {
                    "script": seg.script,
                    "emotion": seg.emotion.value
                    if isinstance(seg.emotion, Enum)
                    else seg.emotion,
                    "video_start": seg.video_start,
                    "video_end": seg.video_end,
                    "audio_path": seg.audio_path,
                    "audio_duration": seg.audio_duration,
                    "captions": seg.captions,
                }
                for seg in self.segments
            ],
        }

        from ...utils.json_io import write_json

        write_json(save_path, data, indent=2)

        return str(save_path)

    @classmethod
    def load(cls, path: str) -> "MonologueProject":
        """
        从 .scenefab 文件加载项目（兼容旧 .narrafilm / .narrafiilm）。

        Args:
            path: 项目文件路径（.scenefab / 旧 .narrafilm / .narrafiilm）

        Returns:
            MonologueProject 实例
        """
        from ...utils.json_io import read_json

        data = read_json(path)

        segments = [
            MonologueSegment(
                script=seg["script"],
                emotion=seg["emotion"],
                video_start=seg["video_start"],
                video_end=seg["video_end"],
                audio_path=seg.get("audio_path", ""),
                audio_duration=seg.get("audio_duration", 0.0),
                captions=seg.get("captions", []),
            )
            for seg in data.get("segments", [])
        ]

        style_val = data.get("style", "melancholic")
        if isinstance(style_val, str):
            try:
                style = MonologueStyle(style_val)
            except ValueError:
                style = MonologueStyle.MELANCHOLIC
        else:
            style = MonologueStyle.MELANCHOLIC

        # v2.5.0: source_videos 优先，缺失回退 source_video
        source_video = data.get("source_video", "")
        source_videos_raw = data.get("source_videos") or []
        if not source_videos_raw and source_video:
            source_videos_raw = [source_video]
        # 去重保序
        seen: set[str] = set()
        source_videos: list[str] = []
        for p in source_videos_raw:
            if p and p not in seen:
                seen.add(p)
                source_videos.append(p)

        # series_context（可选）
        sc_raw = data.get("series_context")
        series_ctx = (
            SeriesContext.from_dict(sc_raw) if isinstance(sc_raw, dict) else None
        )

        return cls(
            id=data.get("id", ""),
            name=data.get("name", "新建项目"),
            source_video=source_video,
            source_videos=source_videos,
            multi_strategy=data.get("multi_strategy", "single"),
            series_context=series_ctx,
            video_duration=data.get("video_duration", 0.0),
            output_dir=data.get("output_dir", ""),
            context=data.get("context", ""),
            emotion=data.get("emotion", ""),
            full_script=data.get("full_script", ""),
            style=style,
            caption_style=data.get("caption_style", "cinematic"),
            segments=segments,
        )


class MonologueMaker(BaseVideoMaker[MonologueProject]):
    """
    AI 第一人称独白制作器

    将原视频转换为带有沉浸式独白的视频

    使用示例:
        maker = MonologueMaker()

        # 创建项目
        project = maker.create_project(
            source_video="night_walk.mp4",
            context="深夜独自走在雨后的街道上",
            emotion="惆怅",
            style=MonologueStyle.MELANCHOLIC,
        )

        # 生成独白
        maker.generate_script(project)

        # 生成配音
        maker.generate_voice(project)

        # 生成字幕
        maker.generate_captions(project)

        # 导出到剪映
        draft_path = maker.export_to_jianying(project, "/path/to/drafts")
    """

    # 风格对应的配置
    STYLE_CONFIG = {
        MonologueStyle.MELANCHOLIC: {
            "tone": VoiceTone.CALM,
            "voice_style": VoiceStyle.NARRATION,
            "rate": 0.9,
            "prompt_hint": "忧郁、沉思、内心独白",
        },
        MonologueStyle.INSPIRATIONAL: {
            "tone": VoiceTone.EXCITED,
            "voice_style": VoiceStyle.NARRATION,
            "rate": 1.0,
            "prompt_hint": "励志、向上、充满力量",
        },
        MonologueStyle.ROMANTIC: {
            "tone": VoiceTone.EMOTIONAL,
            "voice_style": VoiceStyle.CONVERSATIONAL,
            "rate": 0.95,
            "prompt_hint": "温柔、浪漫、深情",
        },
        MonologueStyle.MYSTERIOUS: {
            "tone": VoiceTone.MYSTERIOUS,
            "voice_style": VoiceStyle.WHISPERING,
            "rate": 0.85,
            "prompt_hint": "神秘、悬疑、低沉",
        },
        MonologueStyle.NOSTALGIC: {
            "tone": VoiceTone.CALM,
            "voice_style": VoiceStyle.NARRATION,
            "rate": 0.9,
            "prompt_hint": "怀旧、追忆、温暖",
        },
        MonologueStyle.PHILOSOPHICAL: {
            "tone": VoiceTone.CALM,
            "voice_style": VoiceStyle.NARRATION,
            "rate": 0.88,
            "prompt_hint": "深邃、哲思、引人深思",
        },
        MonologueStyle.HEALING: {
            "tone": VoiceTone.CALM,
            "voice_style": VoiceStyle.CONVERSATIONAL,
            "rate": 0.92,
            "prompt_hint": "治愈、温暖、安慰",
        },
    }

    def __init__(
        self,
        voice_provider: str = "edge",
    ):
        super().__init__()
        self.voice_provider = voice_provider

        self.voice_generator = VoiceGenerator(provider=voice_provider)
        self.script_generator = ScriptGenerator(use_llm_manager=True)
        self.caption_gen = CaptionGenerator()

    def create_project(  # type: ignore[override]
        self,
        source_video: str | None = None,
        context: str = "",
        emotion: str = "neutral",
        name: str | None = None,
        style: MonologueStyle = MonologueStyle.MELANCHOLIC,
        output_dir: str | None = None,
        *,
        source_videos: list[str] | None = None,
        multi_strategy: str = "single",
        series_context: SeriesContext | None = None,
        **kwargs,
    ) -> MonologueProject:
        """创建独白项目（v2.5.0 支持多视频）。

        支持三种调用方式（优先级从高到低）：
        1. ``source_videos=[v1, v2, ...]`` ：多视频模式，根据 ``multi_strategy`` 处理
        2. ``source_video="x.mp4"`` ：单视频模式（向后兼容）

        ``multi_strategy`` 取值：
        - ``"single"`` ：1 个视频，1 个项目
        - ``"concat"`` ：N 个视频拼接为 1 个，1 个项目（FFmpeg concat demuxer）
        - ``"batch"`` ：N 个视频独立生成 N 个项目（参看 ``create_batch``）
        - ``"series"`` ：N 个视频作为整季系列，需 ``series_context``
        """
        # 统一得到所有要处理的视频路径（去重保序）
        paths: list[str] = []
        if source_videos:
            seen: set[str] = set()
            for p in source_videos:
                if p and p not in seen:
                    seen.add(p)
                    paths.append(p)
        if source_video and source_video not in paths:
            paths.insert(0, source_video)

        if not paths:
            raise ValueError("create_project 需至少传入 source_video 或 source_videos")

        primary = paths[0]
        strategy = multi_strategy
        if len(paths) > 1 and strategy == "single":
            # 多文件但策略 single：自动升级为 batch （防呆）
            strategy = "batch"
            logger.info(
                "source_videos 有 %d 个路径但未指定策略，自动升为 batch", len(paths)
            )

        project = MonologueProject(
            context=context,
            emotion=emotion,
            style=style,
            source_videos=list(paths),
            multi_strategy=strategy,
            series_context=series_context,
        )

        self._report_progress("分析视频", 0.0)
        self._init_project(project, primary, name, output_dir)

        # 多视频模式：首件时长为参考，全集总时长求和
        if project.video_duration <= 0:
            try:
                project.video_duration = FFmpegTool.get_duration(primary) or 0.0
            except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
                # FFmpegTool.get_duration 失败: 子进程错误 / FFmpeg 未安装 / OS 错误
                # 不吞 RuntimeError/TypeError 等真实编程 bug
                logger.warning(f"Failed to get video duration for {primary}: {e}")
                project.video_duration = 0.0

        self._report_progress("分析视频", 1.0)

        return project

    def generate_script(
        self,
        project: MonologueProject,
        custom_script: str | None = None,
    ) -> None:
        """
        生成独白文案

        Args:
            project: 项目对象
            custom_script: 自定义文案
        """
        self._report_progress("生成独白", 0.0)

        if custom_script:
            project.full_script = custom_script
        else:
            # 复用预建的 script_generator（避免每次重新加载配置）
            # v2.5.0: 透传 multi_strategy + series_context 让 LLM 知道场景
            result = self.script_generator.generate_monologue(
                context=project.context,
                emotion=project.emotion,
                duration=project.video_duration,
                multi_strategy=project.multi_strategy or None,
                series_context=project.series_context,
            )
            project.full_script = result.content

        # 分段
        self._segment_script(project)

        self._report_progress("生成独白", 1.0)

    def _segment_script(self, project: MonologueProject) -> None:
        """将独白分段 — 支持空白行和中文句末标点双重拆分

        流程:
        1. 优先按 \\n\\n 段落分
        2. 否则按中文句末标点分, 合并过短碎片
        3. 匹配场景 + 推断情感 + 计算时长 → 创建 MonologueSegment
        """
        paragraphs = self._split_paragraphs(project.full_script)

        # 匹配场景
        scenes = project.scenes if project.scenes else [None]
        n_scenes = len(scenes) if scenes and scenes[0] else 1

        project.segments = []
        for i, para in enumerate(paragraphs):
            scene_idx = i % n_scenes
            scene = scenes[scene_idx] if scenes and scenes[0] else None

            # 根据内容推断情感
            emotion = self._infer_emotion(para, project.emotion)

            seg_duration = (
                project.video_duration / len(paragraphs) if paragraphs else 10.0
            )
            segment = MonologueSegment(
                script=para,
                emotion=emotion,
                video_start=scene.start if scene else i * seg_duration,
                video_end=scene.end if scene else (i + 1) * seg_duration,
            )
            project.segments.append(segment)

    def _split_paragraphs(self, full_script: str) -> list[str]:
        """将独白文本拆分为段落列表

        拆分策略:
        - 优先按空行 (\\n\\n) 切分
        - 若只有 1 段 (无空行), 改按中文句末标点 (。！？?!) 切分
        - 标点切分时若碎片过短 (merged > 3 且 buf < 30 字), 合并到 30 字以上

        Returns:
            段落列表 (至少 1 段)
        """
        # 优先按空白行分段
        paragraphs = [p.strip() for p in full_script.split("\n\n") if p.strip()]

        if len(paragraphs) > 1:
            return paragraphs

        # 按中文句末标点拆分（保留标点）
        paragraphs = _split_by_chinese_punctuation(full_script)
        if not paragraphs:
            return [full_script]

        # 碎片合并: 仅当碎片数 > 3 才合并到 30 字以上, 否则保留原样
        if len(paragraphs) > 3:
            return _merge_short_fragments(paragraphs, min_chars=30)
        return paragraphs

    def _infer_emotion(self, text: str, base_emotion: str) -> EmotionType:
        """根据文本内容推断情感"""
        # 简单关键词匹配
        emotion_keywords = {
            EmotionType.SAD: ["悲", "泪", "哭", "失去", "离别", "孤独", "寂寞"],
            EmotionType.HAPPY: ["开心", "快乐", "笑", "幸福", "美好", "温暖"],
            EmotionType.CALM: ["平静", "安宁", "静", "默", "沉思"],
            EmotionType.TENDER: ["温柔", "爱", "思念", "想", "心"],
            EmotionType.EXCITED: ["激动", "兴奋", "期待", "梦想", "未来"],
        }

        # 检查关键词
        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return emotion

        # 使用基础情感
        emotion_map = {
            "惆怅": EmotionType.SAD,
            "忧郁": EmotionType.SAD,
            "开心": EmotionType.HAPPY,
            "平静": EmotionType.CALM,
            "温柔": EmotionType.TENDER,
            "excited": EmotionType.EXCITED,
        }

        return emotion_map.get(base_emotion, EmotionType.NEUTRAL)

    def generate_voice(
        self,
        project: MonologueProject,
        voice_config: VoiceConfig | None = None,
    ) -> None:
        """
        生成 AI 配音（并行多 segment，max_workers=4）

        Args:
            project: 项目对象
            voice_config: 配音配置
        """
        style_cfg = self.STYLE_CONFIG.get(
            project.style, self.STYLE_CONFIG[MonologueStyle.MELANCHOLIC]
        )

        if voice_config:
            project.voice_config = voice_config
        else:
            project.voice_config = VoiceConfig(
                style=style_cfg["voice_style"],  # type: ignore[arg-type]
                rate=style_cfg["rate"],  # type: ignore[arg-type]
            )

        output_dir = Path(project.output_dir) / "audio"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 准备任务列表
        tasks = [
            (i, seg, str(output_dir / f"monologue_{i:03d}.mp3"))
            for i, seg in enumerate(project.segments)
        ]

        results: dict[int, tuple[str, float, list]] = {}
        completed = 0

        def _create_fallback_audio(output_path: str, text: str) -> float:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            duration = max(2.0, len(text) * 0.25)
            try:
                import wave

                with wave.open(str(path), "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(22050)
                    n_samples = int(22050 * duration)
                    wav.writeframes(b"\x00\x00" * n_samples)
            except Exception as e:
                logger.warning(f"Failed to write silent wav: {e}")
                with open(path, "wb") as f:
                    f.write(b"0" * 1024)
            return duration

        def _generate_one(i: int, segment: MonologueSegment, audio_path: str):
            config = VoiceConfig(
                voice_id=project.voice_config.voice_id,
                rate=project.voice_config.rate,
            )
            try:
                result = self.voice_generator.generate(
                    text=segment.script,
                    output_path=audio_path,
                    config=config,
                )
                return (
                    i,
                    result.audio_path,
                    result.duration,
                    result.sentence_timestamps or [],
                )
            except Exception as e:
                logger.warning(
                    f"Segment {i} 配音合成网络超时/失败, 使用防崩占位音频: {e}"
                )
                duration = _create_fallback_audio(audio_path, segment.script)
                return (i, audio_path, duration, [])

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(_generate_one, i, seg, path): i
                for i, seg, path in tasks
            }
            for future in as_completed(futures):
                i, audio_path, duration, timestamps = future.result()
                results[i] = (audio_path, duration, timestamps)
                completed += 1
                self._report_progress("生成配音", completed / len(tasks))

        for i, segment in enumerate(project.segments):
            if i in results:
                (
                    segment.audio_path,
                    segment.audio_duration,
                    segment.sentence_timestamps,
                ) = results[i]

        self._report_progress("生成配音", 1.0)

    def generate_captions(
        self,
        project: MonologueProject,
        style: str = "cinematic",
    ) -> None:
        """
        生成电影级字幕

        Args:
            project: 项目对象
            style: 字幕风格 (cinematic, minimal, expressive)
        """
        self._report_progress("生成字幕", 0.0)

        project.caption_style = style
        caption_cfg = CAPTION_STYLES.get(style, CAPTION_STYLES["cinematic"])

        current_time = 0.0
        total_segments = len(project.segments)

        for i, segment in enumerate(project.segments):
            segment.captions = self._captions_for_segment(
                segment, caption_cfg, current_time
            )

            current_time += segment.audio_duration
            self._report_progress("生成字幕", (i + 1) / total_segments)

        self._report_progress("生成字幕", 1.0)

    def _captions_for_segment(
        self,
        segment: MonologueSegment,
        caption_cfg: dict,
        offset: float,
    ) -> list[dict]:
        """根据是否有 EdgeTTS 真实时间戳，分发到不同的字幕构建路径"""
        if segment.sentence_timestamps:
            return self._captions_from_timestamps(segment, caption_cfg, offset)
        return self._captions_from_fallback(segment, caption_cfg, offset)

    def _captions_from_timestamps(
        self,
        segment: MonologueSegment,
        caption_cfg: dict,
        offset: float,
    ) -> list[dict]:
        """使用 EdgeTTS 真实句子时间戳构建字幕"""
        captions: list[dict] = []
        for ts in segment.sentence_timestamps:
            captions.append(
                {
                    "text": ts["text"],
                    "start": offset + ts["start"],
                    "duration": max(ts["end"] - ts["start"], 0.5),
                    "style": caption_cfg,
                    "emotion": segment.emotion.value,
                }
            )
        return captions

    def _captions_from_fallback(
        self,
        segment: MonologueSegment,
        caption_cfg: dict,
        offset: float,
    ) -> list[dict]:
        """回退：按中文句末标点拆分并按字符数估算时长"""
        parts = re.split(r"([。！？\u3001])", segment.script)
        segment_words = max(len(segment.script.replace(" ", "")), 1)

        captions: list[dict] = []
        current_start = offset
        current_text = ""

        for part in parts:
            if not part:
                continue
            if part in ("，", "；"):
                current_text += part
                continue
            if part in ("。", "！", "？"):
                current_text += part
                if len(current_text.strip()) >= 2:
                    self._emit_fallback_caption(
                        captions,
                        current_text,
                        segment,
                        caption_cfg,
                        segment_words,
                        current_start,
                    )
                    duration = (
                        len(current_text) / segment_words * segment.audio_duration
                    )
                    current_start += duration
                    current_text = ""
            else:
                current_text += part

        if current_text.strip() and len(current_text.strip()) >= 2:
            self._emit_fallback_caption(
                captions,
                current_text,
                segment,
                caption_cfg,
                segment_words,
                current_start,
            )

        return captions

    def _emit_fallback_caption(
        self,
        captions: list,
        current_text: str,
        segment,
        caption_cfg,
        segment_words: int,
        current_start: float,
    ) -> None:
        """构造 fallback caption（loop 内 + 尾随双调用共享）"""
        duration = (len(current_text) / segment_words) * segment.audio_duration
        captions.append(
            self._build_fallback_caption(
                current_text,
                caption_cfg,
                current_start,
                duration,
                segment.emotion.value,
            )
        )

    def _build_fallback_caption(
        self,
        text: str,
        caption_cfg: dict,
        start: float,
        duration: float,
        emotion: str,
    ) -> dict:
        """构造单条字幕 dict（时长已计算好）"""
        return {
            "text": text,
            "start": start,
            "duration": max(duration, 0.5),
            "style": caption_cfg,
            "emotion": emotion,
        }

    # ------------------------------------------------------------------ #
    #  v2.5.0 多视频批量生成                                              #
    # ------------------------------------------------------------------ #

    def create_batch(
        self,
        sources: "MultiVideoSource | list[str]",
        context: str = "",
        emotion: str = "neutral",
        style: MonologueStyle = MonologueStyle.MELANCHOLIC,
        name_prefix: str = "EP",
        parallel: int | None = None,
        output_dir: str | None = None,
    ) -> list[MonologueProject]:
        """批量创建多集独白项目（batch 模式）。

        输入为 ``MultiVideoSource`` 或纯路径列表。

        - 每个路径独立生成一个 ``MonologueProject``，名字 = ``{name_prefix}{idx:02d}_{stem}``
        - ``parallel=None`` （默认）时，按 ``compute_adaptive_parallel(n_tasks)``
          自适应选择并发度（参见该函数注释）
        - ``parallel=N`` 显式传入时，clamp 到 ``[1, max_parallel]`` 范围
        - 仅生成 project + 运行 create_project，不会自动生成脚本/配音（由调用方控制）
        - 返回按顺序的 N 个 ``MonologueProject``

        注意：完整管线（脚本/配音/字幕/导出）仍需逐个调用 ``generate_*`` 方法。
        如需一次性跑完，参考 :class:`ProductionRunner` 中的 ``start_batch``。
        """
        # 输入归一化
        if isinstance(sources, MultiVideoSource):
            paths = sources.paths
            strategy = sources.strategy
            series_ctx = sources.series_context
        else:
            paths = list(sources)
            strategy = "batch"
            series_ctx = None

        if not paths:
            return []

        # v2.5.0 自适应并发：默认 None → 走 CPU 自适应
        n_tasks = len(paths)
        max_parallel = max(1, (os.cpu_count() or 1) * 2)
        if parallel is None:
            parallel = compute_adaptive_parallel(n_tasks, max_parallel=max_parallel)
        if parallel < 1:
            parallel = 1
        if parallel > max_parallel:
            parallel = max_parallel

        results: list[MonologueProject | None] = [None] * len(paths)

        def _build_one(idx: int, video_path: str) -> MonologueProject:
            stem = Path(video_path).stem
            # v2.5.0: series 策略 + SeriesContext → 消费 episode_naming 模板
            if strategy == "series" and series_ctx is not None:
                project_name = _format_episode_name(
                    series_ctx.episode_naming,
                    title=series_ctx.series_title or stem,
                    ep=idx + 1,
                    stem=stem,
                )
            else:
                project_name = f"{name_prefix}{idx + 1:02d}_{stem}"
            return self.create_project(
                source_video=video_path,
                context=context,
                emotion=emotion,
                name=project_name,
                style=style,
                output_dir=output_dir,
                source_videos=None,  # batch 模式下每个项目仅为单视频
                multi_strategy="single",
                series_context=series_ctx if strategy == "series" else None,
            )

        with ThreadPoolExecutor(max_workers=parallel) as executor:
            future_to_idx = {
                executor.submit(_build_one, i, p): i for i, p in enumerate(paths)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:  # noqa: BLE001 - record failure, keep batch going
                    logger.error(
                        "create_batch: 第 %d 个项目创建失败 (%s)，跳过", idx, e
                    )
                    results[idx] = None

        return [p for p in results if p is not None]

    def _build_jianying_tracks(
        self, draft: JianyingDraft, project: MonologueProject
    ) -> None:
        """构建独白视频的剪映轨道"""
        build_monologue_tracks(
            draft=draft,
            source_video=project.source_video,
            video_duration=project.video_duration,
            segments=project.segments,
            caption_style=project.caption_style,
        )

    # ------------------------------------------------------------------ #
    #  辅助方法                                                           #
    # ------------------------------------------------------------------ #


# =========== 便捷函数 ===========


def _format_episode_name(
    template: str,
    *,
    title: str,
    ep: int,
    stem: str,
) -> str:
    """按模板渲染单集项目名（v2.5.0 集数命名器）。

    支持占位符：
    - ``{title}`` : :class:`SeriesContext.series_title`
    - ``{ep}``    : 当前集数（1-based）
    - ``{stem}``  : 视频文件名 stem（不含扩展名）

    Args:
        template: 模板字符串，如 ``"{title}_EP{ep:02d}"`` / ``"EP{ep:02d}_{title}"``
        title: 剧名(为空时回退到 ``stem``)
        ep: 当前集数(1-based)
        stem: 视频文件名

    Returns:
        渲染后的项目名。若模板为空 / 解析异常 / 渲染后为空,则回退
        到 ``{stem}_EP{ep:02d}``。
    """
    fallback = f"{stem}_EP{ep:02d}"
    if not template:
        return fallback
    try:
        rendered = template.format(title=title, ep=ep, stem=stem)
    except (KeyError, IndexError, ValueError):
        logger.warning("episode_naming 模板解析失败: %r, 回退到默认命名", template)
        return fallback
    return rendered or fallback


def compute_adaptive_parallel(
    n_tasks: int,
    *,
    max_parallel: int | None = None,
) -> int:
    """按 CPU 数自适应选择并发度（v2.5.0）。

    规则：
    - n_tasks <= 1  → 1（避免无意义并发）
    - n_tasks == 2  → 2（小任务集，直接并行）
    - n_tasks > 2   → ``min(n_tasks, cpu_count, max_parallel)``

    ``max_parallel`` 默认取 ``os.cpu_count() * 2``，但调用方可显式压低
    （如 CI 环境 / 受限线程池）。
    """
    if n_tasks <= 1:
        return 1

    if max_parallel is None:
        cpu = os.cpu_count() or 1
        max_parallel = max(1, cpu * 2)

    # I/O bound 任务（ffprobe、FFmpeg 探测）下，2x CPU 通常就够了；
    # 但允许 n_tasks 突破这个上限（任务数很多时全跑更划算）。
    return min(n_tasks, max(max_parallel, n_tasks), max_parallel * 2)


def create_monologue(
    source_video: str,
    context: str,
    emotion: str,
    output_jianying_dir: str,
    style: MonologueStyle = MonologueStyle.MELANCHOLIC,
) -> str:
    """
    一键创建独白视频

    Args:
        source_video: 源视频
        context: 场景描述
        emotion: 情感
        output_jianying_dir: 剪映草稿目录
        style: 独白风格

    Returns:
        剪映草稿路径
    """
    maker = MonologueMaker()

    project = maker.create_project(
        source_video=source_video,
        context=context,
        emotion=emotion,
        style=style,
    )

    maker.generate_script(project)
    maker.generate_voice(project)
    maker.generate_captions(project)

    return maker.export_to_jianying(project, output_jianying_dir)


# ============================================
# MonologueMaker._split_paragraphs 的 2 个纯函数辅助
# ============================================


def _split_by_chinese_punctuation(text: str) -> list[str]:
    """按中文 + 英文句末标点拆分, 保留标点.

    支持的标点: 。 ！ ？ ? !

    Example:
        "你好。今天！是吗?" → ["你好。", "今天！", "是吗?"]
    """
    parts = re.split(r"([。！？\?!]+)", text)
    result: list[str] = []
    for i in range(0, len(parts) - 1, 2):
        chunk = parts[i] + (parts[i + 1] if i + 1 < len(parts) else "")
        if chunk.strip():
            result.append(chunk.strip())
    return result


def _merge_short_fragments(fragments: list[str], min_chars: int = 30) -> list[str]:
    """合并短碎片, 每段累计到至少 min_chars 字才输出.

    Example:
        ["短。", "也短。", "再来一句凑够30字。", "短。"] (min_chars=10) →
        ["短。也短。再来一句凑够30字。短。"]
    """
    result: list[str] = []
    buf = ""
    for frag in fragments:
        buf += frag
        if len(buf) >= min_chars:
            result.append(buf)
            buf = ""
    if buf:
        result.append(buf)
    return result
