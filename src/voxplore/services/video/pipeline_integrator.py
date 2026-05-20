"""
Pipeline Integrator
统一流水线——整合 MonologueMaker + PerspectiveMapper + VideoInterleaver

工作流程:
    1. MonologueMaker: 生成独白脚本、配音、字幕
    2. PerspectiveMapper: 建立解说与画面的视角关系
    3. VideoInterleaver: 决定解说与原片的穿插策略
    4. 应用穿插决策到项目

使用示例:
    from voxplore.services.video import MonologueMaker

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

from typing import List, Optional, Dict, Any

from .monologue_maker import MonologueMaker, MonologueProject, MonologueSegment
from .perspective_mapper import PerspectiveMapper
from .scene_converter import SceneConverter, EmotionCurveGenerator
from .video_interleaver import VideoInterleaver
from .models.perspective import (
    PerspectiveShot,
    InterleaveTimeline,
    InterleaveContext,
    NarrationSegment,
    ClipSegment,
    SceneSegment,
)
from ..ai.scene_models import SceneInfo


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
        perspective_config: Optional[Dict[str, Any]] = None,
        interleaver_config: Optional[Dict[str, Any]] = None,
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
        self._last_perspective_shots: List[PerspectiveShot] = []
        self._last_interleave_timeline: Optional[InterleaveTimeline] = None

    # ─────────────────────────────────────────────────────────────────
    # 视角映射
    # ─────────────────────────────────────────────────────────────────

    def run_perspective_mapping(self, project: MonologueProject) -> List[PerspectiveShot]:
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

    def _convert_scenes(self, scenes: List[SceneInfo]) -> List[SceneSegment]:
        """将 SceneInfo 转换为 SceneSegment（委托给 SceneConverter）"""
        return [SceneConverter.from_scene_info(scene) for scene in scenes]

    def _convert_to_narration_segments(
        self, segments: List[MonologueSegment]
    ) -> List[NarrationSegment]:
        """将 MonologueSegment 转换为 NarrationSegment（委托给 SceneConverter）"""
        return [
            SceneConverter.from_monologue_segment(seg, segment_id=f"narration_{i}")
            for i, seg in enumerate(segments)
        ]

    def _extract_keyframes(self, project: MonologueProject) -> List:
        """提取关键帧列表"""
        from .models.perspective import KeyFrame

        keyframes = []
        for i, scene in enumerate(project.scenes):
            if hasattr(scene, 'keyframe_path') and scene.keyframe_path:
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
        perspective_shots: List[PerspectiveShot],
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

    def _build_original_clips(self, project: MonologueProject) -> List[ClipSegment]:
        """构建原片片段列表"""
        clips = []
        for i, scene in enumerate(project.scenes):
            clip = ClipSegment(
                clip_id=f"clip_{i}",
                source_path=project.source_video,
                start_time=scene.start,
                end_time=scene.end,
                duration=scene.duration,
                is_key_moment=scene.suitability_score > 70 if hasattr(scene, 'suitability_score') else False,
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

    def generate_emotion_curve(self, segments: List[MonologueSegment]) -> List[float]:
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
            return None

    # ─────────────────────────────────────────────────────────────────
    # 便捷方法
    # ─────────────────────────────────────────────────────────────────

    def get_pipeline_status(self) -> Dict[str, Any]:
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
                if self._last_interleave_timeline else None
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
        name: Optional[str] = None,
        include_interleave: bool = True,
        custom_script: Optional[str] = None,
    ) -> MonologueProject:
        """
        一步到位运行完整流水线（创建项目 → 全流程 → 返回项目）

        依次执行:
        1. 创建项目并分析视频
        2. 生成独白脚本
        3. 生成配音
        4. 生成字幕
        5. 视角映射（可选）
        6. 视频穿插（可选）

        Args:
            source_video: 源视频路径或 URL
            context: 视频主题/背景描述
            emotion: 情感风格（healing/suspense/motivational/nostalgic/romantic）
            name: 项目名称（默认从视频文件名推断）
            include_interleave: 是否包含视角映射和视频穿插
            custom_script: 自定义解说脚本（可选）

        Returns:
            MonologueProject: 包含完整解说数据的项目对象

        Raises:
            FileNotFoundError: 源视频文件不存在
            ValueError: 参数校验失败
        """
        import os

        # 校验源视频
        if not os.path.exists(source_video) and not source_video.startswith(("http://", "https://")):
            raise FileNotFoundError(f"源视频不存在: {source_video}")

        # 1. 创建项目
        self._report_progress("完整流水线", 0.0)
        project = self.create_project(
            source_video=source_video,
            context=context,
            emotion=emotion,
            name=name,
        )

        # 2. 生成脚本
        self._report_progress("完整流水线", 0.15)
        if custom_script:
            self.generate_script(project, custom_script=custom_script)
        else:
            self.generate_script(project)

        # 3. 生成配音
        self._report_progress("完整流水线", 0.35)
        self.generate_voice(project)

        # 4. 生成字幕
        self._report_progress("完整流水线", 0.50)
        self.generate_captions(project)

        if include_interleave:
            # 5. 视角映射
            self._report_progress("完整流水线", 0.65)
            perspective_shots = self.run_perspective_mapping(project)

            # 6. 视频穿插
            self._report_progress("完整流水线", 0.80)
            timeline = self.run_video_interleave(project, perspective_shots)
            self.apply_interleave_to_project(project, timeline)

        self._report_progress("完整流水线", 1.0)
        return project


# ─────────────────────────────────────────────────────────────────────────────
# 为 MonologueSegment 添加穿插属性（向后兼容）
# ─────────────────────────────────────────────────────────────────────────────

def _add_interleave_attributes():
    """动态添加穿插相关属性到 MonologueSegment"""
    from .models.monologue import MonologueSegment
    from .models.perspective import TransitionType

    # 检查是否已添加
    if hasattr(MonologueSegment, 'show_original'):
        return

    MonologueSegment.show_original: bool = False
    MonologueSegment.original_start: Optional[float] = None
    MonologueSegment.original_end: Optional[float] = None
    MonologueSegment.transition_type: TransitionType = TransitionType.CUT
    MonologueSegment.zoom_factor: float = 1.0
    MonologueSegment.highlight_box = None
    MonologueSegment.narration_volume: float = 1.0
    MonologueSegment.original_audio_volume: float = 0.0
    MonologueSegment.interleave_subtitle: str = ""
    MonologueSegment.subtitle_style: str = "cinematic"


# 添加属性（模块加载时自动执行）
_add_interleave_attributes()


__all__ = [
    "PipelineIntegrator",
]
