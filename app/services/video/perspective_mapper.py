"""
Perspective Mapper
第一人称视角映射器——建立解说与画面的视角关系
"""

from typing import List, Optional, Dict, Any
import numpy as np

from .models.perspective_models import (
    SceneSegment, KeyFrame, PerspectiveShot, ViewpointAnchor,
    SubjectPosition, SubjectRole, NarrationSegment,
    InterleaveDecision, InterleaveMode, TransitionType
)


class PerspectiveMapper:
    """
    第一人称视角映射器
    
    核心职责:
    1. 分析画面中的主体位置，建立"我"的视觉坐标系
    2. 将解说内容与画面元素关联
    3. 决定何时展示原片画面（穿插策略）
    
    算法流程:
    - 输入: 场景分段 + 关键帧 + 解说文本
    - 处理: 主体检测 → 视角锚点 → 穿插决策
    - 输出: PerspectiveShot 列表
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        # 默认配置
        self.focal_length = self.config.get("focal_length", 50)  # 焦距 mm
        self.screen_width = self.config.get("screen_width", 1920)
        self.screen_height = self.config.get("screen_height", 1080)

    def map_scenes_to_perspective(
        self,
        scenes: List[SceneSegment],
        narration_segments: List[NarrationSegment],
        video_keyframes: List[KeyFrame],
        emotion_curve: Optional[List[float]] = None,
    ) -> List[PerspectiveShot]:
        """
        将场景与第一人称视角映射
        
        Args:
            scenes: 场景分段列表
            narration_segments: 解说片段列表
            video_keyframes: 视频关键帧
            emotion_curve: 情感强度曲线
            
        Returns:
            PerspectiveShot 列表
        """
        if not emotion_curve:
            # 默认情感曲线（全平静）
            emotion_curve = [0.3] * max(len(narration_segments), 1)

        shots = []
        for i, (scene, narration) in enumerate(zip(scenes, narration_segments)):
            # 提取视角锚点
            viewpoint = self._extract_viewpoint(scene, video_keyframes, i)

            # 确定原片展示策略
            emotional_intensity = emotion_curve[i] if i < len(emotion_curve) else 0.5

            # 决定是否展示原片
            show_original = self._should_show_original(
                narration=narration,
                scene=scene,
                emotional_intensity=emotional_intensity
            )

            # 计算原片权重
            original_weight = self._calculate_original_weight(
                emotional_intensity=emotional_intensity,
                narration_importance=scene.narration_importance
            )

            shot = PerspectiveShot(
                shot_id=f"shot_{scene.scene_id}",
                start_time=narration.start_time,
                end_time=narration.end_time,
                duration=narration.duration,
                viewpoint=viewpoint,
                primary_subject=self._find_primary_subject(scene),
                show_original_clip=show_original,
                original_clip_weight=original_weight,
                interleave_mode=self._decide_interleave_mode(emotional_intensity),
                emotional_intensity=emotional_intensity,
                narration_emotion=narration.emotion,
                narration_text=narration.text,
                scene_context=f"{scene.location} - {scene.atmosphere}",
            )
            shots.append(shot)

        return shots

    def _extract_viewpoint(
        self,
        scene: SceneSegment,
        keyframes: List[KeyFrame],
        scene_index: int,
    ) -> ViewpointAnchor:
        """
        从场景中提取视角锚点
        
        建立"我"在画面中的位置:
        - 基于画面构图规则（三分法、视线引导）
        - 基于场景氛围
        - 基于主体分布
        """
        subjects = scene.subjects

        if not subjects:
            # 默认：中心视角
            return ViewpointAnchor(
                spatial_x=50.0,
                spatial_y=50.0,
                spatial_depth=1,
                emotional_tone=self._infer_emotion(scene.atmosphere),
                narration_pov="first"
            )

        # 找主角
        protagonist = self._find_protagonist(subjects)
        if protagonist:
            # "我"的位置与主角相对（反方向）
            spatial_x = 100 - protagonist.x_percent
            spatial_y = protagonist.y_percent
            spatial_depth = protagonist.depth_layer
        else:
            # 取平均位置
            avg_x = sum(s.x_percent for s in subjects) / len(subjects)
            spatial_x = avg_x
            spatial_y = sum(s.y_percent for s in subjects) / len(subjects)
            spatial_depth = 1

        return ViewpointAnchor(
            spatial_x=spatial_x,
            spatial_y=spatial_y,
            spatial_depth=spatial_depth,
            emotional_tone=self._infer_emotion(scene.atmosphere),
            narration_pov="first"
        )

    def _find_protagonist(self, subjects: List[SubjectPosition]) -> Optional[SubjectPosition]:
        """找到主角（Protagonist）"""
        for subject in subjects:
            if subject.role == SubjectRole.PROTAGONIST:
                return subject
        return None

    def _find_primary_subject(self, scene: SceneSegment) -> Optional[SubjectPosition]:
        """找到场景中的主要主体"""
        if not scene.subjects:
            return None
        return min(scene.subjects, key=lambda s: s.depth_layer)

    def _should_show_original(
        self,
        narration: NarrationSegment,
        scene: SceneSegment,
        emotional_intensity: float,
    ) -> bool:
        """
        决定是否展示原片画面
        
        规则:
        - 情绪强度 >= 0.7 → 展示（沉浸感）
        - 叙事重要性 >= 0.8 → 展示（关键信息）
        - 解说提及具体物体/人物 → 展示（可视化佐证）
        - 情绪强度 < 0.3 → 可选展示
        """
        # 高情绪时刻 → 展示原片
        if emotional_intensity >= 0.7:
            return True

        # 关键叙事 → 展示原片
        if scene.narration_importance >= 0.8:
            return True

        # 解说中有具体指代 → 展示原片
        if self._has_specific_reference(narration.text):
            return True

        # 低情绪 + 不重要 → 纯解说
        if emotional_intensity < 0.3 and scene.narration_importance < 0.5:
            return False

        return True

    def _has_specific_reference(self, text: str) -> bool:
        """检查解说是否包含具体指代（需要可视化）"""
        # 简化的启发式判断
        specific_words = [
            "看", "这里", "这个", "那个人", "这个东西",
            "左边", "右边", "前面", "后面", "上方"
        ]
        return any(word in text for word in specific_words)

    def _calculate_original_weight(
        self,
        emotional_intensity: float,
        narration_importance: float,
    ) -> float:
        """
        计算原片权重 (0=纯解说, 1=纯原片)
        
        公式: weight = (emotional + importance) / 2 * 0.8
        """
        return min(1.0, (emotional_intensity + narration_importance) / 2 * 0.9)

    def _decide_interleave_mode(self, emotional_intensity: float) -> str:
        """根据情绪强度决定穿插模式"""
        if emotional_intensity >= 0.8:
            return "原片优先"
        elif emotional_intensity >= 0.5:
            return "交替"
        else:
            return "解说优先"

    def _infer_emotion(self, atmosphere: str) -> str:
        """从氛围推断情感基调"""
        mapping = {
            "bright": "warm",
            "dark": "tense",
            "mysterious": "tense",
            "peaceful": "neutral",
            "warm": "warm",
            "nostalgic": "nostalgic",
        }
        return mapping.get(atmosphere, "neutral")

    def determine_viewpoint_anchor(
        self,
        frame,
        subject_positions: List[SubjectPosition],
    ) -> ViewpointAnchor:
        """
        确定单帧的视角锚点
        
        Args:
            frame: 视频帧（numpy array 或路径）
            subject_positions: 检测到的主体位置列表
            
        Returns:
            ViewpointAnchor
        """
        if not subject_positions:
            return ViewpointAnchor(
                spatial_x=50.0,
                spatial_y=50.0,
                spatial_depth=1,
                emotional_tone="neutral",
                narration_pov="first"
            )

        protagonist = self._find_protagonist(subject_positions)
        if protagonist:
            return ViewpointAnchor(
                spatial_x=100 - protagonist.x_percent,
                spatial_y=protagonist.y_percent,
                spatial_depth=protagonist.depth_layer,
                emotional_tone="neutral",
                narration_pov="first"
            )

        avg_x = sum(s.x_percent for s in subject_positions) / len(subject_positions)
        return ViewpointAnchor(
            spatial_x=avg_x,
            spatial_y=sum(s.y_percent for s in subject_positions) / len(subject_positions),
            spatial_depth=1,
            emotional_tone="neutral",
            narration_pov="first"
        )
