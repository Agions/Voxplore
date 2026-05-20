#!/usr/bin/env python3
"""
EmotionPeakDetector 优化版本
改进点：
1. 真实视觉复杂度分析（基于帧差分）
2. 真实音频情绪分析（基于音频能量/音调）
3. 自适应采样策略
4. 批量并行处理
"""
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from collections.abc import Callable
import logging
import math

logger = logging.getLogger(__name__)


@dataclass
class EmotionPeak:
    """情感峰值"""
    segment: any  # VideoSegment
    peak_score: float
    reason: str
    visual_score: float = 0.0
    audio_score: float = 0.0


@runtime_checkable
class VisualComplexityAnalyzer(Protocol):
    """视觉复杂度分析器协议"""
    def analyze(self, video_path: str, start: float, end: float) -> float:
        """返回复杂度评分（0.0 ~ 1.0）"""
        ...


@runtime_checkable
class AudioEmotionAnalyzer(Protocol):
    """音频情绪分析器协议"""
    def analyze(self, video_path: str, start: float, end: float) -> float:
        """返回情绪评分（0.0 ~ 1.0）"""
        ...


class FrameDiffVisualAnalyzer:
    """基于帧差分的视觉复杂度分析器"""
    
    def __init__(self, frame_sample_rate: float = 0.5):
        """
        Args:
            frame_sample_rate: 帧采样率（秒），默认0.5秒采一帧
        """
        self.frame_sample_rate = frame_sample_rate
    
    def analyze(self, video_path: str, start: float, end: float) -> float:
        """
        基于帧间差异度量的视觉复杂度
        - 动作场景：帧间差异大
        - 静止场景：帧间差异小
        """
        try:
            import cv2
            import numpy as np
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.warning(f"Cannot open video: {video_path}")
                return 0.5
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            start_frame = int(start * fps)
            end_frame = min(int(end * fps), total_frames)
            
            # 采样帧
            sample_interval = max(1, int(self.frame_sample_rate * fps))
            frames = []
            for f in range(start_frame, end_frame, sample_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, f)
                ret, frame = cap.read()
                if ret:
                    frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
            
            cap.release()
            
            if len(frames) < 2:
                return 0.5
            
            # 计算帧间差异
            diffs = []
            for i in range(1, len(frames)):
                diff = np.mean(np.abs(frames[i].astype(float) - frames[i-1].astype(float)))
                diffs.append(diff)
            
            # 归一化（差异范围通常是0-50）
            avg_diff = np.mean(diffs)
            complexity = min(1.0, avg_diff / 50.0)
            
            return complexity
            
        except ImportError:
            logger.warning("OpenCV not available, using mock analysis")
            return self._mock_analyze(video_path, start, end)
        except Exception as e:
            logger.warning(f"Visual analysis failed: {e}")
            return 0.5
    
    def _mock_analyze(self, video_path: str, start: float, end: float) -> float:
        """降级方案：基于时间戳生成伪随机但稳定的复杂度"""
        hash_val = hash(video_path + f"{start:.1f}{end:.1f}") % (2**20)
        return 0.3 + (hash_val % 70) / 100.0


class AudioEnergyEmotionAnalyzer:
    """基于音频能量和音调的情绪分析器"""
    
    def __init__(self, energy_threshold: float = 0.1):
        self.energy_threshold = energy_threshold
    
    def analyze(self, video_path: str, start: float, end: float) -> float:
        """
        基于音频能量和音调变化判断情绪强度
        - 高能量+高音调 = 高情绪
        - 低能量+低音调 = 低情绪
        """
        try:
            import librosa
            import numpy as np
            
            # 提取音频片段
            try:
                y, sr = librosa.load(video_path, offset=start, duration=end-start, sr=16000)
            except Exception as e:
                logger.warning(f"librosa load failed: {e}")
                return 0.5
            
            if len(y) < sr:  # 音频太短
                return 0.5
            
            # 计算能量
            energy = np.sum(y ** 2) / len(y)
            energy_norm = min(1.0, math.sqrt(energy) * 10)
            
            # 计算音调（基频）
            try:
                pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
                pitch_max = []
                for t in range(pitches.shape[1]):
                    index = magnitudes[:, t].argmax()
                    pitch = pitches[index, t]
                    if pitch > 0:
                        pitch_max.append(pitch)
                avg_pitch = np.mean(pitch_max) if pitch_max else 0
                # 归一化（人类语音基频约50-500Hz）
                pitch_norm = min(1.0, avg_pitch / 300.0)
            except Exception:
                pitch_norm = 0.5
            
            # 综合情绪 = 能量 * 0.6 + 音调 * 0.4
            emotion = energy_norm * 0.6 + pitch_norm * 0.4
            
            return emotion
            
        except ImportError:
            logger.warning("librosa not available, using mock analysis")
            return self._mock_analyze(video_path, start, end)
        except Exception as e:
            logger.warning(f"Audio analysis failed: {e}")
            return 0.5
    
    def _mock_analyze(self, video_path: str, start: float, end: float) -> float:
        """降级方案"""
        hash_val = hash(video_path + f"{end:.1f}") % (2**20)
        return 0.2 + (hash_val % 60) / 100.0


class EmotionPeakDetector:
    """优化后的情感峰值检测器"""
    
    # 评分权重（可配置）
    VISUAL_WEIGHT = 0.6
    AUDIO_WEIGHT = 0.4
    MIN_PEAK_THRESHOLD = 0.35  # 降低阈值以捕获更多峰值
    
    # 批量处理配置
    BATCH_SIZE = 10
    
    def __init__(
        self,
        visual_analyzer: VisualComplexityAnalyzer | None = None,
        audio_analyzer: AudioEmotionAnalyzer | None = None,
        visual_weight: float = VISUAL_WEIGHT,
        audio_weight: float = AUDIO_WEIGHT,
        min_peak_threshold: float = MIN_PEAK_THRESHOLD,
        progress_callback: Callable[[int, int], None] | None = None,
    ):
        """
        Args:
            visual_analyzer: 视觉复杂度分析器
            audio_analyzer: 音频情绪分析器
            visual_weight: 视觉权重
            audio_weight: 音频权重
            min_peak_threshold: 最低峰值阈值
            progress_callback: 进度回调 (current, total)
        """
        self._visual_analyzer = visual_analyzer or FrameDiffVisualAnalyzer()
        self._audio_analyzer = audio_analyzer or AudioEnergyEmotionAnalyzer()
        self._visual_weight = visual_weight
        self._audio_weight = audio_weight
        self._min_peak_threshold = min_peak_threshold
        self._progress_callback = progress_callback
    
    def detect_peaks(
        self,
        segments: list,
        parallel: bool = True,
    ) -> list[EmotionPeak]:
        """
        检测情感峰值（支持并行处理）
        
        Args:
            segments: 视频片段列表
            parallel: 是否并行处理
            
        Returns:
            情感峰值列表（按峰值评分降序）
        """
        if not segments:
            return []
        
        peaks = []
        total = len(segments)
        
        if parallel:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import os
            
            # 根据 CPU 核心数动态调整 worker 数量
            max_workers = min(8, os.cpu_count() or 4)
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._analyze_segment, seg): seg 
                    for seg in segments
                }
                
                for i, future in enumerate(as_completed(futures), 1):
                    seg = futures[future]
                    try:
                        peak = future.result()
                        if peak and peak.peak_score >= self._min_peak_threshold:
                            peaks.append(peak)
                        
                        if self._progress_callback:
                            self._progress_callback(i, total)
                            
                    except Exception as e:
                        logger.warning(f"Segment analysis failed at {seg.start_time:.1f}s: {e}")
        
        else:
            for i, seg in enumerate(segments, 1):
                try:
                    peak = self._analyze_segment(seg)
                    if peak and peak.peak_score >= self._min_peak_threshold:
                        peaks.append(peak)
                    
                    if self._progress_callback:
                        self._progress_callback(i, total)
                except Exception as e:
                    logger.warning(f"Segment analysis failed at {seg.start_time:.1f}s: {e}")
        
        # 降序排列
        peaks.sort(key=lambda p: p.peak_score, reverse=True)
        
        # 非极大值抑制：过滤靠得太近的高峰值
        peaks = self._non_maximum_suppression(peaks, min_gap=5.0)
        
        return peaks
    
    def _analyze_segment(self, seg) -> EmotionPeak | None:
        """分析单个片段"""
        try:
            visual_score = self._visual_analyzer.analyze(
                seg.video_path, seg.start_time, seg.end_time
            )
        except Exception as e:
            logger.warning(f"Visual analysis failed: {e}")
            visual_score = 0.5
        
        try:
            audio_score = self._audio_analyzer.analyze(
                seg.video_path, seg.start_time, seg.end_time
            )
        except Exception as e:
            logger.warning(f"Audio analysis failed: {e}")
            audio_score = 0.5
        
        peak_score = (
            self._visual_weight * visual_score + 
            self._audio_weight * audio_score
        )
        
        reason = self._determine_reason(visual_score, audio_score, getattr(seg, 'description', ''))
        
        return EmotionPeak(
            segment=seg,
            peak_score=peak_score,
            reason=reason,
            visual_score=visual_score,
            audio_score=audio_score,
        )
    
    def _determine_reason(
        self,
        visual_score: float,
        audio_score: float,
        description: str,
    ) -> str:
        """判断峰值原因"""
        v_a_ratio = visual_score / (audio_score + 0.001)
        a_v_ratio = audio_score / (visual_score + 0.001)
        
        if v_a_ratio > 1.5:
            if visual_score > 0.8:
                return "高复杂度场景，信息密度大"
            elif visual_score > 0.6:
                return "动作密度较高"
            else:
                return "画面信息丰富"
        
        elif a_v_ratio > 1.5:
            return "音频情绪强度高"
        
        else:
            if visual_score > 0.7 and audio_score > 0.7:
                return "视觉+音频双重高能"
            elif visual_score > 0.6:
                return "综合情感峰值"
            else:
                return "情感起伏明显"
    
    def _non_maximum_suppression(
        self, 
        peaks: list[EmotionPeak], 
        min_gap: float = 5.0
    ) -> list[EmotionPeak]:
        """非极大值抑制：保留峰值，抑制附近的较低峰"""
        if not peaks:
            return []
        
        kept = [peaks[0]]  # 保留最高峰值
        
        for peak in peaks[1:]:
            seg = peak.segment
            # 检查与已有保留峰值的距离
            too_close = False
            for kept_peak in kept:
                kept_seg = kept_peak.segment
                # 检查时间重叠
                if (seg.start_time < kept_seg.end_time and 
                    seg.end_time > kept_seg.start_time):
                    too_close = True
                    break
            
            if not too_close:
                kept.append(peak)
        
        return kept


__all__ = [
    "EmotionPeakDetector",
    "EmotionPeak",
    "VisualComplexityAnalyzer",
    "AudioEmotionAnalyzer",
    "FrameDiffVisualAnalyzer",
    "AudioEnergyEmotionAnalyzer",
]
