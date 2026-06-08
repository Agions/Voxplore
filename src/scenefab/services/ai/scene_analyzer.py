#!/usr/bin/env python3

"""
场景分析器 (Scene Analyzer)

提供场景检测、镜头评分、关键帧提取、上下文提示生成等功能。

使用示例:
    from scenefab.services.ai import SceneAnalyzer

    analyzer = SceneAnalyzer()
    scenes = analyzer.analyze('video.mp4')

    key_moments = analyzer.extract_key_moments(scenes, top_k=5)

注意:
    SceneAnalyzerV2 已移至 scene_analyzer_v2.py。
"""

import logging
import re
from pathlib import Path

from ...utils.security import get_ffmpeg_executor
from .scene_models import AnalysisConfig, SceneInfo, SceneType

logger = logging.getLogger(__name__)


# =============================================================================
# 基础场景分析器（原 scene_analyzer.py 的实现）
# =============================================================================
__all__ = ["SceneAnalyzer"]


class SceneAnalyzer:
    """
    场景分析器

    集成 PySceneDetect 和 FFmpeg 进行视频场景检测和分析。
    优先使用 PySceneDetect（更准确），回退到 FFmpeg 方法。
    """

    def __init__(self, config: AnalysisConfig | None = None):
        self.config = config or AnalysisConfig()
        self._pyscenect_available = self._check_pyscenect()
        self._executor = get_ffmpeg_executor()

    def _check_pyscenect(self) -> bool:
        """检查 PySceneDetect 是否可用"""
        import importlib.util
        return importlib.util.find_spec("scenedetect") is not None

    def analyze(self, video_path: str) -> list[SceneInfo]:
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
        from ..video_tools.ffmpeg_tool import FFmpegTool
        duration = FFmpegTool.get_duration(str(video_path))

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

    def _detect_scenes_pyscenect(self, video_path: str) -> list[float]:
        """使用 PySceneDetect 检测场景变化"""
        try:
            from scenedetect import SceneManager, open_video
            from scenedetect.detectors import ContentDetector, ThresholdDetector

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
            except Exception as e:
                logger.warning(f"Scene detection failed: {e}, returning [0.0]")
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

    def _detect_scene_changes(self, video_path: str) -> list[float]:
        """使用 FFmpeg 检测场景变化时间点（回退方法）"""
        threshold = self.config.scene_threshold

        cmd = [
            'ffmpeg', '-i', video_path,
            '-filter:v', f"select='gt(scene,{threshold})',showinfo",
            '-f', 'null', '-'
        ]

        try:
            result = self._executor.run(cmd, timeout=300)

            scene_times = [0.0]

            pattern = r'pts_time:(\d+\.?\d*)'
            matches = re.findall(pattern, result.stderr)

            for match in matches:
                time = float(match)
                if not scene_times or (time - scene_times[-1]) >= self.config.min_scene_duration:
                    scene_times.append(time)

            return scene_times

        except TimeoutError:
            logger.warning("场景检测超时")
            return [0.0]
        except Exception as e:
            logger.error(f"场景检测失败: {e}")
            return [0.0]

    def _build_scenes(self, scene_times: list[float], total_duration: float) -> list[SceneInfo]:
        """根据场景变化时间点构建场景列表"""
        scenes = []

        scene_times = sorted(set(scene_times))

        for i, start in enumerate(scene_times):
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

    def _run_video_metric(
        self,
        video_path: str,
        start: float,
        duration: float,
        vf: str,
        regex: str,
        default: float,
    ) -> float:
        """通用的 FFmpeg 视频指标提取"""
        try:
            cmd = [
                'ffmpeg', '-ss', str(start), '-t', str(min(duration, 2)),
                '-i', video_path, '-vf', vf, '-f', 'null', '-'
            ]
            result = self._executor.run(cmd, timeout=30)
            match = re.search(regex, result.stderr)
            if match:
                return float(match.group(1))
        except Exception:
            pass
        return default

    def _get_avg_brightness(self, video_path: str, start: float, duration: float) -> float:
        """获取场景平均亮度"""
        val = self._run_video_metric(
            video_path, start, duration,
            vf='signalstats',
            regex=r'YAVG:(\d+\.?\d*)',
            default=0.5,
        )
        return val / 255.0

    def _get_motion_level(self, video_path: str, start: float, duration: float) -> float:
        """获取场景运动程度"""
        try:
            cmd = [
                'ffmpeg', '-ss', str(start), '-t', str(min(duration, 2)),
                '-i', video_path,
                '-filter:v', "select='gte(scene,0)',metadata=print",
                '-f', 'null', '-'
            ]
            result = self._executor.run(cmd, timeout=30)
            scores = re.findall(r'lavfi\.scene_score=(\d+\.?\d*)', result.stderr)
            if scores:
                avg_score = sum(float(s) for s in scores) / len(scores)
                return min(1.0, avg_score * 2)
        except Exception as e:
            logger.debug(f"Scene score detection failed: {e}")
        return 0.3

    def _get_audio_level(self, video_path: str, start: float, duration: float) -> float:
        """获取场景音频音量"""
        db = self._run_video_metric(
            video_path, start, duration,
            vf='volumedetect',
            regex=r'mean_volume:\s*([-\d.]+)',
            default=-60.0,
        )
        return max(0, min(1, (db + 60) / 60))

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

    def _extract_keyframes(self, video_path: str, scenes: list[SceneInfo]) -> None:
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

                result = self._executor.run(cmd, timeout=60)

                if result.returncode == 0:
                    scene.keyframe_path = str(output_path)

            except Exception as e:
                logger.error(f"提取关键帧失败 (场景 {scene.index}): {e}")
