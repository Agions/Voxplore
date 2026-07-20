"""
Pipeline Integrator
统一流水线——整合 MonologueMaker + PerspectiveMapper + VideoInterleaver

工作流程:
    1. MonologueMaker: 生成独白脚本、配音、字幕
    2. PerspectiveMapper: 建立解说与画面的视角关系
    3. VideoInterleaver: 决定解说与原片的穿插策略
    4. 应用穿插决策到项目

使用示例:
    from scenefab.services.video import MonologueMaker

    maker = MonologueMaker()
    project = maker.create_project(
        source_video="input.mp4",
        context="深夜独自走在街头，回忆涌上心头",
        emotion="惆怅",
    )

    # 运行完整流水线
    timeline = maker.run_full_pipeline(project, include_interleave=True)

    # 或分步执行
    maker.generate_script(project)
    maker.generate_voice(project)
    maker.generate_captions(project)
    perspective_shots = maker.run_perspective_mapping(project)
    timeline = maker.run_video_interleave(project, perspective_shots)
    maker.apply_interleave_to_project(project, timeline)
"""

from typing import Any

from ..ai.scene_models import SceneInfo
from .models.perspective import (
    ClipSegment,
    InterleaveContext,
    InterleaveTimeline,
    NarrationSegment,
    PerspectiveShot,
    SceneSegment,
)
from .monologue_maker import MonologueMaker, MonologueProject, MonologueSegment
from .perspective_mapper import PerspectiveMapper
from .scene_converter import EmotionCurveGenerator, SceneConverter
from .video_interleaver import VideoInterleaver


class PipelineIntegrator(MonologueMaker):
    """
    统一流水线整合器

    在 MonologueMaker 基础上整合:
    - PerspectiveMapper: 视角映射
    - VideoInterleaver: 穿插决策
    """

    def __init__(
        self,
        voice_provider: str = "edge",
        perspective_config: dict[str, Any] | None = None,
        interleaver_config: dict[str, Any] | None = None,
    ):
        """
        初始化整合器

        Args:
            voice_provider: 语音提供商
            perspective_config: PerspectiveMapper 配置
            interleaver_config: VideoInterleaver 配置
        """
        super().__init__(voice_provider=voice_provider)

        self.perspective_mapper = PerspectiveMapper(config=perspective_config)
        self.video_interleaver = VideoInterleaver(config=interleaver_config)
        self.emotion_generator = EmotionCurveGenerator()

        # 缓存最新穿插结果
        self._last_perspective_shots: list[PerspectiveShot] = []
        self._last_interleave_timeline: InterleaveTimeline | None = None

    # ─────────────────────────────────────────────────────────────────
    # 视角映射
    # ─────────────────────────────────────────────────────────────────

    def run_perspective_mapping(
        self, project: MonologueProject
    ) -> list[PerspectiveShot]:
        """
        运行视角映射

        将独白片段与视频场景关联，建立第一人称视角关系

        Args:
            project: 独白项目

        Returns:
            PerspectiveShot 列表
        """
        self._report_progress("视角映射", 0.0)

        # 生成情感曲线
        emotion_curve = self.generate_emotion_curve(project.segments)

        # 转换场景信息
        scene_segments = self._convert_scenes(project.scenes)

        # 构建解说片段
        narration_segments = self._convert_to_narration_segments(project.segments)

        # 提取关键帧（如果有）
        keyframes = self._extract_keyframes(project)

        self._report_progress("视角映射", 0.5)

        # 执行视角映射
        perspective_shots = self.perspective_mapper.map_scenes_to_perspective(
            scenes=scene_segments,
            narration_segments=narration_segments,
            video_keyframes=keyframes,
            emotion_curve=emotion_curve,
        )

        self._report_progress("视角映射", 1.0)

        self._last_perspective_shots = perspective_shots
        return perspective_shots

    def _convert_scenes(self, scenes: list[SceneInfo]) -> list[SceneSegment]:
        """将 SceneInfo 转换为 SceneSegment（委托给 SceneConverter）"""
        return [SceneConverter.from_scene_info(scene) for scene in scenes]

    def _convert_to_narration_segments(
        self, segments: list[MonologueSegment]
    ) -> list[NarrationSegment]:
        """将 MonologueSegment 转换为 NarrationSegment（委托给 SceneConverter）"""
        return [
            SceneConverter.from_monologue_segment(seg, segment_id=f"narration_{i}")
            for i, seg in enumerate(segments)
        ]

    def _extract_keyframes(self, project: MonologueProject) -> list:
        """提取关键帧列表（使用 LRU 缓存）"""

        from .models.perspective import KeyFrame

        keyframes = []
        for i, scene in enumerate(project.scenes):
            if hasattr(scene, "keyframe_path") and scene.keyframe_path:
                kf = KeyFrame(
                    timestamp=scene.start,
                    frame_index=i,
                    image_path=scene.keyframe_path,
                )
                keyframes.append(kf)
        return keyframes

    # ─────────────────────────────────────────────────────────────────
    # 视频穿插
    # ─────────────────────────────────────────────────────────────────

    def run_video_interleave(
        self,
        project: MonologueProject,
        perspective_shots: list[PerspectiveShot],
    ) -> InterleaveTimeline:
        """
        运行视频穿插决策

        根据视角映射结果，决定解说与原片的穿插策略

        Args:
            project: 独白项目
            perspective_shots: 视角映射结果

        Returns:
            InterleaveTimeline: 穿插时间线
        """
        self._report_progress("视频穿插", 0.0)

        # 生成情感曲线
        emotion_curve = self.generate_emotion_curve(project.segments)

        # 构建解说片段
        narration_segments = self._convert_to_narration_segments(project.segments)

        # 构建原片片段
        original_clips = self._build_original_clips(project)

        # 转换场景
        scene_segments = self._convert_scenes(project.scenes)

        # 创建穿插上下文
        context = InterleaveContext(
            max_original_ratio=0.6,
            min_narration_ratio=0.4,
            emotion_threshold=0.6,
            allow_zoom_highlight=True,
            allow_subtitle_only_gaps=True,
        )

        self._report_progress("视频穿插", 0.5)

        # 执行穿插决策
        timeline = self.video_interleaver.decide_interleave(
            narration_timeline=narration_segments,
            original_clips=original_clips,
            perspective_shots=perspective_shots,
            scene_segments=scene_segments,
            emotion_curve=emotion_curve,
            context=context,
        )

        self._report_progress("视频穿插", 1.0)

        self._last_interleave_timeline = timeline
        return timeline

    def _build_original_clips(self, project: MonologueProject) -> list[ClipSegment]:
        """构建原片片段列表"""
        clips = []
        for i, scene in enumerate(project.scenes):
            clip = ClipSegment(
                clip_id=f"clip_{i}",
                source_path=project.source_video,
                start_time=scene.start,
                end_time=scene.end,
                duration=scene.duration,
                is_key_moment=scene.suitability_score > 70
                if hasattr(scene, "suitability_score")
                else False,
            )
            clips.append(clip)
        return clips

    # ─────────────────────────────────────────────────────────────────
    # 应用穿插决策
    # ─────────────────────────────────────────────────────────────────

    def apply_interleave_to_project(
        self,
        project: MonologueProject,
        timeline: InterleaveTimeline,
    ) -> MonologueProject:
        """
        应用穿插决策到项目

        根据穿插时间线更新 MonologueSegment 的元数据

        Args:
            project: 独白项目
            timeline: 穿插时间线

        Returns:
            更新后的项目
        """
        self._report_progress("应用穿插", 0.0)

        if not timeline.decisions:
            self._report_progress("应用穿插", 1.0)
            return project

        # 为每个 segment 更新穿插信息
        for i, segment in enumerate(project.segments):
            if i < len(timeline.decisions):
                decision = timeline.decisions[i]

                # 更新 segment 的穿插属性
                segment.show_original = decision.show_original
                segment.original_start = decision.original_start
                segment.original_end = decision.original_end
                segment.transition_type = decision.transition
                segment.zoom_factor = decision.zoom_factor
                segment.highlight_box = decision.highlight_box
                segment.narration_volume = decision.narration_volume
                segment.original_audio_volume = decision.original_audio_volume

                # 如果有字幕更新
                if decision.subtitle_text:
                    segment.interleave_subtitle = decision.subtitle_text
                segment.subtitle_style = decision.subtitle_style

            self._report_progress("应用穿插", (i + 1) / len(project.segments))

        self._report_progress("应用穿插", 1.0)
        return project

    # ─────────────────────────────────────────────────────────────────
    # 情感曲线（委托给 scene_converter）
    # ─────────────────────────────────────────────────────────────────

    def generate_emotion_curve(self, segments: list[MonologueSegment]) -> list[float]:
        """
        生成情感强度曲线（委托给 EmotionCurveGenerator）

        基于每个片段的情感类型生成 0-1 的情感强度曲线。

        Args:
            segments: 独白片段列表

        Returns:
            情感强度曲线列表，每项 0-1
        """
        return self.emotion_generator.get_segment_emotions(segments)

    # ─────────────────────────────────────────────────────────────────
    # 完整流水线
    # ─────────────────────────────────────────────────────────────────

    def run_full_pipeline(
        self,
        project: MonologueProject,
        include_interleave: bool = True,
    ) -> InterleaveTimeline:
        """
        运行完整流水线

        依次执行:
        1. 生成独白脚本
        2. 生成配音
        3. 生成字幕
        4. 视角映射
        5. 视频穿插
        6. 应用穿插决策

        Args:
            project: 独白项目
            include_interleave: 是否包含穿插决策

        Returns:
            InterleaveTimeline: 穿插时间线（如果 include_interleave=True）
        """
        # 1. 生成独白脚本
        self._report_progress("完整流水线", 0.0)
        self.generate_script(project)
        self._report_progress("完整流水线", 0.15)

        # 2. 生成配音
        self.generate_voice(project)
        self._report_progress("完整流水线", 0.35)

        # 3. 生成字幕
        self.generate_captions(project)
        self._report_progress("完整流水线", 0.50)

        if include_interleave:
            # 4. 视角映射
            perspective_shots = self.run_perspective_mapping(project)
            self._report_progress("完整流水线", 0.70)

            # 5. 视频穿插
            timeline = self.run_video_interleave(project, perspective_shots)
            self._report_progress("完整流水线", 0.85)

            # 6. 应用穿插决策
            self.apply_interleave_to_project(project, timeline)
            self._report_progress("完整流水线", 1.0)

            return timeline
        else:
            self._report_progress("完整流水线", 1.0)
            return None  # type: ignore[return-value]

    # ─────────────────────────────────────────────────────────────────
    # 便捷方法
    # ─────────────────────────────────────────────────────────────────

    def get_pipeline_status(self) -> dict[str, Any]:
        """
        获取流水线状态

        Returns:
            状态字典
        """
        return {
            "has_perspective_shots": len(self._last_perspective_shots) > 0,
            "perspective_shots_count": len(self._last_perspective_shots),
            "has_interleave_timeline": self._last_interleave_timeline is not None,
            "interleave_mode": (
                self._last_interleave_timeline.interleave_mode.value
                if self._last_interleave_timeline
                else None
            ),
        }

    def reset_pipeline_cache(self) -> None:
        """重置流水线缓存"""
        self._last_perspective_shots = []
        self._last_interleave_timeline = None

    # ─────────────────────────────────────────────────────────────────
    # 便捷入口
    # ─────────────────────────────────────────────────────────────────

    def run(
        self,
        source_video: str,
        context: str = "",
        emotion: str = "neutral",
        name: str | None = None,
        include_interleave: bool = True,
        custom_script: str | None = None,
    ) -> MonologueProject:
        """
        一步到位运行完整流水线 — 编排器 (创建项目 → 全流程 → 返回项目).

        依次执行:
        1. 创建项目并分析视频
        2. 生成独白脚本
        3. 生成配音
        4. 生成字幕
        5. 视角映射(可选)
        6. 视频穿插(可选)

        Args:
            source_video: 源视频路径或 URL
            context: 视频主题/背景描述
            emotion: 情感风格(healing/suspense/motivational/nostalgic/romantic)
            name: 项目名称(默认从视频文件名推断)
            include_interleave: 是否包含视角映射和视频穿插
            custom_script: 自定义解说脚本(可选)

        Returns:
            MonologueProject: 包含完整解说数据的项目对象

        Raises:
            FileNotFoundError: 源视频文件不存在
            ValueError: 参数校验失败
        """
        self._validate_source_video(source_video)
        project = self._create_and_report_project(source_video, context, emotion, name)
        self._generate_narration_content(project, custom_script)
        if include_interleave:
            self._run_interleave_pipeline(project)
        self._report_progress("完整流水线", 1.0)
        return project

    @staticmethod
    def _validate_source_video(source_video: str) -> None:
        """校验源视频: 本地文件须存在, URL 须以 http(s):// 开头."""
        import os

        if not source_video.startswith(("http://", "https://")) and not os.path.exists(
            source_video
        ):
            raise FileNotFoundError(f"源视频不存在: {source_video}")

    def _create_and_report_project(
        self,
        source_video: str,
        context: str,
        emotion: str,
        name: str | None,
    ) -> MonologueProject:
        """阶段 1: 报告进度并创建项目."""
        self._report_progress("完整流水线", 0.0)
        return self.create_project(
            source_video=source_video,
            context=context,
            emotion=emotion,
            name=name,
        )

    def _generate_narration_content(
        self, project: MonologueProject, custom_script: str | None
    ) -> None:
        """阶段 2-4: 生成脚本 → 配音 → 字幕, 含进度报告."""
        # 2. 脚本
        self._report_progress("完整流水线", 0.15)
        if custom_script:
            self.generate_script(project, custom_script=custom_script)
        else:
            self.generate_script(project)

        # 3. 配音
        self._report_progress("完整流水线", 0.35)
        self.generate_voice(project)

        # 4. 字幕
        self._report_progress("完整流水线", 0.50)
        self.generate_captions(project)

    def _run_interleave_pipeline(self, project: MonologueProject) -> None:
        """阶段 5-6: 视角映射 + 视频穿插 + 应用决策."""
        # 5. 视角映射
        self._report_progress("完整流水线", 0.65)
        perspective_shots = self.run_perspective_mapping(project)

        # 6. 视频穿插
        self._report_progress("完整流水线", 0.80)
        timeline = self.run_video_interleave(project, perspective_shots)
        self.apply_interleave_to_project(project, timeline)


# ─────────────────────────────────────────────────────────────────────────────
# 为 MonologueSegment 添加穿插属性（向后兼容）
# ─────────────────────────────────────────────────────────────────────────────


__all__ = [
    "PipelineIntegrator",
]
