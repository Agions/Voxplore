#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试智能视频分组服务"""

import numpy as np

from app.services.video.grouping.smart_grouper import (
    SmartGrouper,
    VideoGroup,
)


class TestVideoGroup:
    """测试 VideoGroup 数据类"""

    def test_creation(self):
        """测试创建"""
        group = VideoGroup(
            group_id="group_001",
            video_paths=["/path/video1.mp4", "/path/video2.mp4"],
            confidence=0.95,
            reason="视觉相似度极高"
        )

        assert group.group_id == "group_001"
        assert len(group.video_paths) == 2
        assert group.confidence == 0.95
        assert group.reason == "视觉相似度极高"

    def test_confidence_range(self):
        """测试置信度范围"""
        group = VideoGroup(
            group_id="test",
            video_paths=[],
            confidence=0.0,
            reason=""
        )
        assert group.confidence == 0.0

        group.confidence = 1.0
        assert group.confidence == 1.0


class MockVisionEmbedder:
    """模拟视觉 embedding 提取器"""

    def __init__(self, embeddings: dict[str, list[float]]):
        self._embeddings = embeddings

    def extract(self, video_path: str, num_frames: int = 8) -> list[float]:
        if video_path not in self._embeddings:
            # 返回随机 embedding 用于不相似视频
            return list(np.random.randn(128))
        return self._embeddings[video_path]


class MockAudioEmbedder:
    """模拟音频 embedding 提取器"""

    def __init__(self, embeddings: dict[str, list[float]]):
        self._embeddings = embeddings

    def extract(self, video_path: str) -> list[float]:
        if video_path not in self._embeddings:
            return list(np.random.randn(64))
        return self._embeddings[video_path]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算余弦相似度"""
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


class TestSmartGrouper:
    """测试 SmartGrouper"""

    def test_init(self):
        """测试初始化"""
        grouper = SmartGrouper()
        assert grouper is not None

    def test_group_videos_same_scene_high_confidence(self):
        """测试：2个视频同一场景 → 高置信度同组"""
        video_paths = ["/test/scene1_video1.mp4", "/test/scene1_video2.mp4"]
        
        # 相同场景的视觉 embedding（高度相似）
        same_embedding = [0.1] * 128
        vision_embeddings = {vp: same_embedding for vp in video_paths}
        audio_embeddings = {vp: [0.2] * 64 for vp in video_paths}

        grouper = SmartGrouper()
        grouper._vision_embedder = MockVisionEmbedder(vision_embeddings)
        grouper._audio_embedder = MockAudioEmbedder(audio_embeddings)

        groups = grouper.group_videos(video_paths)

        assert len(groups) == 1
        assert len(groups[0].video_paths) == 2
        assert groups[0].confidence > 0.8
        # reason 可以是 "视觉相似", "声纹匹配", "视觉+声纹综合" 等
        assert any(k in groups[0].reason for k in ["视觉", "声纹", "相似", "综合"])

    def test_group_videos_different_scene_low_confidence(self):
        """测试：2个视频不同场景 → 低置信度不同组"""
        video_paths = ["/test/scene1.mp4", "/test/scene2.mp4"]
        
        # 不同场景的视觉 embedding（随机，不相似）
        vision_embeddings = {vp: list(np.random.randn(128)) for vp in video_paths}
        audio_embeddings = {vp: [np.random.rand()] * 64 for vp in video_paths}

        grouper = SmartGrouper()
        grouper._vision_embedder = MockVisionEmbedder(vision_embeddings)
        grouper._audio_embedder = MockAudioEmbedder(audio_embeddings)

        groups = grouper.group_videos(video_paths)

        # 不同场景应该分成不同组
        assert len(groups) == 2
        for group in groups:
            assert len(group.video_paths) == 1

    def test_group_videos_mixed_3videos_2groups(self):
        """测试：3个视频混合 → 正确分2组"""
        # video_a, video_b 同一场景；video_c 不同场景
        video_paths = ["/test/video_a.mp4", "/test/video_b.mp4", "/test/video_c.mp4"]
        
        # video_a 和 video_b 相似，video_c 不相似
        ab_embedding = [0.5] * 128
        c_embedding = [-0.5] * 128
        
        vision_embeddings = {
            "/test/video_a.mp4": ab_embedding,
            "/test/video_b.mp4": ab_embedding,
            "/test/video_c.mp4": c_embedding,
        }
        audio_embeddings = {vp: [0.3] * 64 for vp in video_paths}

        grouper = SmartGrouper()
        grouper._vision_embedder = MockVisionEmbedder(vision_embeddings)
        grouper._audio_embedder = MockAudioEmbedder(audio_embeddings)

        groups = grouper.group_videos(video_paths)

        assert len(groups) == 2
        
        # 找到包含 video_a 和 video_b 的组
        ab_group = None
        c_group = None
        for g in groups:
            if "/test/video_c.mp4" in g.video_paths:
                c_group = g
            else:
                ab_group = g

        assert ab_group is not None
        assert c_group is not None
        assert len(ab_group.video_paths) == 2
        assert len(c_group.video_paths) == 1

    def test_group_videos_empty(self):
        """测试空列表"""
        grouper = SmartGrouper()
        groups = grouper.group_videos([])
        assert groups == []

    def test_group_videos_single(self):
        """测试单个视频"""
        grouper = SmartGrouper()
        groups = grouper.group_videos(["/test/solo.mp4"])
        assert len(groups) == 1
        assert groups[0].video_paths == ["/test/solo.mp4"]

    def test_group_id_unique(self):
        """测试 group_id 唯一性"""
        grouper = SmartGrouper()
        groups = grouper.group_videos(["/test/v1.mp4", "/test/v2.mp4", "/test/v3.mp4"])
        group_ids = [g.group_id for g in groups]
        assert len(group_ids) == len(set(group_ids)), "group_id 应该唯一"