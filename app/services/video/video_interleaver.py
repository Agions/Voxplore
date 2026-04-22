"""
Video Interleaver
视频穿插逻辑处理器——决定解说与原片的穿插策略
"""

from typing import List, Optional, Dict, Any, Tuple

from .models.perspective_models import (
    NarrationSegment, ClipSegment, PerspectiveShot,
    InterleaveDecision, InterleaveTimeline, InterleaveMode,
    InterleaveContext, TransitionType, SceneSegment,
    SubjectRole, SubjectPosition
)


class VideoInterleaver:
    """
    视频穿插逻辑处理器
    
    核心算法：解说与原片的穿插策略
    
    穿插模式:
    1. NARRATION_PRIORITY (解说优先): 原片作为佐证点缀
    2. ORIGINAL_PRIORITY (原片优先): 解说作为画外音背景
    3. EMOTIONAL_BURST (情绪高潮): 高潮时切入原片营造沉浸
    4. MINIMALIST (极简): 纯解说，最小化原片
    5. CINEMATIC (电影感): 根据场景动态平衡
    
    穿插决策流程:
    - 遍历解说片段
    - 查找对应原片片段
    - 应用情感曲线
    - 生成最终穿插决策
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.default_mode = InterleaveMode.CINEMATIC

    def decide_interleave(
        self,
        narration_timeline: List[NarrationSegment],
        original_clips: List[ClipSegment],
        perspective_shots: List[PerspectiveShot],
        scene_segments: List[SceneSegment],
        emotion_curve: List[float],
        context: Optional[InterleaveContext] = None,
    ) -> InterleaveTimeline:
        """
        生成最终穿插时间线
        
        Args:
            narration_timeline: 解说时间轴
            original_clips: 原片片段列表
            perspective_shots: 视角映射结果
            scene_segments: 场景分段
            emotion_curve: 情感强度曲线
            context: 穿插上下文配置
            
        Returns:
            InterleaveTimeline: 包含所有片段的排列和转场
        """
        ctx = context or InterleaveContext()
        decisions: List[InterleaveDecision] = []

        # 构建原片时间索引
        clip_lookup = self._build_clip_lookup(original_clips)

        # 遍历解说片段
        for i, narration in enumerate(narration_timeline):
            # 获取对应的视角信息
            shot = perspective_shots[i] if i < len(perspective_shots) else None
            emotional_intensity = emotion_curve[i] if i < len(emotion_curve) else 0.5

            # 查找重叠的原片片段
            overlapping_clips = self._find_overlapping_clips(
                narration.start_time,
                narration.end_time,
                original_clips
            )

            # 选择最佳原片片段
            selected_clip = self._select_best_clip(
                overlapping_clips,
                narration,
                shot,
                emotional_intensity
            )

            # 决定穿插策略
            decision = self._make_interleave_decision(
                narration=narration,
                clip=selected_clip,
                shot=shot,
                emotional_intensity=emotional_intensity,
                ctx=ctx
            )
            decisions.append(decision)

        # 计算统计
        total_duration = sum(d.narration_segment.duration for d in decisions)
        original_duration = sum(
            d.original_end - d.original_start
            for d in decisions
            if d.show_original and d.original_start is not None
        )

        return InterleaveTimeline(
            decisions=decisions,
            total_duration=total_duration,
            original_video_duration=original_clips[-1].end_time if original_clips else 0,
            narration_duration=total_duration,
            original_coverage_percent=original_duration / total_duration if total_duration > 0 else 0,
            narration_coverage_percent=100.0,
            interleave_mode=self._infer_interleave_mode(emotion_curve),
            emotion_curve=emotion_curve
        )

    def _build_clip_lookup(
        self,
        clips: List[ClipSegment]
    ) -> Dict[int, ClipSegment]:
        """构建时间索引"""
        return {clip.start_time: clip for clip in clips}

    def _find_overlapping_clips(
        self,
        start: float,
        end: float,
        clips: List[ClipSegment],
    ) -> List[ClipSegment]:
        """查找与给定时间范围重叠的原片片段"""
        return [
            clip for clip in clips
            if clip.start_time < end and clip.end_time > start
        ]

    def _select_best_clip(
        self,
        overlapping: List[ClipSegment],
        narration: NarrationSegment,
        shot: Optional[PerspectiveShot],
        emotional_intensity: float,
    ) -> Optional[ClipSegment]:
        """从多个重叠片段中选择最佳片段"""
        if not overlapping:
            return None
        if len(overlapping) == 1:
            return overlapping[0]

        # 评分函数
        def score(clip: ClipSegment) -> float:
            s = 0.0

            # 关键时刻优先
            if clip.is_key_moment:
                s += 2.0

            # 内容相关性 — 基于主体匹配评分
            if shot and shot.primary_subject:
                s += self._score_subject_match(shot.primary_subject, narration)

            # 时长适配
            duration_diff = abs(clip.duration - narration.duration)
            s -= duration_diff * 0.1

            return s

        return max(overlapping, key=score)

    def _make_interleave_decision(
        self,
        narration: NarrationSegment,
        clip: Optional[ClipSegment],
        shot: Optional[PerspectiveShot],
        emotional_intensity: float,
        ctx: InterleaveContext,
    ) -> InterleaveDecision:
        """
        生成单个穿插决策
        """
        # 决定是否展示原片
        if shot:
            show_original = shot.show_original_clip
            original_weight = shot.original_clip_weight
        else:
            show_original = emotional_intensity >= ctx.emotion_threshold
            original_weight = emotional_intensity

        # 确定转场
        transition = self._decide_transition(
            emotional_intensity, show_original, clip
        )

        # 决定音量
        narration_volume, original_volume = self._decide_volumes(
            original_weight, ctx
        )

        # 决定放大
        zoom_factor = 1.0
        highlight_box = None
        if shot and shot.primary_subject and show_original:
            zoom_factor, highlight_box = self._decide_zoom_highlight(
                shot.primary_subject, ctx
            )

        # 生成字幕
        subtitle_text = narration.text
        subtitle_style = self._infer_subtitle_style(emotional_intensity)

        return InterleaveDecision(
            narration_segment=narration,
            clip_segment=clip,
            show_original=show_original,
            original_start=clip.start_time if clip and show_original else None,
            original_end=clip.end_time if clip and show_original else None,
            transition=transition,
            zoom_factor=zoom_factor,
            highlight_box=highlight_box,
            narration_volume=narration_volume,
            original_audio_volume=original_volume,
            subtitle_text=subtitle_text,
            subtitle_style=subtitle_style
        )

    def _decide_transition(
        self,
        emotional_intensity: float,
        show_original: bool,
        clip: Optional[ClipSegment],
    ) -> TransitionType:
        """决定转场类型"""
        if not show_original:
            return TransitionType.SUBTITLE_ONLY

        if emotional_intensity >= 0.8:
            # 高潮时刻用叠化
            return TransitionType.DISSOLVE
        elif emotional_intensity >= 0.6:
            # 中等情绪用淡入淡出
            return TransitionType.FADE
        elif clip and clip.is_key_moment:
            # 关键时刻用高亮放大
            return TransitionType.ZOOM_HIGHLIGHT
        else:
            return TransitionType.CUT

    def _decide_volumes(
        self,
        original_weight: float,
        ctx: InterleaveContext,
    ) -> Tuple[float, float]:
        """决定解说和原片音量"""
        # 解说音量恒定为 1.0
        narration_volume = 1.0

        # 原片音量根据权重和配置决定
        original_volume = original_weight * 0.3 if original_weight > 0 else 0.0

        return narration_volume, original_volume

    def _decide_zoom_highlight(
        self,
        subject,  # SubjectPosition
        ctx: InterleaveContext,
    ) -> Tuple[float, Optional[Tuple[float, float, float, float]]]:
        """决定是否放大高亮主体"""
        if not ctx.allow_zoom_highlight:
            return 1.0, None

        # 放大因子
        zoom = 1.5

        # 高亮框 (x, y, width, height) 百分比
        box = (
            subject.x_percent - 10,
            subject.y_percent - 10,
            20,
            20
        )

        return zoom, box

    def _score_subject_match(
        self,
        subject: SubjectPosition,
        narration: NarrationSegment,
    ) -> float:
        """
        基于主体角色与解说情感的匹配度评分。

        评分维度:
        - 角色-情感关联 (0.0-1.0): PROTAGONIST 关联内心情感词, SUPPORTING 关联叙述词
        - 空间构图 (0.0-0.5): 主角居中/黄金分割构图加分
        - 视线方向 (0.0-0.3): 与解说视角(pov)匹配的视线加分
        """
        score = 0.0

        # ── 角色-情感关联 ─────────────────────────────────
        emotion = narration.emotion.lower() if narration.emotion else "neutral"
        role = subject.role

        # 内心情感 → 主角（第一人称代入感）
        inner_emotions = {"sad", "melancholy", "nostalgic", "fearful", "tender", "neutral"}
        # 叙述性情感 → 配角/背景（观察者视角）
        narrative_emotions = {"excited", "neutral", "calm", "tense"}

        if role == SubjectRole.PROTAGONIST:
            if emotion in inner_emotions:
                score += 1.0
            else:
                score += 0.3
        elif role == SubjectRole.SUPPORTING:
            if emotion in narrative_emotions:
                score += 0.8
            else:
                score += 0.4
        else:  # BACKGROUND / UNKNOWN
            score += 0.1

        # ── 空间构图 ────────────────────────────────────
        # 黄金分割 / 中心构图加分
        cx, cy = subject.x_percent, subject.y_percent
        is_center = 40 <= cx <= 60 and 40 <= cy <= 60
        is_golden = (
            (55 <= cx <= 65 and 35 <= cy <= 45) or   # 右上黄金点
            (35 <= cx <= 45 and 55 <= cy <= 65) or   # 左下黄金点
            (55 <= cx <= 65 and 55 <= cy <= 65) or   # 右下黄金点
            (35 <= cx <= 45 and 35 <= cy <= 45)       # 左上黄金点
        )
        if is_center:
            score += 0.5
        elif is_golden:
            score += 0.3

        # ── 视线方向 ────────────────────────────────────
        gaze = subject.gaze_direction
        if gaze == "center":
            score += 0.3
        elif gaze in ("left", "right"):
            score += 0.1
        # "up"/"down" 不加分

        return score

    def _infer_subtitle_style(self, emotional_intensity: float) -> str:
        """根据情绪推断字幕风格"""
        if emotional_intensity >= 0.8:
            return "cinematic_intense"
        elif emotional_intensity >= 0.5:
            return "cinematic"
        else:
            return "minimal"

    def _infer_interleave_mode(self, emotion_curve: List[float]) -> InterleaveMode:
        """从情感曲线推断整体穿插模式"""
        if not emotion_curve:
            return self.default_mode

        avg_emotion = sum(emotion_curve) / len(emotion_curve)

        if avg_emotion >= 0.7:
            return InterleaveMode.EMOTIONAL_BURST
        elif avg_emotion >= 0.5:
            return InterleaveMode.CINEMATIC
        elif avg_emotion >= 0.3:
            return InterleaveMode.NARRATION_PRIORITY
        else:
            return InterleaveMode.MINIMALIST

    # ─────────────────────────────────────────────────────────────
    # 高层次 API
    # ─────────────────────────────────────────────────────────────

    def interleave_narration_priority(
        self,
        narration_timeline: List[NarrationSegment],
        original_clips: List[ClipSegment],
    ) -> InterleaveTimeline:
        """解说优先模式——原片仅在关键时刻展示"""
        ctx = InterleaveContext(
            max_original_ratio=0.3,
            min_narration_ratio=0.7,
            emotion_threshold=0.5
        )
        # 使用空视角和默认情感曲线
        empty_shots = [PerspectiveShot(
            shot_id=f"shot_{i}",
            start_time=n.start_time,
            end_time=n.end_time,
            duration=n.duration,
            viewpoint=None,
            show_original_clip=False,
            original_clip_weight=0.0,
        ) for i, n in enumerate(narration_timeline)]

        emotion_curve = [0.3] * len(narration_timeline)

        return self.decide_interleave(
            narration_timeline=narration_timeline,
            original_clips=original_clips,
            perspective_shots=empty_shots,
            scene_segments=[],
            emotion_curve=emotion_curve,
            context=ctx
        )

    def interleave_cinematic(
        self,
        narration_timeline: List[NarrationSegment],
        original_clips: List[ClipSegment],
        emotion_curve: List[float],
    ) -> InterleaveTimeline:
        """电影感模式——动态平衡解说与原片"""
        ctx = InterleaveContext(
            max_original_ratio=0.6,
            min_narration_ratio=0.4,
            emotion_threshold=0.6,
            allow_zoom_highlight=True
        )
        empty_shots = [PerspectiveShot(
            shot_id=f"shot_{i}",
            start_time=n.start_time,
            end_time=n.end_time,
            duration=n.duration,
            viewpoint=None,
            show_original_clip=emotion_curve[i] >= 0.6 if i < len(emotion_curve) else False,
            original_clip_weight=emotion_curve[i] if i < len(emotion_curve) else 0.5,
        ) for i, n in enumerate(narration_timeline)]

        return self.decide_interleave(
            narration_timeline=narration_timeline,
            original_clips=original_clips,
            perspective_shots=empty_shots,
            scene_segments=[],
            emotion_curve=emotion_curve,
            context=ctx
        )
