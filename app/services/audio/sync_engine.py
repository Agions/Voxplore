#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
音画同步引擎
将视频剪辑点与音乐节拍对齐，实现"踩点"效果

同步策略:
- BEAT_SYNC: 每个节拍切换画面
- PHRASE_SYNC: 按乐句段落切换
- ENERGY_SYNC: 按音频能量匹配画面动态
- HYBRID: 混合策略（推荐）
"""

from typing import List, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .beat_detector import (
    AudioAnalysisResult, BeatStrength, MusicSection
)


class SyncStrategy(Enum):
    BEAT_SYNC = "beat_sync"       # 每个节拍切
    PHRASE_SYNC = "phrase_sync"   # 按乐句切
    ENERGY_SYNC = "energy_sync"  # 按能量切
    HYBRID = "hybrid"            # 混合（推荐）


class TransitionType(Enum):
    HARD_CUT = "hard_cut"         # 硬切
    CROSSFADE = "crossfade"       # 交叉淡化
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    ZOOM = "zoom"                 # 缩放转场
    WHIP = "whip"                 # 甩镜


@dataclass
class SyncPoint:
    """同步点"""
    timestamp: float              # 在音乐中的时间
    clip_index: int = -1          # 应该使用的视频片段索引
    transition: TransitionType = TransitionType.HARD_CUT
    speed_factor: float = 1.0     # 片段播放速度（<1慢放，>1快放）
    beat_strength: BeatStrength = BeatStrength.WEAK


@dataclass
class SyncPlan:
    """同步计划"""
    total_duration: float
    bpm: float
    strategy: SyncStrategy
    sync_points: List[SyncPoint] = field(default_factory=list)
    speed_curve: List[Tuple[float, float]] = field(default_factory=list)  # (time, speed)


class SyncEngine:
    """
    音画同步引擎

    用法:
        from app.services.audio.beat_detector import BeatDetector
        from app.services.audio.sync_engine import SyncEngine

        # 分析音频
        detector = BeatDetector()
        audio = detector.analyze("music.mp3")

        # 生成同步计划
        engine = SyncEngine()
        plan = engine.create_sync_plan(
            audio_analysis=audio,
            num_clips=20,
            strategy=SyncStrategy.HYBRID,
        )

        for sp in plan.sync_points:
            print(f"{sp.timestamp:.2f}s → clip[{sp.clip_index}] {sp.transition.value}")
    """

    def create_sync_plan(
        self,
        audio_analysis: AudioAnalysisResult,
        num_clips: int,
        strategy: SyncStrategy = SyncStrategy.HYBRID,
        min_clip_duration: float = 0.3,
        max_clip_duration: float = 5.0,
    ) -> SyncPlan:
        """
        创建音画同步计划

        Args:
            audio_analysis: 音频分析结果
            num_clips: 可用的视频片段数量
            strategy: 同步策略
            min_clip_duration: 最短片段时长
            max_clip_duration: 最长片段时长
        """
        plan = SyncPlan(
            total_duration=audio_analysis.duration,
            bpm=audio_analysis.bpm,
            strategy=strategy,
        )

        if strategy == SyncStrategy.BEAT_SYNC:
            self._beat_sync(plan, audio_analysis, num_clips,
                           min_clip_duration, max_clip_duration)
        elif strategy == SyncStrategy.PHRASE_SYNC:
            self._phrase_sync(plan, audio_analysis, num_clips)
        elif strategy == SyncStrategy.ENERGY_SYNC:
            self._energy_sync(plan, audio_analysis, num_clips,
                             min_clip_duration, max_clip_duration)
        else:  # HYBRID
            self._hybrid_sync(plan, audio_analysis, num_clips,
                             min_clip_duration, max_clip_duration)

        # 生成速度曲线
        plan.speed_curve = self._generate_speed_curve(audio_analysis)

        return plan

    def _beat_sync(self, plan: SyncPlan,
                   audio: AudioAnalysisResult,
                   num_clips: int,
                   min_dur: float, max_dur: float):
        """节拍同步：在每个（或每隔N个）节拍处切换"""
        beats = audio.beats
        if not beats:
            return

        # 根据片段数量决定每几个节拍切一次
        beats_per_cut = max(1, len(beats) // num_clips)

        clip_idx = 0
        for i, beat in enumerate(beats):
            if i % beats_per_cut == 0:
                # 检查与上一个切点的间隔
                if plan.sync_points:
                    gap = beat.timestamp - plan.sync_points[-1].timestamp
                    if gap < min_dur:
                        continue

                transition = self._beat_to_transition(beat.strength)

                plan.sync_points.append(SyncPoint(
                    timestamp=beat.timestamp,
                    clip_index=clip_idx % num_clips,
                    transition=transition,
                    beat_strength=beat.strength,
                ))
                clip_idx += 1

    def _phrase_sync(self, plan: SyncPlan,
                     audio: AudioAnalysisResult,
                     num_clips: int):
        """乐句同步：在段落边界切换"""
        if not audio.sections:
            # 降级到节拍同步
            return self._beat_sync(plan, audio, num_clips, 0.5, 10.0)

        clip_idx = 0
        for section in audio.sections:
            transition = TransitionType.CROSSFADE
            if section.section_type == MusicSection.CHORUS:
                transition = TransitionType.HARD_CUT
            elif section.section_type == MusicSection.BRIDGE:
                transition = TransitionType.FADE_IN

            plan.sync_points.append(SyncPoint(
                timestamp=section.start,
                clip_index=clip_idx % num_clips,
                transition=transition,
            ))
            clip_idx += 1

    def _energy_sync(self, plan: SyncPlan,
                     audio: AudioAnalysisResult,
                     num_clips: int,
                     min_dur: float, max_dur: float):
        """能量同步：在能量突变处切换"""
        onsets = audio.onsets
        if not onsets:
            return self._beat_sync(plan, audio, num_clips, min_dur, max_dur)

        # 按能量突变点分配切换
        step = max(1, len(onsets) // num_clips)
        clip_idx = 0

        for i in range(0, len(onsets), step):
            t = onsets[i]

            # 检查间隔
            if plan.sync_points:
                gap = t - plan.sync_points[-1].timestamp
                if gap < min_dur:
                    continue

            plan.sync_points.append(SyncPoint(
                timestamp=t,
                clip_index=clip_idx % num_clips,
                transition=TransitionType.HARD_CUT,
            ))
            clip_idx += 1

    def _hybrid_sync(self, plan: SyncPlan,
                     audio: AudioAnalysisResult,
                     num_clips: int,
                     min_dur: float, max_dur: float):
        """
        混合同步（推荐）

        规则：
        - Chorus 段：按节拍密集切换（踩点感）
        - Verse 段：按乐句切换（叙事感）
        - Intro/Outro：慢节奏
        - 强拍用硬切，弱拍用交叉淡化
        """
        sections = audio.sections
        beats = audio.beats

        if not sections:
            return self._beat_sync(plan, audio, num_clips, min_dur, max_dur)

        clip_idx = 0

        for section in sections:
            # 获取此段落内的节拍
            section_beats = [
                b for b in beats
                if section.start <= b.timestamp < section.end
            ]

            if section.section_type == MusicSection.CHORUS:
                # Chorus：每 1-2 个节拍切一次
                beats_per_cut = max(1, min(2, len(section_beats) // 4))
                for i, beat in enumerate(section_beats):
                    if i % beats_per_cut == 0:
                        if plan.sync_points:
                            gap = beat.timestamp - plan.sync_points[-1].timestamp
                            if gap < min_dur:
                                continue

                        plan.sync_points.append(SyncPoint(
                            timestamp=beat.timestamp,
                            clip_index=clip_idx % num_clips,
                            transition=self._beat_to_transition(beat.strength),
                            beat_strength=beat.strength,
                            speed_factor=1.0,
                        ))
                        clip_idx += 1

            elif section.section_type in (MusicSection.INTRO, MusicSection.OUTRO):
                # Intro/Outro：整个段落一个片段
                plan.sync_points.append(SyncPoint(
                    timestamp=section.start,
                    clip_index=clip_idx % num_clips,
                    transition=TransitionType.FADE_IN if section.section_type == MusicSection.INTRO else TransitionType.FADE_OUT,
                    speed_factor=0.8,  # 稍慢
                ))
                clip_idx += 1

            else:
                # Verse/Bridge：每 4 个节拍切一次
                beats_per_cut = max(2, min(4, len(section_beats) // 3))
                for i, beat in enumerate(section_beats):
                    if i % beats_per_cut == 0:
                        if plan.sync_points:
                            gap = beat.timestamp - plan.sync_points[-1].timestamp
                            if gap < min_dur:
                                continue

                        plan.sync_points.append(SyncPoint(
                            timestamp=beat.timestamp,
                            clip_index=clip_idx % num_clips,
                            transition=TransitionType.CROSSFADE,
                            beat_strength=beat.strength,
                        ))
                        clip_idx += 1

    def _beat_to_transition(self, strength: BeatStrength) -> TransitionType:
        """根据节拍强度选择转场类型"""
        if strength == BeatStrength.STRONG:
            return TransitionType.HARD_CUT
        elif strength == BeatStrength.MEDIUM:
            return TransitionType.ZOOM
        else:
            return TransitionType.CROSSFADE

    def _generate_speed_curve(
        self, audio: AudioAnalysisResult
    ) -> List[Tuple[float, float]]:
        """
        根据音频能量生成速度曲线

        高能量 → 快节奏（speed > 1.0）
        低能量 → 慢节奏（speed < 1.0）
        """
        if not audio.energy_curve:
            return [(0.0, 1.0), (audio.duration, 1.0)]

        # 计算平均能量
        energies = [e for _, e in audio.energy_curve]
        avg_energy = sum(energies) / len(energies) if energies else 0.5

        curve = []
        for t, energy in audio.energy_curve:
            if avg_energy > 0:
                ratio = energy / avg_energy
                # 映射到 0.7-1.5 的速度范围
                speed = max(0.7, min(1.5, 0.7 + ratio * 0.4))
            else:
                speed = 1.0
            curve.append((t, round(speed, 2)))

        return curve
