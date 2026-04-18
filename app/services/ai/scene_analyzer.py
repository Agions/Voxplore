"""
场景分析器 (Scene Analyzer)

分析视频内容，识别场景变化、关键帧和内容类型。
为 AI 解说和混剪提供素材分析支持。

集成 PySceneDetect 提供高精度的场景检测能力。

使用示例:
    from app.services.ai import SceneAnalyzer
    
    analyzer = SceneAnalyzer()
    scenes = analyzer.analyze('video.mp4')
    
    for scene in scenes:
        print(f"场景 {scene.index}: {scene.start}s - {scene.end}s")
        print(f"  类型: {scene.type.value}")
        print(f"  描述: {scene.description}")
"""

import logging
import subprocess
import re

from pathlib import Path
from typing import List, Optional
from ..video_tools.ffmpeg_tool import FFmpegTool


from .scene_models import SceneType, SceneInfo, AnalysisConfig

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
        return FFmpegTool.get_duration(video_path)
    
    def _detect_scenes_pyscenect(self, video_path: str) -> List[float]:
        """
        使用 PySceneDetect 检测场景变化
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            场景变化时间点列表（秒）
        """
        try:
            from scenedetect import open_video, SceneManager
            from scenedetect.detectors import ContentDetector, AdaptiveDetector, ThresholdDetector
            
            # 打开视频
            video = open_video(video_path)
            
            # 创建场景管理器
            scene_manager = SceneManager()
            
            # 根据配置选择检测器
            threshold = self.config.scene_threshold
            
            if self.config.detector_type == "adaptive":
                # 自适应检测器 - 适合有相机运动的视频
                # threshold: 较低值 = 更敏感，检测到更多场景
                # min_delta_hsv: 颜色变化阈值
                # min_scene_length: 最小场景长度（帧数）
                from scenedetect.detectors.adaptive_detector import AdaptiveDetector
                scene_manager.add_detector(
                    AdaptiveDetector(
                        adaptive_threshold=threshold * 50,  # PySceneDetect 使用不同范围
                        min_scene_len=max(int(self.config.min_scene_duration * 30), 15)  # 至少15帧
                    )
                )
            elif self.config.detector_type == "threshold":
                # 阈值检测器 - 适合检测渐变（淡入淡出）
                scene_manager.add_detector(
                    ThresholdDetector(threshold=int(threshold * 255))
                )
            else:
                # 内容检测器 - 默认，适合大多数视频
                scene_manager.add_detector(
                    ContentDetector(
                        threshold=threshold * 50,  # 缩放到 PySceneDetect 的范围
                        min_scene_len=max(int(self.config.min_scene_duration * 30), 15)
                    )
                )
            
            # 检测场景
            # show_progress=True 会显示进度条
            try:
                scene_manager.detect_scenes(video, show_progress=False)
            except Exception:
                # 如果视频无法读取，回退
                return [0.0]
            
            # 获取场景列表
            scene_list = scene_manager.get_scene_list()
            
            if not scene_list:
                return [0.0]
            
            # 提取时间点
            scene_times = [0.0]
            for scene in scene_list:
                # scene[0] 是开始帧，scene[1] 是结束帧
                start_time = scene[0].get_seconds()
                scene_times.append(start_time)
            
            return scene_times
            
        except ImportError as e:
            logger.warning(f"PySceneDetect 导入失败: {e}")
            self._pyscenect_available = False
            return self._detect_scene_changes(video_path)
        except Exception as e:
            logger.error(f"PySceneDetect 场景检测失败: {e}")
            # 回退到 FFmpeg 方法
            return self._detect_scene_changes(video_path)
    
    def _detect_scene_changes(self, video_path: str) -> List[float]:
        """
        使用 FFmpeg 检测场景变化时间点
        
        这是回退方法，当 PySceneDetect 不可用时使用
        """
        threshold = self.config.scene_threshold
        
        cmd = [
            'ffmpeg', '-i', video_path,
            '-filter:v', f"select='gt(scene,{threshold})',showinfo",
            '-f', 'null', '-'
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            # 解析输出，提取时间点
            scene_times = [0.0]  # 总是从 0 开始
            
            # 匹配 pts_time:X.XXX
            pattern = r'pts_time:(\d+\.?\d*)'
            matches = re.findall(pattern, result.stderr)
            
            for match in matches:
                time = float(match)
                # 过滤太近的场景变化
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
        
        # 确保 scene_times 是排序的
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
        """
        分析单个场景的特征
        
        提取亮度、运动程度、音频等信息
        """
        # 分析亮度
        scene.avg_brightness = self._get_avg_brightness(
            video_path, scene.start, scene.duration
        )
        
        # 分析运动程度
        scene.motion_level = self._get_motion_level(
            video_path, scene.start, scene.duration
        )
        
        # 分析音频
        if self.config.analyze_audio:
            scene.audio_level = self._get_audio_level(
                video_path, scene.start, scene.duration
            )
        
        # 计算适用性评分
        scene.suitability_score = self._calculate_suitability(scene)
        
        # 推断场景类型
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
            
            # 解析 YAVG (亮度平均值)
            match = re.search(r'YAVG:(\d+\.?\d*)', result.stderr)
            if match:
                return float(match.group(1)) / 255.0  # 归一化到 0-1
                
        except Exception:
            logger.debug("Operation failed")
        
        return 0.5  # 默认中等亮度
    
    def _get_motion_level(self, video_path: str, start: float, duration: float) -> float:
        """
        获取场景运动程度
        
        基于帧间差异估算运动强度
        """
        try:
            cmd = [
                'ffmpeg', '-ss', str(start), '-t', str(min(duration, 2)),
                '-i', video_path,
                '-filter:v', "select='gte(scene,0)',metadata=print",
                '-f', 'null', '-'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # 提取场景分数
            scores = re.findall(r'lavfi\.scene_score=(\d+\.?\d*)', result.stderr)
            if scores:
                avg_score = sum(float(s) for s in scores) / len(scores)
                return min(1.0, avg_score * 2)  # 归一化
                
        except Exception:
            logger.debug("Operation failed")
        
        return 0.3  # 默认中等运动
    
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
            
            # 解析 mean_volume
            match = re.search(r'mean_volume:\s*([-\d.]+)', result.stderr)
            if match:
                # 将 dB 转换为 0-1 范围（-60dB = 0, 0dB = 1）
                db = float(match.group(1))
                return max(0, min(1, (db + 60) / 60))
                
        except Exception:
            logger.debug("Operation failed")
        
        return 0.5
    
    def _calculate_suitability(self, scene: SceneInfo) -> float:
        """
        计算场景作为解说画面的适用性
        
        考虑因素：
        - 时长：太短不适合
        - 运动程度：适中最好
        - 亮度：不能太暗或太亮
        """
        score = 50.0  # 基础分
        
        # 时长评分（2-5秒最佳）
        if 2 <= scene.duration <= 5:
            score += 20
        elif scene.duration < 1:
            score -= 20
        elif scene.duration > 10:
            score -= 10
        
        # 运动程度（0.2-0.6 最佳）
        if 0.2 <= scene.motion_level <= 0.6:
            score += 15
        elif scene.motion_level > 0.8:
            score -= 10
        
        # 亮度（0.3-0.7 最佳）
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
            # 在场景中间提取一帧
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
        """
        获取最适合作为解说画面的场景
        
        Args:
            scenes: 场景列表
            count: 返回数量
            min_score: 最低适用性分数
            
        Returns:
            排序后的最佳场景列表
        """
        # 过滤低分场景
        filtered = [s for s in scenes if s.suitability_score >= min_score]
        
        # 按适用性排序
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
        """
        获取满足目标时长的场景组合
        
        贪心算法：优先选择高分场景，直到满足时长
        """
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
        
        # 按时间顺序排列
        selected.sort(key=lambda s: s.start)
        
        return selected
    
    def split_video_by_scenes(
        self,
        video_path: str,
        output_dir: str,
        scenes: Optional[List[SceneInfo]] = None,
    ) -> List[str]:
        """
        将视频按场景分割
        
        Args:
            video_path: 源视频路径
            output_dir: 输出目录
            scenes: 场景列表（如果为 None，将自动检测）
            
        Returns:
            分割后的视频文件路径列表
        """
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


# =========== 便捷函数 ===========

def analyze_video(video_path: str, config: Optional[AnalysisConfig] = None) -> List[SceneInfo]:
    """
    分析视频场景的便捷函数
    
    Args:
        video_path: 视频路径
        config: 分析配置
        
    Returns:
        场景列表
    """
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
    
    # 获取最佳场景
    best = analyzer.get_best_scenes(scenes, count=5)
    print("\n最佳场景 (前5个):")
    for scene in best:
        print(f"  场景 {scene.index}: {scene.suitability_score:.1f}分")


if __name__ == '__main__':
    demo_analyze()
