#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SmartGrouper - 智能视频分组服务

功能：
1. Qwen2.5-VL 提取每帧视觉 embedding（采样关键帧）
2. 声纹识别提取音频 embedding（如果有音频）
3. 混合相似度计算（视觉权重 0.7 + 音频权重 0.3）
4. 层次聚类分组
5. 返回分组列表（含置信度）

接口预留：
- 视觉 embedding: VisionEmbedder 协议（未来替换为真实 Qwen2.5-VL）
- 音频 embedding: AudioEmbedder 协议（未来替换为真实声纹识别）
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from enum import Enum
import numpy as np
from collections import defaultdict


class GroupingReason(Enum):
    """分组原因枚举"""
    VISUAL_SIMILAR = "视觉相似"
    AUDIO_SIMILAR = "声纹匹配"
    VISUAL_AUDIO_COMBINED = "视觉+声纹综合"


@dataclass
class VideoGroup:
    """视频分组"""
    group_id: str
    video_paths: list[str]
    confidence: float  # 0.0 ~ 1.0
    reason: str  # 分组原因


@runtime_checkable
class VisionEmbedder(Protocol):
    """视觉 embedding 提取器协议
    
    实现此协议以接入真实 Qwen2.5-VL 模型
    """
    
    def extract(self, video_path: str, num_frames: int = 8) -> list[float]:
        """提取视频视觉 embedding
        
        Args:
            video_path: 视频路径
            num_frames: 采样帧数
            
        Returns:
            embedding 向量（固定维度）
        """
        ...


@runtime_checkable
class AudioEmbedder(Protocol):
    """音频 embedding 提取器协议
    
    实现此协议以接入真实声纹识别模型
    """
    
    def extract(self, video_path: str) -> list[float]:
        """提取音频 embedding
        
        Args:
            video_path: 视频路径
            
        Returns:
            embedding 向量（固定维度）
        """
        ...


class MockVisionEmbedder:
    """模拟视觉 embedding 提取器（用于测试和开发）"""
    
    def __init__(self, seed: int = 42):
        self._rng = np.random.RandomState(seed)
    
    def extract(self, video_path: str, num_frames: int = 8) -> list[float]:
        # 使用路径哈希生成确定性但唯一的 embedding
        hash_val = hash(video_path) % (2**31)
        rng = np.random.RandomState(hash_val)
        return list(rng.randn(128))


class MockAudioEmbedder:
    """模拟音频 embedding 提取器（用于测试和开发）"""
    
    def __init__(self, seed: int = 42):
        self._rng = np.random.RandomState(seed)
    
    def extract(self, video_path: str) -> list[float]:
        hash_val = hash(video_path) % (2**31)
        rng = np.random.RandomState(hash_val)
        return list(rng.randn(64))


class SmartGrouper:
    """多视频智能分组服务"""
    
    # 相似度阈值：超过此值则视为同一组
    SIMILARITY_THRESHOLD = 0.75
    
    # 混合权重
    VISION_WEIGHT = 0.7
    AUDIO_WEIGHT = 0.3
    
    def __init__(
        self,
        vision_embedder: VisionEmbedder | None = None,
        audio_embedder: AudioEmbedder | None = None,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
        vision_weight: float = VISION_WEIGHT,
        audio_weight: float = AUDIO_WEIGHT,
    ):
        """初始化分组器
        
        Args:
            vision_embedder: 视觉 embedding 提取器（默认使用 Mock）
            audio_embedder: 音频 embedding 提取器（默认使用 Mock）
            similarity_threshold: 相似度阈值
            vision_weight: 视觉权重
            audio_weight: 音频权重
        """
        self._vision_embedder = vision_embedder or MockVisionEmbedder()
        self._audio_embedder = audio_embedder or MockAudioEmbedder()
        self._similarity_threshold = similarity_threshold
        self._vision_weight = vision_weight
        self._audio_weight = audio_weight
        self._group_counter = 0
    
    def group_videos(self, video_paths: list[str]) -> list[VideoGroup]:
        """智能分组
        
        Args:
            video_paths: 视频路径列表
            
        Returns:
            分组列表
        """
        if not video_paths:
            return []
        
        if len(video_paths) == 1:
            return [self._make_group([video_paths[0]], 1.0, GroupingReason.VISUAL_SIMILAR)]
        
        # 1. 提取 embedding
        vision_embeddings = {}
        audio_embeddings = {}
        
        for vp in video_paths:
            try:
                vision_embeddings[vp] = self._vision_embedder.extract(vp)
            except Exception:
                vision_embeddings[vp] = list(np.random.randn(128))
            
            try:
                audio_embeddings[vp] = self._audio_embedder.extract(vp)
            except Exception:
                audio_embeddings[vp] = list(np.random.randn(64))
        
        # 2. 计算两两相似度矩阵
        n = len(video_paths)
        similarity_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i + 1, n):
                sim = self._compute_similarity(
                    vision_embeddings[video_paths[i]],
                    vision_embeddings[video_paths[j]],
                    audio_embeddings[video_paths[i]],
                    audio_embeddings[video_paths[j]],
                )
                similarity_matrix[i, j] = sim
                similarity_matrix[j, i] = sim
        
        # 3. 层次聚类
        clusters = self._hierarchical_clustering(similarity_matrix, video_paths)
        
        # 4. 构建分组
        groups = []
        for cluster in clusters:
            if len(cluster) == 0:
                continue
            if len(cluster) == 1:
                # 单视频单独成一组，置信度较低
                groups.append(self._make_group(
                    [cluster[0]],
                    0.5,
                    GroupingReason.VISUAL_SIMILAR
                ))
            else:
                # 计算组内平均相似度作为置信度
                total_sim = 0.0
                count = 0
                indices = [video_paths.index(vp) for vp in cluster]
                for i in range(len(indices)):
                    for j in range(i + 1, len(indices)):
                        total_sim += similarity_matrix[indices[i], indices[j]]
                        count += 1
                
                avg_sim = total_sim / count if count > 0 else 0.5
                confidence = min(1.0, avg_sim)
                
                # 判断原因
                reason = self._determine_reason(
                    cluster, video_paths, vision_embeddings, audio_embeddings
                )
                
                groups.append(self._make_group(cluster, confidence, reason))
        
        return groups
    
    def _compute_similarity(
        self,
        v_emb1: list[float],
        v_emb2: list[float],
        a_emb1: list[float],
        a_emb2: list[float],
    ) -> float:
        """计算混合相似度"""
        v_sim = self._cosine_similarity(v_emb1, v_emb2)
        a_sim = self._cosine_similarity(a_emb1, a_emb2)
        
        # 归一化到 [0, 1]（余弦相似度本来就是 [-1, 1]）
        # 负值意味着不相似，但层次聚类中我们用阈值判断
        v_sim_norm = (v_sim + 1) / 2
        a_sim_norm = (a_sim + 1) / 2
        
        return self._vision_weight * v_sim_norm + self._audio_weight * a_sim_norm
    
    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """计算余弦相似度"""
        a = np.array(a)
        b = np.array(b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
    
    def _hierarchical_clustering(
        self,
        similarity_matrix: np.ndarray,
        video_paths: list[str],
    ) -> list[list[str]]:
        """层次聚类
        
        使用自底向上聚合聚类
        
        Returns:
            聚类结果列表，每个元素是一组视频路径
        """
        n = len(video_paths)
        if n == 0:
            return []
        if n == 1:
            return [[video_paths[0]]]
        
        # 初始化：每个视频一个簇
        clusters = [[vp] for vp in video_paths]
        
        while len(clusters) > 1:
            # 找到最相似的两个簇
            max_sim = -1.0
            merge_idx = (-1, -1)
            
            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    # 计算两个簇之间的平均相似度
                    sims = []
                    for vp1 in clusters[i]:
                        for vp2 in clusters[j]:
                            idx1 = video_paths.index(vp1)
                            idx2 = video_paths.index(vp2)
                            sims.append(similarity_matrix[idx1, idx2])
                    
                    avg_sim = np.mean(sims) if sims else 0.0
                    
                    if avg_sim > max_sim:
                        max_sim = avg_sim
                        merge_idx = (i, j)
            
            # 如果最大相似度低于阈值，停止合并
            if max_sim < self._similarity_threshold:
                break
            
            # 合并簇
            i, j = merge_idx
            clusters[i].extend(clusters[j])
            clusters.pop(j)
        
        return clusters
    
    def _determine_reason(
        self,
        cluster: list[str],
        video_paths: list[str],
        vision_embeddings: dict[str, list[float]],
        audio_embeddings: dict[str, list[float]],
    ) -> GroupingReason:
        """判断分组原因"""
        # 计算组内平均视觉和音频相似度
        indices = [video_paths.index(vp) for vp in cluster]
        
        v_sims = []
        a_sims = []
        for i in range(len(indices)):
            for j in range(i + 1, len(indices)):
                v1 = np.array(vision_embeddings[video_paths[indices[i]]])
                v2 = np.array(vision_embeddings[video_paths[indices[j]]])
                a1 = np.array(audio_embeddings[video_paths[indices[i]]])
                a2 = np.array(audio_embeddings[video_paths[indices[j]]])
                
                v_sim = self._cosine_similarity(list(v1), list(v2))
                a_sim = self._cosine_similarity(list(a1), list(a2))
                v_sims.append(v_sim)
                a_sims.append(a_sim)
        
        avg_v = np.mean(v_sims) if v_sims else 0.0
        avg_a = np.mean(a_sims) if a_sims else 0.0
        
        # 判断主要原因
        if avg_v > 0.8 and avg_a > 0.8:
            return GroupingReason.VISUAL_AUDIO_COMBINED
        elif avg_v > avg_a:
            return GroupingReason.VISUAL_SIMILAR
        else:
            return GroupingReason.AUDIO_SIMILAR
    
    def _make_group(
        self,
        video_paths: list[str],
        confidence: float,
        reason: GroupingReason,
    ) -> VideoGroup:
        """创建分组"""
        self._group_counter += 1
        return VideoGroup(
            group_id=f"group_{self._group_counter:03d}",
            video_paths=video_paths,
            confidence=confidence,
            reason=reason.value,
        )


__all__ = [
    "SmartGrouper",
    "VideoGroup",
    "VisionEmbedder",
    "AudioEmbedder",
    "GroupingReason",
    "MockVisionEmbedder",
    "MockAudioEmbedder",
]