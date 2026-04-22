#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试情感峰值检测服务"""


from app.services.video.extraction.emotion_peak_detector import (
    EmotionPeak,
    EmotionPeakDetector,
)
from app.services.video.extraction.first_person_extractor import VideoSegment


class TestEmotionPeak:
    """测试 EmotionPeak 数据类"""

    def test_creation(self):
        """测试创建"""
        segment = VideoSegment(
            video_path="/test/video.mp4",
            start_time=10.0,
            end_time=30.0,
            confidence=0.85,
            description="测试片段"
        )
        
        peak = EmotionPeak(
            segment=segment,
            peak_score=0.95,
            reason="高复杂度场景，动作密集"
        )

        assert peak.segment == segment
        assert peak.peak_score == 0.95
        assert "高复杂度" in peak.reason or "动作" in peak.reason


class MockVisualComplexityAnalyzer:
    """模拟视觉复杂度分析器"""

    def __init__(self, complexity_scores: dict[str, float]):
        # complexity_scores: video_path -> complexity score (0.0 ~ 1.0)
        self._scores = complexity_scores

    def analyze(self, video_path: str, start: float, end: float) -> float:
        if video_path in self._scores:
            return self._scores[video_path]
        return 0.5  # 默认中等复杂度


class MockAudioEmotionAnalyzer:
    """模拟音频情绪分析器"""

    def __init__(self, emotion_scores: dict[str, float]):
        # emotion_scores: video_path -> emotion score (0.0 ~ 1.0)
        self._scores = emotion_scores

    def analyze(self, video_path: str, start: float, end: float) -> float:
        if video_path in self._scores:
            return self._scores[video_path]
        return 0.5  # 默认中等情绪


class TestEmotionPeakDetector:
    """测试 EmotionPeakDetector"""

    def test_init(self):
        """测试初始化"""
        detector = EmotionPeakDetector()
        assert detector is not None

    def test_detect_peaks_3segments_sorted_by_score(self):
        """测试：3个片段 → 正确按峰值评分排序"""
        segments = [
            VideoSegment("/test/v1.mp4", 0, 15, 0.8, "平淡场景"),
            VideoSegment("/test/v2.mp4", 15, 35, 0.9, "高潮场景"),
            VideoSegment("/test/v3.mp4", 35, 50, 0.7, "结尾场景"),
        ]

        # 设置不同复杂度
        complexity_scores = {
            "/test/v1.mp4": 0.3,   # 低复杂度
            "/test/v2.mp4": 0.95,  # 高复杂度
            "/test/v3.mp4": 0.5,   # 中复杂度
        }

        detector = EmotionPeakDetector()
        detector._visual_analyzer = MockVisualComplexityAnalyzer(complexity_scores)
        detector._audio_analyzer = MockAudioEmotionAnalyzer({})

        peaks = detector.detect_peaks(segments)

        assert len(peaks) <= 3 and len(peaks) >= 1
        # 验证按 peak_score 降序排列
        scores = [p.peak_score for p in peaks]
        assert scores == sorted(scores, reverse=True), \
            f"峰值评分应降序排列: {scores}"
        # 最高分应该是 v2（复杂度 0.95）
        assert peaks[0].segment.video_path == "/test/v2.mp4"

    def test_detect_peaks_no_obvious_peaks_returns_empty_or_low(self):
        """测试：无明显峰值 → 返回空或低分"""
        segments = [
            VideoSegment("/test/v1.mp4", 0, 15, 0.6, "平淡"),
            VideoSegment("/test/v2.mp4", 15, 35, 0.55, "普通"),
            VideoSegment("/test/v3.mp4", 35, 50, 0.5, "无聊"),
        ]

        # 所有片段都是低复杂度
        complexity_scores = {
            "/test/v1.mp4": 0.1,
            "/test/v2.mp4": 0.15,
            "/test/v3.mp4": 0.1,
        }

        detector = EmotionPeakDetector()
        detector._visual_analyzer = MockVisualComplexityAnalyzer(complexity_scores)
        detector._audio_analyzer = MockAudioEmotionAnalyzer({})

        peaks = detector.detect_peaks(segments)

        # 应该有结果但分数较低，或者空列表
        assert isinstance(peaks, list)
        if len(peaks) > 0:
            # 所有分数应该低于阈值或整体偏低
            for peak in peaks:
                assert peak.peak_score <= 0.7

    def test_detect_peaks_empty_input(self):
        """测试空输入"""
        detector = EmotionPeakDetector()
        peaks = detector.detect_peaks([])
        assert peaks == []

    def test_detect_peaks_reason_variety(self):
        """测试峰值原因的多样性"""
        segments = [
            VideoSegment("/test/v1.mp4", 0, 20, 0.9, "动作场景"),
            VideoSegment("/test/v2.mp4", 20, 40, 0.85, "情绪场景"),
            VideoSegment("/test/v3.mp4", 40, 55, 0.8, "复杂场景"),
        ]

        complexity_scores = {
            "/test/v1.mp4": 0.9,   # 动作密度高
            "/test/v2.mp4": 0.85,  # 情绪强
            "/test/v3.mp4": 0.88,  # 信息密度高
        }

        detector = EmotionPeakDetector()
        detector._visual_analyzer = MockVisualComplexityAnalyzer(complexity_scores)
        detector._audio_analyzer = MockAudioEmotionAnalyzer(complexity_scores)

        peaks = detector.detect_peaks(segments)

        reasons = [p.reason for p in peaks]
        # 应该有不同的峰值原因（高复杂度/强情绪/动作密度）
        assert any("复杂度" in r or "信息密度" in r for r in reasons) or \
               any("情绪" in r or "音频" in r for r in reasons) or \
               any("动作" in r for r in reasons)

    def test_detect_peaks_with_audio_emotion(self):
        """测试音频情绪检测影响峰值评分"""
        segments = [
            VideoSegment("/test/v1.mp4", 0, 20, 0.8, "安静"),
        ]

        complexity_scores = {"/test/v1.mp4": 0.5}
        emotion_scores = {"/test/v1.mp4": 0.95}  # 高情绪

        detector = EmotionPeakDetector()
        detector._visual_analyzer = MockVisualComplexityAnalyzer(complexity_scores)
        detector._audio_analyzer = MockAudioEmotionAnalyzer(emotion_scores)

        peaks = detector.detect_peaks(segments)

        # 有音频情绪加成，peak_score 应该更高
        assert len(peaks) == 1
        # peak_score 应该 > 0.5（基础分 + 情绪加成）
        assert peaks[0].peak_score > 0.5


class TestEmotionPeakScoring:
    """测试情感峰值评分机制"""

    def test_high_visual_complexity_increases_score(self):
        """测试：高视觉复杂度 → 高峰值评分"""
        segment = VideoSegment("/test/v.mp4", 0, 20, 0.8, "动作密集")

        detector = EmotionPeakDetector()
        detector._visual_analyzer = MockVisualComplexityAnalyzer({"/test/v.mp4": 0.95})
        detector._audio_analyzer = MockAudioEmotionAnalyzer({"/test/v.mp4": 0.1})

        peaks = detector.detect_peaks([segment])

        assert len(peaks) == 1
        # 高视觉复杂度应该推高评分
        assert peaks[0].peak_score > 0.6

    def test_combined_score(self):
        """测试：视觉+音频综合评分"""
        segment = VideoSegment("/test/v.mp4", 0, 20, 0.9, "综合场景")

        detector = EmotionPeakDetector()
        detector._visual_analyzer = MockVisualComplexityAnalyzer({"/test/v.mp4": 0.8})
        detector._audio_analyzer = MockAudioEmotionAnalyzer({"/test/v.mp4": 0.9})

        peaks = detector.detect_peaks([segment])

        assert len(peaks) == 1
        # 综合评分应该高于单一维度
        assert peaks[0].peak_score >= 0.7