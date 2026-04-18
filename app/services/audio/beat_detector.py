#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
节拍检测器
基于 librosa 进行音频节拍/BPM/能量分析

功能:
- BPM 检测
- 节拍点提取（强拍/弱拍）
- 能量包络（onset detection）
- 音乐段落分析（intro/verse/chorus/outro）
- Beat-sync 剪辑点建议
"""

import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class BeatStrength(Enum):
    STRONG = "strong"    # 强拍（1拍）
    MEDIUM = "medium"    # 中拍（3拍，4/4拍中）
    WEAK = "weak"        # 弱拍


class MusicSection(Enum):
    INTRO = "intro"
    VERSE = "verse"
    CHORUS = "chorus"
    BRIDGE = "bridge"
    OUTRO = "outro"
    UNKNOWN = "unknown"


@dataclass
class BeatInfo:
    """单个节拍信息"""
    timestamp: float          # 秒
    strength: BeatStrength
    bar_position: int = 0     # 小节内位置 (1-4 for 4/4)


@dataclass
class BeatSyncCutpoint:
    """
    Beat-sync 剪辑点
    
    建议的剪辑时间点，基于节拍对齐
    """
    timestamp: float          # 剪辑时间点
    strength: BeatStrength   # 节拍强度
    beat_position: int       # 在小节中的位置
    suggested_cut_before: bool = True  # 是否建议在此点前剪辑
    energy: float = 0.0      # 该时刻的能量 (0-1)


@dataclass
class SectionInfo:
    """音乐段落"""
    start: float
    end: float
    section_type: MusicSection
    energy: float = 0.0       # 平均能量 0-1


@dataclass
class AudioAnalysisResult:
    """音频分析结果"""
    file_path: str
    duration: float
    sample_rate: int

    # BPM
    bpm: float = 0.0
    beat_interval: float = 0.0  # 节拍间隔（秒）

    # 节拍
    beats: List[BeatInfo] = field(default_factory=list)

    # 能量包络 onset
    onsets: List[float] = field(default_factory=list)  # onset 时间点

    # 音乐段落
    sections: List[SectionInfo] = field(default_factory=list)

    # RMS 能量曲线（采样）
    energy_curve: List[Tuple[float, float]] = field(default_factory=list)  # (time, energy)

    # 频谱特征
    spectral_centroid_mean: float = 0.0  # 平均频谱质心（亮度感）
    
    # Beat-sync 剪辑点
    beat_sync_cutpoints: List[BeatSyncCutpoint] = field(default_factory=list)


class BeatDetector:
    """
    节拍检测器

    用法:
        detector = BeatDetector()
        result = detector.analyze("music.mp3")

        print(f"BPM: {result.bpm}")
        for beat in result.beats:
            print(f"  {beat.timestamp:.3f}s [{beat.strength.value}]")
    """

    def __init__(self, hop_length: int = 512):
        self._hop_length = hop_length

    def analyze(self, audio_path: str,
                extract_sections: bool = True) -> AudioAnalysisResult:
        """
        分析音频

        Args:
            audio_path: 音频文件路径（mp3/wav/flac 等）
            extract_sections: 是否提取段落结构
        """
        try:
            import librosa
            import numpy as np
        except ImportError:
            raise ImportError(
                "需要安装 librosa: pip install librosa soundfile"
            )

        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        # 加载音频
        y, sr = librosa.load(str(path), sr=None)
        duration = librosa.get_duration(y=y, sr=sr)

        result = AudioAnalysisResult(
            file_path=str(path),
            duration=duration,
            sample_rate=sr,
        )

        # 1. BPM + 节拍检测
        tempo, beat_frames = librosa.beat.beat_track(
            y=y, sr=sr, hop_length=self._hop_length
        )
        # librosa 0.10+ 返回数组
        if hasattr(tempo, '__len__'):
            result.bpm = float(tempo[0]) if len(tempo) > 0 else 0.0
        else:
            result.bpm = float(tempo)

        beat_times = librosa.frames_to_time(
            beat_frames, sr=sr, hop_length=self._hop_length
        )

        # 标记强拍/弱拍（假设 4/4 拍）
        for i, t in enumerate(beat_times):
            bar_pos = (i % 4) + 1
            if bar_pos == 1:
                strength = BeatStrength.STRONG
            elif bar_pos == 3:
                strength = BeatStrength.MEDIUM
            else:
                strength = BeatStrength.WEAK

            result.beats.append(BeatInfo(
                timestamp=float(t),
                strength=strength,
                bar_position=bar_pos,
            ))

        # 2. Onset detection（音频能量突变点）
        onset_frames = librosa.onset.onset_detect(
            y=y, sr=sr, hop_length=self._hop_length
        )
        result.onsets = [
            float(t) for t in librosa.frames_to_time(
                onset_frames, sr=sr, hop_length=self._hop_length
            )
        ]

        # 3. RMS 能量曲线
        rms = librosa.feature.rms(y=y, hop_length=self._hop_length)[0]
        rms_times = librosa.frames_to_time(
            range(len(rms)), sr=sr, hop_length=self._hop_length
        )
        # 降采样到约每秒 4 个点
        step = max(1, len(rms) // int(duration * 4))
        result.energy_curve = [
            (float(rms_times[i]), float(rms[i]))
            for i in range(0, len(rms), step)
        ]

        # 4. 频谱质心（音色亮度）
        centroid = librosa.feature.spectral_centroid(
            y=y, sr=sr, hop_length=self._hop_length
        )[0]
        result.spectral_centroid_mean = float(np.mean(centroid))

        # 5. 段落分析
        if extract_sections:
            result.sections = self._detect_sections(y, sr, duration, rms)
        
        # 6. 计算节拍间隔
        if result.bpm > 0:
            result.beat_interval = 60.0 / result.bpm
        
        # 7. 生成 Beat-sync 剪辑点
        result.beat_sync_cutpoints = self.get_beat_sync_cutpoints(result)

        return result

    def _detect_sections(self, y, sr, duration, rms) -> List[SectionInfo]:
        """基于能量和频谱变化检测音乐段落"""
        import librosa
        import numpy as np

        # 使用 MFCC 的自相似矩阵做结构分割
        mfcc = librosa.feature.mfcc(
            y=y, sr=sr, n_mfcc=13, hop_length=self._hop_length
        )

        try:
            # 结构边界检测
            bound_frames = librosa.segment.agglomerative(
                mfcc, k=min(8, max(2, int(duration / 15)))
            )
            bound_times = librosa.frames_to_time(
                bound_frames, sr=sr, hop_length=self._hop_length
            )
        except Exception:
            # 降级：简单按时间等分
            n_sections = max(2, int(duration / 30))
            bound_times = [i * duration / n_sections
                          for i in range(1, n_sections)]

        # 构建段落
        sections = []
        all_boundaries = [0.0] + list(bound_times) + [duration]

        rms_times = librosa.frames_to_time(
            range(len(rms)), sr=sr, hop_length=self._hop_length
        )

        for i in range(len(all_boundaries) - 1):
            start = float(all_boundaries[i])
            end = float(all_boundaries[i + 1])

            # 计算段落平均能量
            mask = (rms_times >= start) & (rms_times < end)
            seg_energy = float(np.mean(rms[mask])) if np.any(mask) else 0.0

            # 推断段落类型
            position_ratio = start / duration if duration > 0 else 0
            if position_ratio < 0.1:
                section_type = MusicSection.INTRO
            elif position_ratio > 0.85:
                section_type = MusicSection.OUTRO
            elif seg_energy > np.mean(rms) * 1.2:
                section_type = MusicSection.CHORUS
            elif seg_energy < np.mean(rms) * 0.7:
                section_type = MusicSection.BRIDGE
            else:
                section_type = MusicSection.VERSE

            sections.append(SectionInfo(
                start=start,
                end=end,
                section_type=section_type,
                energy=seg_energy,
            ))

        return sections
    
    def get_beat_sync_cutpoints(
        self,
        result: AudioAnalysisResult,
        min_interval: float = 0.5,
        prefer_strong_beats: bool = True,
        energy_threshold: float = 0.3,
    ) -> List[BeatSyncCutpoint]:
        """
        获取 Beat-sync 剪辑点
        
        基于节拍和能量分析，生成建议的剪辑时间点。
        这些时间点适合进行视频切换，以配合音乐节奏。
        
        Args:
            result: 音频分析结果
            min_interval: 最小剪辑间隔（秒）
            prefer_strong_beats: 是否优先使用强拍
            energy_threshold: 能量阈值，低于此值的节拍会被过滤
            
        Returns:
            Beat-sync 剪辑点列表
        """
        cutpoints = []
        
        # 计算节拍间隔
        if result.beat_interval > 0:
            beat_interval = result.beat_interval
        elif result.bpm > 0:
            beat_interval = 60.0 / result.bpm
        else:
            beat_interval = 0.5  # 默认 120 BPM
        
        # 构建能量查找表
        energy_lookup = {}
        for time, energy in result.energy_curve:
            energy_lookup[int(time * 10) / 10] = energy  # 保留一位小数
        
        last_cut_time = -min_interval  # 确保第一个节拍可以用
        
        for beat in result.beats:
            # 检查最小间隔
            if beat.timestamp - last_cut_time < min_interval:
                continue
            
            # 获取该时刻的能量
            key = int(beat.timestamp * 10) / 10
            energy = energy_lookup.get(key, 0.5)
            
            # 过滤低能量点
            if energy < energy_threshold:
                continue
            
            # 强拍优先模式
            if prefer_strong_beats and beat.strength != BeatStrength.STRONG:
                # 检查是否是强拍附近（前后半拍内）
                nearby_strong = False
                for other in result.beats:
                    if other.strength == BeatStrength.STRONG:
                        diff = abs(other.timestamp - beat.timestamp)
                        if diff < beat_interval * 0.6:
                            nearby_strong = True
                            break
                if nearby_strong:
                    continue
            
            cutpoint = BeatSyncCutpoint(
                timestamp=beat.timestamp,
                strength=beat.strength,
                beat_position=beat.bar_position,
                suggested_cut_before=True,
                energy=energy,
            )
            cutpoints.append(cutpoint)
            last_cut_time = beat.timestamp
        
        return cutpoints
    
    def sync_analysis(self, result: AudioAnalysisResult) -> Dict[str, any]:
        """
        生成节拍同步分析报告
        
        用于混剪时的参考信息
        """
        report = {
            "bpm": result.bpm,
            "beat_interval_seconds": result.beat_interval,
            "total_beats": len(result.beats),
            "total_sections": len(result.sections),
            "sections_summary": [],
            "recommended_cutpoints": len(self.get_beat_sync_cutpoints(result)),
        }
        
        # 段落摘要
        for section in result.sections:
            report["sections_summary"].append({
                "type": section.section_type.value,
                "start": section.start,
                "end": section.end,
                "duration": section.end - section.start,
                "energy": section.energy,
            })
        
        # 能量分析
        if result.energy_curve:
            energies = [e for _, e in result.energy_curve]
            report["energy_stats"] = {
                "min": min(energies),
                "max": max(energies),
                "avg": sum(energies) / len(energies),
            }
        
        return report

    def extract_audio_from_video(self, video_path: str,
                                  output_path: Optional[str] = None) -> str:
        """从视频中提取音频"""
        if output_path is None:
            output_path = str(Path(video_path).with_suffix('.wav'))

        cmd = [
            'ffmpeg', '-y', '-i', video_path,
            '-vn', '-acodec', 'pcm_s16le',
            '-ar', '22050', '-ac', '1',
            output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
