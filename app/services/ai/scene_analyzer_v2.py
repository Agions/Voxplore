#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
场景分析器 V2 (Scene Analyzer V2)

包含完整的场景分析实现：
- SceneAnalyzer: 基础版（来自原有 scene_analyzer.py）
- SceneAnalyzerV2: 扩展版，增加重要性评分、关键时刻提取、场景上下文提示

使用示例:
    from app.services.ai import SceneAnalyzer   # 基础版
    from app.services.ai import SceneAnalyzerV2  # 增强版（推荐）

    analyzer = SceneAnalyzerV2()
    scenes = analyzer.analyze_with_importance('video.mp4')

    # 提取最佳关键时刻
    key_moments = analyzer.extract_key_moments(scenes, top_k=5)

    # 生成场景上下文提示
    context_prompt = analyzer.generate_scene_context_prompt(scenes)
"""

import logging
import subprocess
import re

from pathlib import Path
from typing import List, Optional, Callable, Dict, Any

from .scene_models import SceneType, SceneInfo, AnalysisConfig


logger = logging.getLogger(__name__)


# =============================================================================
# 场景类型优先级（数值越高越重要）
# =============================================================================
SCENE_TYPE_PRIORITY: Dict[SceneType, int] = {
    SceneType.LANDSCAPE: 10,     # 风景画面 - 最适合展示
    SceneType.B_ROLL: 8,         # 素材画面 - 适合混剪
    SceneType.ACTION: 6,         # 动作场景
    SceneType.TALKING_HEAD: 4,   # 人物讲话 - 较少使用
    SceneType.TRANSITION: 2,      # 转场 - 不适合
    SceneType.TITLE: 3,           # 标题画面
    SceneType.PRODUCT: 5,         # 产品展示
    SceneType.UNKNOWN: 1,        # 未知 - 最低优先级
}


# =============================================================================
# 基础场景分析器（原 scene_analyzer.py 的实现）
# =============================================================================
class SceneAnalyzer:
    """
    场景分析器

    集成 PySceneDetect 和 FFmpeg 进行视频场景检测和分析。
    优先使用 PySceneDetect（更准确），回退到 FFmpeg 方法。
    """

    def __init__(self, config: Optional[AnalysisConfig] = None):
        self.config = config or AnalysisConfig()
        self._pyscenect_available = self._check_pyscenect()

    def _check_pyscenect(self) -> bool:
        """检查 PySceneDetect 是否可用"""
        import importlib.util
        return importlib.util.find_spec("scenedetect") is not None

    def analyze(self, video_path: str) -> List[SceneInfo]:
        """
        分析视频场景

        Args:
            video_path: 视频文件路径

        Returns:
            场景列表
        """
        video_path_obj = Path(video_path)
        if not video_path_obj.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        # 获取视频时长
        duration = self._get_video_duration(str(video_path))

        # 检测场景变化 - 优先使用 PySceneDetect
        if self.config.use_pyscenect and self._pyscenect_available:
            scene_times = self._detect_scenes_pyscenect(str(video_path))
        else:
            scene_times = self._detect_scene_changes(str(video_path))

        # 构建场景列表
        scenes = self._build_scenes(scene_times, duration)

        # 分析每个场景
        for scene in scenes:
            self._analyze_scene(str(video_path), scene)

        # 提取关键帧（如果启用）
        if self.config.extract_keyframes:
            self._extract_keyframes(str(video_path), scenes)

        return scenes

    def _get_video_duration(self, video_path: str) -> float:
        """获取视频时长"""
        from ..video_tools.ffmpeg_tool import FFmpegTool
        return FFmpegTool.get_duration(video_path)

    def _detect_scenes_pyscenect(self, video_path: str) -> List[float]:
        """使用 PySceneDetect 检测场景变化"""
        try:
            from scenedetect import open_video, SceneManager
            from scenedetect.detectors import ContentDetector, AdaptiveDetector, ThresholdDetector

            video = open_video(video_path)
            scene_manager = SceneManager()

            threshold = self.config.scene_threshold

            if self.config.detector_type == "adaptive":
                from scenedetect.detectors.adaptive_detector import AdaptiveDetector
                scene_manager.add_detector(
                    AdaptiveDetector(
                        adaptive_threshold=threshold * 50,
                        min_scene_len=max(int(self.config.min_scene_duration * 30), 15)
                    )
                )
            elif self.config.detector_type == "threshold":
                scene_manager.add_detector(
                    ThresholdDetector(threshold=int(threshold * 255))
                )
            else:
                scene_manager.add_detector(
                    ContentDetector(
                        threshold=threshold * 50,
                        min_scene_len=max(int(self.config.min_scene_duration * 30), 15)
                    )
                )

            try:
                scene_manager.detect_scenes(video, show_progress=False)
            except Exception:
                return [0.0]

            scene_list = scene_manager.get_scene_list()

            if not scene_list:
                return [0.0]

            scene_times = [0.0]
            for scene in scene_list:
                start_time = scene[0].get_seconds()
                scene_times.append(start_time)

            return scene_times

        except ImportError as e:
            logger.warning(f"PySceneDetect 导入失败: {e}")
            self._pyscenect_available = False
            return self._detect_scene_changes(video_path)
        except Exception as e:
            logger.error(f"PySceneDetect 场景检测失败: {e}")
            return self._detect_scene_changes(video_path)

    def _detect_scene_changes(self, video_path: str) -> List[float]:
        """使用 FFmpeg 检测场景变化时间点（回退方法）"""
        threshold = self.config.scene_threshold

        cmd = [
            'ffmpeg', '-i', video_path,
            '-filter:v', f"select='gt(scene,{threshold})',showinfo",
            '-f', 'null', '-'
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            scene_times = [0.0]

            pattern = r'pts_time:(\d+\.?\d*)'
            matches = re.findall(pattern, result.stderr)

            for match in matches:
                time = float(match)
                if not scene_times or (time - scene_times[-1]) >= self.config.min_scene_duration:
                    scene_times.append(time)

            return scene_times

        except subprocess.TimeoutExpired:
            logger.warning("场景检测超时")
            return [0.0]
        except Exception as e:
            logger.error(f"场景检测失败: {e}")
            return [0.0]

    def _build_scenes(self, scene_times: List[float], total_duration: float) -> List[SceneInfo]:
        """根据场景变化时间点构建场景列表"""
        scenes = []

        scene_times = sorted(set(scene_times))

        for i in range(len(scene_times)):
            start = scene_times[i]
            end = scene_times[i + 1] if i + 1 < len(scene_times) else total_duration

            if end - start >= self.config.min_scene_duration:
                scene = SceneInfo(
                    index=i,
                    start=start,
                    end=end,
                    duration=end - start,
                )
                scenes.append(scene)

        return scenes

    def _analyze_scene(self, video_path: str, scene: SceneInfo) -> None:
        """分析单个场景的特征"""
        scene.avg_brightness = self._get_avg_brightness(
            video_path, scene.start, scene.duration
        )

        scene.motion_level = self._get_motion_level(
            video_path, scene.start, scene.duration
        )

        if self.config.analyze_audio:
            scene.audio_level = self._get_audio_level(
                video_path, scene.start, scene.duration
            )

        scene.suitability_score = self._calculate_suitability(scene)

        scene.type = self._infer_scene_type(scene)

    def _get_avg_brightness(self, video_path: str, start: float, duration: float) -> float:
        """获取场景平均亮度"""
        try:
            cmd = [
                'ffmpeg', '-ss', str(start), '-t', str(min(duration, 2)),
                '-i', video_path,
                '-vf', 'signalstats',
                '-f', 'null', '-'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            match = re.search(r'YAVG:(\d+\.?\d*)', result.stderr)
            if match:
                return float(match.group(1)) / 255.0

        except Exception:
            logger.debug("Operation failed")

        return 0.5

    def _get_motion_level(self, video_path: str, start: float, duration: float) -> float:
        """获取场景运动程度"""
        try:
            cmd = [
                'ffmpeg', '-ss', str(start), '-t', str(min(duration, 2)),
                '-i', video_path,
                '-filter:v', "select='gte(scene,0)',metadata=print",
                '-f', 'null', '-'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            scores = re.findall(r'lavfi\.scene_score=(\d+\.?\d*)', result.stderr)
            if scores:
                avg_score = sum(float(s) for s in scores) / len(scores)
                return min(1.0, avg_score * 2)

        except Exception:
            logger.debug("Operation failed")

        return 0.3

    def _get_audio_level(self, video_path: str, start: float, duration: float) -> float:
        """获取场景音频音量"""
        try:
            cmd = [
                'ffmpeg', '-ss', str(start), '-t', str(min(duration, 2)),
                '-i', video_path,
                '-af', 'volumedetect',
                '-f', 'null', '-'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            match = re.search(r'mean_volume:\s*([-\d.]+)', result.stderr)
            if match:
                db = float(match.group(1))
                return max(0, min(1, (db + 60) / 60))

        except Exception:
            logger.debug("Operation failed")

        return 0.5

    def _calculate_suitability(self, scene: SceneInfo) -> float:
        """计算场景作为解说画面的适用性"""
        score = 50.0

        if 2 <= scene.duration <= 5:
            score += 20
        elif scene.duration < 1:
            score -= 20
        elif scene.duration > 10:
            score -= 10

        if 0.2 <= scene.motion_level <= 0.6:
            score += 15
        elif scene.motion_level > 0.8:
            score -= 10

        if 0.3 <= scene.avg_brightness <= 0.7:
            score += 15
        else:
            score -= 10

        return max(0, min(100, score))

    def _infer_scene_type(self, scene: SceneInfo) -> SceneType:
        """根据特征推断场景类型"""
        if scene.audio_level > 0.7 and scene.motion_level < 0.3:
            return SceneType.TALKING_HEAD
        elif scene.motion_level > 0.7:
            return SceneType.ACTION
        elif scene.duration < 1:
            return SceneType.TRANSITION
        elif scene.motion_level < 0.2 and scene.audio_level < 0.2:
            return SceneType.LANDSCAPE
        else:
            return SceneType.B_ROLL

    def _extract_keyframes(self, video_path: str, scenes: List[SceneInfo]) -> None:
        """为每个场景提取关键帧"""
        if not self.config.keyframe_dir:
            keyframe_dir = Path(video_path).parent / "keyframes"
        else:
            keyframe_dir = Path(self.config.keyframe_dir)

        keyframe_dir.mkdir(parents=True, exist_ok=True)

        for scene in scenes:
            timestamp = scene.start + scene.duration / 2
            output_path = keyframe_dir / f"scene_{scene.index:03d}.jpg"

            try:
                cmd = [
                    'ffmpeg', '-ss', str(timestamp),
                    '-i', video_path,
                    '-vframes', '1',
                    '-q:v', '2',
                    '-y', str(output_path)
                ]

                result = subprocess.run(cmd, capture_output=True, timeout=30)

                if result.returncode == 0:
                    scene.keyframe_path = str(output_path)

            except Exception as e:
                logger.error(f"提取关键帧失败 (场景 {scene.index}): {e}")

    def get_best_scenes(
        self,
        scenes: List[SceneInfo],
        count: int = 10,
        min_score: float = 50.0,
    ) -> List[SceneInfo]:
        """获取最适合作为解说画面的场景"""
        filtered = [s for s in scenes if s.suitability_score >= min_score]

        sorted_scenes = sorted(
            filtered,
            key=lambda s: s.suitability_score,
            reverse=True
        )

        return sorted_scenes[:count]

    def get_scenes_for_duration(
        self,
        scenes: List[SceneInfo],
        target_duration: float,
    ) -> List[SceneInfo]:
        """获取满足目标时长的场景组合"""
        sorted_scenes = sorted(
            scenes,
            key=lambda s: s.suitability_score,
            reverse=True
        )

        selected = []
        total = 0.0

        for scene in sorted_scenes:
            if total >= target_duration:
                break
            selected.append(scene)
            total += scene.duration

        selected.sort(key=lambda s: s.start)

        return selected

    def split_video_by_scenes(
        self,
        video_path: str,
        output_dir: str,
        scenes: Optional[List[SceneInfo]] = None,
    ) -> List[str]:
        """将视频按场景分割"""
        if scenes is None:
            scenes = self.analyze(video_path)

        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)

        video_stem = Path(video_path).stem
        output_paths = []

        for scene in scenes:
            output_path = output_dir_path / f"{video_stem}_scene_{scene.index:03d}.mp4"

            try:
                cmd = [
                    'ffmpeg', '-y',
                    '-ss', str(scene.start),
                    '-t', str(scene.duration),
                    '-i', video_path,
                    '-c', 'copy',
                    '-avoid_negative_ts', 'make_zero',
                    str(output_path)
                ]

                result = subprocess.run(cmd, capture_output=True, timeout=60)

                if result.returncode == 0:
                    output_paths.append(str(output_path))

            except Exception as e:
                logger.error(f"分割场景失败 (场景 {scene.index}): {e}")

        return output_paths


# =============================================================================
# 场景分析器 V2（扩展版）
# =============================================================================
class SceneAnalyzerV2(SceneAnalyzer):
    """
    场景分析器 V2

    在 SceneAnalyzer 基础上扩展了重要性评分和关键时刻提取功能。
    适合用于 AI 解说和智能混剪场景。
    """

    def __init__(self, config: Optional[AnalysisConfig] = None):
        """
        初始化场景分析器 V2

        Args:
            config: 分析配置，如果为 None 则使用默认配置
        """
        super().__init__(config)
        self._importance_weights = {
            'duration': 0.20,
            'brightness': 0.15,
            'motion': 0.15,
            'scene_type': 0.30,
            'audio': 0.20,
        }

    def analyze_with_importance(
        self,
        video_path: str,
        narration_importance_fn: Optional[Callable[[SceneInfo], float]] = None,
    ) -> List[SceneInfo]:
        """
        分析视频场景并计算重要性评分

        在原有 analyze() 方法基础上，为每个场景计算 suitability_score
        和可选的 narration_importance。

        Args:
            video_path: 视频文件路径
            narration_importance_fn: 可选的回调函数，用于计算叙事重要性。
                                     函数签名: (SceneInfo) -> float (0-1)
                                     如果为 None，则使用默认计算方法

        Returns:
            场景列表，每个场景都包含计算好的 suitability_score

        Raises:
            FileNotFoundError: 视频文件不存在
        """
        scenes = super().analyze(video_path)

        for scene in scenes:
            scene.suitability_score = self._calculate_enhanced_suitability(scene)

            if narration_importance_fn is not None:
                scene.narration_importance = narration_importance_fn(scene)
            elif not hasattr(scene, 'narration_importance') or scene.narration_importance <= 0:
                scene.narration_importance = self._calculate_default_narration_importance(scene)
            # else: 保留现有 scene.narration_importance 值

        return scenes

    def _calculate_enhanced_suitability(self, scene: SceneInfo) -> float:
        """计算增强版适用性评分 (0-100)"""
        score = 50.0

        duration_score = self._score_duration(scene.duration)
        score += duration_score * self._importance_weights['duration'] * 2

        brightness_score = self._score_brightness(scene.avg_brightness)
        score += brightness_score * self._importance_weights['brightness'] * 2

        motion_score = self._score_motion(scene.motion_level)
        score += motion_score * self._importance_weights['motion'] * 2

        type_score = self._score_scene_type(scene.type)
        score += type_score * self._importance_weights['scene_type'] * 2

        audio_score = self._score_audio(scene.audio_level)
        score += audio_score * self._importance_weights['audio'] * 2

        return max(0.0, min(100.0, score))

    def _score_duration(self, duration: float) -> float:
        """评分时长因素 - 最佳范围: 3-15秒"""
        if 3.0 <= duration <= 15.0:
            return 100.0
        elif 1.0 <= duration < 3.0 or 15.0 < duration <= 30.0:
            return 60.0
        else:
            return 20.0

    def _score_brightness(self, brightness: float) -> float:
        """评分亮度因素 - 最佳范围: 0.3-0.7"""
        if 0.3 <= brightness <= 0.7:
            return 100.0
        elif brightness < 0.3:
            return (brightness / 0.3) * 100.0
        else:
            return ((1.0 - brightness) / 0.3) * 100.0

    def _score_motion(self, motion: float) -> float:
        """评分运动程度因素 - 最佳范围: 0.2-0.6"""
        if 0.2 <= motion <= 0.6:
            return 100.0
        elif motion < 0.1:
            return 30.0
        elif motion < 0.2:
            return 30.0 + (motion - 0.1) / 0.1 * 70.0
        elif motion <= 0.9:
            return 100.0 - (motion - 0.6) / 0.3 * 40.0
        else:
            return 20.0

    def _score_scene_type(self, scene_type: SceneType) -> float:
        """评分场景类型因素"""
        priority = SCENE_TYPE_PRIORITY.get(scene_type, 1)
        max_priority = max(SCENE_TYPE_PRIORITY.values())
        return (priority / max_priority) * 100.0

    def _score_audio(self, audio_level: float) -> float:
        """评分音频因素"""
        return audio_level * 100.0

    def _calculate_default_narration_importance(self, scene: SceneInfo) -> float:
        """计算默认叙事重要性"""
        type_weight = SCENE_TYPE_PRIORITY.get(scene.type, 1) / max(SCENE_TYPE_PRIORITY.values())

        if 3.0 <= scene.duration <= 15.0:
            duration_weight = 1.0
        elif 1.0 <= scene.duration < 3.0 or 15.0 < scene.duration <= 30.0:
            duration_weight = 0.6
        else:
            duration_weight = 0.2

        suitability_weight = scene.suitability_score / 100.0

        importance = (
            type_weight * 0.4 +
            duration_weight * 0.3 +
            suitability_weight * 0.3
        )

        return max(0.0, min(1.0, importance))

    def extract_key_moments(
        self,
        scenes: List[SceneInfo],
        top_k: int = 5,
        min_score: float = 30.0,
    ) -> List[SceneInfo]:
        """提取关键时刻（得分最高的场景）"""
        filtered = [s for s in scenes if s.suitability_score >= min_score]

        sorted_scenes = sorted(
            filtered,
            key=lambda s: s.suitability_score,
            reverse=True
        )

        return sorted_scenes[:top_k]

    def extract_key_moments_by_type(
        self,
        scenes: List[SceneInfo],
        scene_type: SceneType,
        top_k: int = 3,
    ) -> List[SceneInfo]:
        """按场景类型提取关键时刻"""
        filtered = [s for s in scenes if s.type == scene_type]

        sorted_scenes = sorted(
            filtered,
            key=lambda s: s.suitability_score,
            reverse=True
        )

        return sorted_scenes[:top_k]

    def generate_scene_context_prompt(self, scenes: List[SceneInfo]) -> str:
        """生成场景上下文提示（用于 ScriptGenerator）"""
        if not scenes:
            return "## 场景列表\n\n*暂无场景数据*"

        lines = ["## 场景列表\n"]

        for i, scene in enumerate(scenes, 1):
            start_str = self._format_timestamp(scene.start)
            end_str = self._format_timestamp(scene.end)

            type_name = self._get_scene_type_name_cn(scene.type)

            lines.append(f"{i}. **{start_str} - {end_str}** {type_name}")
            lines.append(f"   - 类型: `{scene.type.value}`")
            lines.append(f"   - 评分: {scene.suitability_score:.0f}/100")

            if scene.description:
                lines.append(f"   - 描述: {scene.description}")

            details = []
            if scene.avg_brightness > 0:
                brightness_desc = self._describe_brightness(scene.avg_brightness)
                details.append(f"亮度{brightness_desc}")
            if scene.motion_level > 0:
                motion_desc = self._describe_motion(scene.motion_level)
                details.append(f"运动{motion_desc}")
            if scene.audio_level > 0:
                details.append(f"音频{'有' if scene.audio_level > 0.3 else '弱'}")

            if details:
                lines.append(f"   - 特征: {', '.join(details)}")

            lines.append("")

        return "\n".join(lines)

    def generate_brief_scene_summary(
        self,
        scenes: List[SceneInfo],
        max_scenes: int = 10,
    ) -> str:
        """生成简短场景摘要（适用于提示词）"""
        if not scenes:
            return "视频包含0个有效场景。"

        sorted_scenes = sorted(
            scenes,
            key=lambda s: s.suitability_score,
            reverse=True
        )[:max_scenes]

        parts = [f"视频共 {len(scenes)} 个场景，选取最重要的 {len(sorted_scenes)} 个：\n"]

        for scene in sorted_scenes:
            start_str = self._format_timestamp(scene.start)
            type_name = self._get_scene_type_name_cn(scene.type)
            score = scene.suitability_score

            parts.append(f"- [{start_str}] {type_name} (评分:{score:.0f})")

        return "\n".join(parts)

    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳为 MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def _get_scene_type_name_cn(self, scene_type: SceneType) -> str:
        """获取场景类型中文名"""
        names = {
            SceneType.LANDSCAPE: "风景画面",
            SceneType.B_ROLL: "素材画面",
            SceneType.ACTION: "动作场景",
            SceneType.TALKING_HEAD: "人物讲话",
            SceneType.TRANSITION: "转场",
            SceneType.TITLE: "标题画面",
            SceneType.PRODUCT: "产品展示",
            SceneType.UNKNOWN: "未知",
        }
        return names.get(scene_type, "未知")

    def _describe_brightness(self, brightness: float) -> str:
        """描述亮度"""
        if brightness < 0.3:
            return "暗"
        elif brightness > 0.7:
            return "亮"
        else:
            return "适中"

    def _describe_motion(self, motion: float) -> str:
        """描述运动程度"""
        if motion < 0.2:
            return "静态"
        elif motion > 0.7:
            return "剧烈"
        else:
            return "适中"


# =============================================================================
# 向后兼容：SceneAnalyzer = SceneAnalyzerV2
# =============================================================================
# 注意：原有的 scene_analyzer.py 文件现在是一个兼容重导出。
# 所有使用 from ..ai.scene_analyzer import SceneAnalyzer 的代码
# 实际上获得的是 SceneAnalyzerV2（推荐使用的增强版）。
SceneAnalyzer = SceneAnalyzerV2


# =============================================================================
# 便捷函数
# =============================================================================
def analyze_video(video_path: str, config: Optional[AnalysisConfig] = None) -> List[SceneInfo]:
    """分析视频场景的便捷函数"""
    analyzer = SceneAnalyzer(config)
    return analyzer.analyze(video_path)


def demo_analyze():
    """演示场景分析"""
    analyzer = SceneAnalyzer(AnalysisConfig(
        scene_threshold=0.3,
        min_scene_duration=0.5,
        extract_keyframes=True,
        use_pyscenect=True,
    ))

    print(f"PySceneDetect 可用: {analyzer._pyscenect_available}")

    scenes = analyzer.analyze("input.mp4")

    print(f"检测到 {len(scenes)} 个场景")
    print("-" * 50)

    for scene in scenes:
        print(f"场景 {scene.index}")
        print(f"  时间: {scene.start:.2f}s - {scene.end:.2f}s ({scene.duration:.2f}s)")
        print(f"  类型: {scene.type.value}")
        print(f"  亮度: {scene.avg_brightness:.2f}")
        print(f"  运动: {scene.motion_level:.2f}")
        print(f"  音量: {scene.audio_level:.2f}")
        print(f"  评分: {scene.suitability_score:.1f}/100")
        print()

    best = analyzer.get_best_scenes(scenes, count=5)
    print("\n最佳场景 (前5个):")
    for scene in best:
        print(f"  场景 {scene.index}: {scene.suitability_score:.1f}分")


if __name__ == '__main__':
    demo_analyze()
