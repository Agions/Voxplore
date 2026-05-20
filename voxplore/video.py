#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Voxplore 视频处理服务
包含视频分析、分割、帧提取等核心功能
"""
import os
import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Callable
import numpy as np

logger = logging.getLogger(__name__)


class VideoAnalyzer:
    """
    视频分析器
    负责获取视频信息、提取帧、检测场景
    """
    
    @staticmethod
    def get_video_info(video_path: str) -> dict:
        """
        获取视频信息
        
        Returns:
            dict: {
                "duration": float,  # 秒
                "fps": float,
                "width": int,
                "height": int,
                "codec": str,
                "size": int  # bytes
            }
        """
        try:
            import cv2
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video: {video_path}")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            cap.release()
            
            duration = frame_count / fps if fps > 0 else 0
            size = os.path.getsize(video_path)
            
            # 尝试用 ffprobe 获取更准确的信息
            try:
                probe_result = VideoAnalyzer._probe_video(video_path)
                if probe_result:
                    duration = probe_result.get("duration", duration)
            except Exception:
                pass
            
            return {
                "duration": duration,
                "fps": fps,
                "width": width,
                "height": height,
                "codec": "h264",  # 简化
                "size": size,
            }
            
        except ImportError:
            logger.warning("OpenCV not available, using ffprobe fallback")
            return VideoAnalyzer._probe_video(video_path) or {
                "duration": 60.0,
                "fps": 30.0,
                "width": 1920,
                "height": 1080,
                "codec": "unknown",
                "size": 0,
            }
    
    @staticmethod
    def _probe_video(video_path: str) -> Optional[dict]:
        """使用 ffprobe 获取视频信息"""
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-print_format", "json",
                    "-show_format", "-show_streams",
                    video_path
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                # 获取视频流信息
                video_stream = next(
                    (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
                    {}
                )
                
                format_info = data.get("format", {})
                
                return {
                    "duration": float(format_info.get("duration", 0)),
                    "fps": eval(video_stream.get("r_frame_rate", "30/1")) if "/" in video_stream.get("r_frame_rate", "30/1") else float(video_stream.get("r_frame_rate", "30")),
                    "width": int(video_stream.get("width", 0)),
                    "height": int(video_stream.get("height", 0)),
                    "codec": video_stream.get("codec_name", "unknown"),
                    "size": int(format_info.get("size", 0)),
                }
                
        except Exception as e:
            logger.warning(f"ffprobe failed: {e}")
        
        return None
    
    @staticmethod
    def extract_frame(video_path: str, timestamp: float) -> Optional[np.ndarray]:
        """
        提取指定时间戳的帧
        
        Args:
            video_path: 视频路径
            timestamp: 时间戳（秒）
            
        Returns:
            numpy.ndarray: BGR 格式图像，或 None
        """
        try:
            import cv2
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None
            
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            ret, frame = cap.read()
            cap.release()
            
            return frame if ret else None
            
        except ImportError:
            logger.error("OpenCV is required for frame extraction")
            return None
    
    @staticmethod
    def extract_frames_batch(
        video_path: str,
        timestamps: List[float],
        progress_callback: Optional[Callable] = None
    ) -> List[Tuple[float, np.ndarray]]:
        """
        批量提取帧
        
        Returns:
            List[(timestamp, frame)] 只返回成功提取的帧
        """
        results = []
        total = len(timestamps)
        
        try:
            import cv2
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return results
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            for i, ts in enumerate(timestamps):
                try:
                    frame_pos = int(ts * fps)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
                    ret, frame = cap.read()
                    
                    if ret:
                        results.append((ts, frame))
                    
                except Exception as e:
                    logger.warning(f"Failed to extract frame at {ts}s: {e}")
                
                if progress_callback and (i + 1) % 10 == 0:
                    progress_callback(i + 1, total)
            
            cap.release()
            
        except ImportError:
            logger.error("OpenCV is required for frame extraction")
        
        return results
    
    @staticmethod
    def detect_scenes(
        video_path: str,
        threshold: float = 30.0,
        min_scene_duration: float = 1.0
    ) -> List[Tuple[float, float]]:
        """
        检测场景变化
        
        Args:
            video_path: 视频路径
            threshold: 场景变化阈值（帧差异）
            min_scene_duration: 最小场景时长（秒）
            
        Returns:
            List[(start_time, end_time)]
        """
        try:
            import cv2
            import numpy as np
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return []
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            scenes = []
            prev_frame = None
            scene_start = 0
            frame_idx = 0
            
            # 每秒采样一次检测场景变化
            sample_interval = max(1, int(fps))
            
            while frame_idx < total_frames:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if prev_frame is not None:
                    diff = np.mean(np.abs(gray.astype(float) - prev_frame.astype(float)))
                    
                    # 检测到场景变化
                    if diff > threshold:
                        scene_end = frame_idx / fps
                        if scene_end - scene_start >= min_scene_duration:
                            scenes.append((scene_start, scene_end))
                        scene_start = scene_end
                
                prev_frame = gray
                frame_idx += sample_interval
            
            # 添加最后一个场景
            final_time = total_frames / fps
            if final_time - scene_start >= min_scene_duration:
                scenes.append((scene_start, final_time))
            
            cap.release()
            
            return scenes
            
        except ImportError:
            logger.error("OpenCV is required for scene detection")
            return []
    
    @staticmethod
    def extract_audio(video_path: str, output_path: str = None) -> Optional[str]:
        """
        提取音频
        
        Args:
            video_path: 视频路径
            output_path: 输出路径（可选）
            
        Returns:
            音频文件路径
        """
        if output_path is None:
            output_path = video_path.rsplit('.', 1)[0] + '.wav'
        
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-vn", "-acodec", "pcm_s16le",
                    "-ar", "16000", "-ac", "1",
                    output_path
                ],
                capture_output=True,
                timeout=300,
                check=True
            )
            return output_path
            
        except subprocess.TimeoutExpired:
            logger.error("Audio extraction timed out")
            return None
        except subprocess.CalledProcessError as e:
            logger.error(f"Audio extraction failed: {e}")
            return None


class VideoProcessor:
    """
    视频处理器
    负责视频的分割、合并等操作
    """
    
    @staticmethod
    def cut_video(
        input_path: str,
        output_path: str,
        start_time: float,
        end_time: float,
        quality: int = 23
    ) -> bool:
        """
        剪切视频片段
        
        Args:
            input_path: 输入视频
            output_path: 输出视频
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            quality: 质量（0-51，越低越好）
            
        Returns:
            是否成功
        """
        try:
            duration = end_time - start_time
            
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-ss", str(start_time),
                    "-i", input_path,
                    "-t", str(duration),
                    "-c:v", "libx264", "-crf", str(quality),
                    "-c:a", "aac",
                    "-strict", "experimental",
                    output_path
                ],
                capture_output=True,
                timeout=max(60, int(duration * 2)),
                check=True
            )
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Video cutting timed out")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Video cutting failed: {e}")
            return False
    
    @staticmethod
    def concatenate_videos(
        input_paths: List[str],
        output_path: str,
        temp_dir: str = None
    ) -> bool:
        """
        合并多个视频
        
        Args:
            input_paths: 输入视频列表
            output_path: 输出视频
            temp_dir: 临时目录（用于存储文件列表）
            
        Returns:
            是否成功
        """
        if not input_paths:
            return False
        
        if len(input_paths) == 1:
            # 只有一个视频，直接复制
            try:
                import shutil
                shutil.copy(input_paths[0], output_path)
                return True
            except Exception as e:
                logger.error(f"File copy failed: {e}")
                return False
        
        # 创建临时文件列表
        if temp_dir is None:
            temp_dir = os.path.dirname(output_path) or "."
        
        list_file = os.path.join(temp_dir, "concat_list.txt")
        
        try:
            with open(list_file, 'w') as f:
                for path in input_paths:
                    f.write(f"file '{path}'\n")
            
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "concat", "-safe", "0",
                    "-i", list_file,
                    "-c", "copy",
                    output_path
                ],
                capture_output=True,
                timeout=300,
                check=True
            )
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Video concatenation timed out")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Video concatenation failed: {e}")
            return False
        finally:
            if os.path.exists(list_file):
                os.remove(list_file)
    
    @staticmethod
    def add_audio(
        video_path: str,
        audio_path: str,
        output_path: str,
        audio_volume: float = 1.0,
        video_volume: float = 0.0
    ) -> bool:
        """
        添加音频到视频
        
        Args:
            video_path: 视频路径
            audio_path: 音频路径
            output_path: 输出路径
            audio_volume: 音频音量（0.0-1.0）
            video_volume: 视频原音音量（0.0-1.0）
            
        Returns:
            是否成功
        """
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-i", audio_path,
                    "-filter_complex",
                    f"[0:a]volume={video_volume}[a0];[1:a]volume={audio_volume}[a1];[a0][a1]amix=inputs=2:duration=longest[aout]",
                    "-map", "0:v",
                    "-map", "[aout]",
                    "-c:v", "copy",
                    output_path
                ],
                capture_output=True,
                timeout=300,
                check=True
            )
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Audio mixing timed out")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Audio mixing failed: {e}")
            return False


__all__ = [
    "VideoAnalyzer",
    "VideoProcessor",
]
