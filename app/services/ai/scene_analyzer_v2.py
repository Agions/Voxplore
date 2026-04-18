#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
场景分析器 V2 (Scene Analyzer V2)

扩展版场景分析器，在原有 SceneAnalyzer 基础上增加了：
- 重要性评分 (importance scoring)
- 关键时刻提取 (key moment extraction)
- 场景上下文提示生成 (scene context prompt generation)

继承自 SceneAnalyzer 的完整实现。

使用示例:
    from app.services.ai import SceneAnalyzerV2
    
    analyzer = SceneAnalyzerV2()
    scenes = analyzer.analyze_with_importance('video.mp4')
    
    # 提取最佳关键时刻
    key_moments = analyzer.extract_key_moments(scenes, top_k=5)
    
    # 生成场景上下文提示
    context_prompt = analyzer.generate_scene_context_prompt(scenes)
"""

import logging
from typing import List, Optional, Callable, Dict, Any

from .scene_analyzer import SceneAnalyzer
from .scene_models import SceneType, SceneInfo, AnalysisConfig

logger = logging.getLogger(__name__)


# 场景类型优先级（数值越高越重要）
SCENE_TYPE_PRIORITY: Dict[SceneType, int] = {
    SceneType.LANDSCAPE: 10,     # 风景画面 - 最适合展示
    SceneType.B_ROLL: 8,         # 素材画面 - 适合混剪
    SceneType.ACTION: 6,          # 动作场景
    SceneType.TALKING_HEAD: 4,   # 人物讲话 - 较少使用
    SceneType.TRANSITION: 2,      # 转场 - 不适合
    SceneType.TITLE: 3,           # 标题画面
    SceneType.PRODUCT: 5,         # 产品展示
    SceneType.UNKNOWN: 1,        # 未知 - 最低优先级
}


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
            'duration': 0.20,      # 时长权重
            'brightness': 0.15,    # 亮度权重
            'motion': 0.15,        # 运动程度权重
            'scene_type': 0.30,    # 场景类型权重（最重要）
            'audio': 0.20,         # 音频权重
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
        # 调用父类的 analyze 方法
        scenes = super().analyze(video_path)
        
        # 为每个场景计算增强版 suitability_score
        for scene in scenes:
            # 使用增强版评分算法
            scene.suitability_score = self._calculate_enhanced_suitability(scene)
            
            # 计算叙事重要性（如果提供回调或使用默认方法）
            if narration_importance_fn is not None:
                scene.narration_importance = narration_importance_fn(scene)
            elif hasattr(scene, 'narration_importance') and scene.narration_importance > 0:
                # 已有值，保持不变
                pass
            else:
                # 使用默认计算方法
                scene.narration_importance = self._calculate_default_narration_importance(scene)
        
        return scenes

    def _calculate_enhanced_suitability(self, scene: SceneInfo) -> float:
        """
        计算增强版适用性评分 (0-100)
        
        评分因素：
        - 时长：3-15秒为最佳（适合 narration）
        - 亮度：mid-range (0.3-0.7) 评分较高
        - 运动程度：moderate (0.2-0.6) 评分较高
        - 场景类型：LANDSCAPE > B_ROLL > ACTION > ...
        - 音频水平：higher is better
        
        Args:
            scene: 场景信息
            
        Returns:
            适用性评分 (0-100)
        """
        score = 50.0  # 基础分
        
        # === 1. 时长评分 (权重 20%) ===
        # 最佳时长 3-15秒，太短或太长都降低评分
        duration_score = self._score_duration(scene.duration)
        score += duration_score * self._importance_weights['duration'] * 2
        
        # === 2. 亮度评分 (权重 15%) ===
        # mid-range brightness (0.3-0.7) scores higher
        brightness_score = self._score_brightness(scene.avg_brightness)
        score += brightness_score * self._importance_weights['brightness'] * 2
        
        # === 3. 运动程度评分 (权重 15%) ===
        # moderate motion (0.2-0.6) scores higher
        motion_score = self._score_motion(scene.motion_level)
        score += motion_score * self._importance_weights['motion'] * 2
        
        # === 4. 场景类型评分 (权重 30%) ===
        # 根据场景类型加权
        type_score = self._score_scene_type(scene.type)
        score += type_score * self._importance_weights['scene_type'] * 2
        
        # === 5. 音频评分 (权重 20%) ===
        # higher audio presence scores higher
        audio_score = self._score_audio(scene.audio_level)
        score += audio_score * self._importance_weights['audio'] * 2
        
        # 确保分数在 0-100 范围内
        return max(0.0, min(100.0, score))

    def _score_duration(self, duration: float) -> float:
        """
        评分时长因素
        
        最佳范围: 3-15秒
        - 3-15秒: 100% 得分
        - 1-3秒或15-30秒: 60% 得分
        - <1秒或>30秒: 20% 得分
        
        Args:
            duration: 时长（秒）
            
        Returns:
            评分 (0-100)
        """
        if 3.0 <= duration <= 15.0:
            return 100.0
        elif 1.0 <= duration < 3.0 or 15.0 < duration <= 30.0:
            return 60.0
        else:
            return 20.0

    def _score_brightness(self, brightness: float) -> float:
        """
        评分亮度因素
        
        最佳范围: 0.3-0.7 (mid-range)
        归一化 brightness 到 0-1 范围后评分：
        - 0.3-0.7: 100% 得分
        - 边缘处线性衰减
        
        Args:
            brightness: 亮度值 (0.0-1.0)
            
        Returns:
            评分 (0-100)
        """
        if 0.3 <= brightness <= 0.7:
            return 100.0
        elif brightness < 0.3:
            # 线性插值: 0.0 -> 0.0, 0.3 -> 100.0
            return (brightness / 0.3) * 100.0
        else:  # brightness > 0.7
            # 线性插值: 0.7 -> 100.0, 1.0 -> 0.0
            return ((1.0 - brightness) / 0.3) * 100.0

    def _score_motion(self, motion: float) -> float:
        """
        评分运动程度因素
        
        最佳范围: 0.2-0.6 (moderate motion)
        - 0.2-0.6: 100% 得分
        - 静态 (<0.1) 或 过于混乱 (>0.9): 低分
        
        Args:
            motion: 运动程度 (0.0-1.0)
            
        Returns:
            评分 (0-100)
        """
        if 0.2 <= motion <= 0.6:
            return 100.0
        elif motion < 0.1:
            # 静态场景，得分较低
            return 30.0
        elif motion < 0.2:
            # 略微运动，线性插值
            return 30.0 + (motion - 0.1) / 0.1 * 70.0
        elif motion <= 0.9:
            # 超过最佳范围，线性衰减
            return 100.0 - (motion - 0.6) / 0.3 * 40.0
        else:
            # 过于混乱的场景
            return 20.0

    def _score_scene_type(self, scene_type: SceneType) -> float:
        """
        评分场景类型因素
        
        优先级顺序 (从高到低):
        LANDSCAPE > B_ROLL > ACTION > TALKING_HEAD > TITLE > PRODUCT > TRANSITION > UNKNOWN
        
        Args:
            scene_type: 场景类型
            
        Returns:
            评分 (0-100)
        """
        priority = SCENE_TYPE_PRIORITY.get(scene_type, 1)
        max_priority = max(SCENE_TYPE_PRIORITY.values())
        # 归一化到 0-100
        return (priority / max_priority) * 100.0

    def _score_audio(self, audio_level: float) -> float:
        """
        评分音频因素
        
        更高的音频水平得分更高
        0.0 -> 0分, 1.0 -> 100分
        
        Args:
            audio_level: 音频水平 (0.0-1.0)
            
        Returns:
            评分 (0-100)
        """
        return audio_level * 100.0

    def _calculate_default_narration_importance(self, scene: SceneInfo) -> float:
        """
        计算默认叙事重要性
        
        综合考虑场景类型、时长和适合度来计算叙事重要性。
        
        Args:
            scene: 场景信息
            
        Returns:
            叙事重要性 (0.0-1.0)
        """
        # 场景类型权重
        type_weight = SCENE_TYPE_PRIORITY.get(scene.type, 1) / max(SCENE_TYPE_PRIORITY.values())
        
        # 时长权重（太长或太短都不适合）
        if 3.0 <= scene.duration <= 15.0:
            duration_weight = 1.0
        elif 1.0 <= scene.duration < 3.0 or 15.0 < scene.duration <= 30.0:
            duration_weight = 0.6
        else:
            duration_weight = 0.2
        
        # 适合度权重
        suitability_weight = scene.suitability_score / 100.0
        
        # 综合评分
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
        """
        提取关键时刻（得分最高的场景）
        
        这些是展示原始素材的最佳时刻。
        
        Args:
            scenes: 场景列表（应已包含 suitability_score）
            top_k: 返回的场景数量上限
            min_score: 最低分数阈值，低于此分数的场景会被过滤
            
        Returns:
            按 suitability_score 降序排列的 top_k 个场景
            
        Example:
            >>> analyzer = SceneAnalyzerV2()
            >>> scenes = analyzer.analyze_with_importance('video.mp4')
            >>> key_moments = analyzer.extract_key_moments(scenes, top_k=5)
        """
        # 过滤低分场景
        filtered = [s for s in scenes if s.suitability_score >= min_score]
        
        # 按 suitability_score 降序排列
        sorted_scenes = sorted(
            filtered,
            key=lambda s: s.suitability_score,
            reverse=True
        )
        
        # 返回 top_k
        return sorted_scenes[:top_k]

    def extract_key_moments_by_type(
        self,
        scenes: List[SceneInfo],
        scene_type: SceneType,
        top_k: int = 3,
    ) -> List[SceneInfo]:
        """
        按场景类型提取关键时刻
        
        Args:
            scenes: 场景列表
            scene_type: 要筛选的场景类型
            top_k: 每种类型返回的场景数量上限
            
        Returns:
            指定的场景类型的 top_k 个高分场景
        """
        # 过滤指定类型
        filtered = [s for s in scenes if s.type == scene_type]
        
        # 按 suitability_score 降序排列
        sorted_scenes = sorted(
            filtered,
            key=lambda s: s.suitability_score,
            reverse=True
        )
        
        return sorted_scenes[:top_k]

    def generate_scene_context_prompt(self, scenes: List[SceneInfo]) -> str:
        """
        生成场景上下文提示（用于 ScriptGenerator）
        
        生成一个 markdown 格式的场景描述列表，包含：
        - 时间戳
        - 场景描述
        - 场景类型
        - 适合度评分
        
        Args:
            scenes: 场景列表
            
        Returns:
            Markdown 格式的场景描述字符串
            
        Example:
            >>> analyzer = SceneAnalyzerV2()
            >>> scenes = analyzer.analyze_with_importance('video.mp4')
            >>> prompt = analyzer.generate_scene_context_prompt(scenes)
            >>> # prompt 内容示例:
            >>> # ## 场景列表
            >>> # 
            >>> # 1. **[00:00-00:05]** 风景画面
            >>> #    - 类型: LANDSCAPE
            >>> #    - 评分: 95/100
            >>> #    - 描述: 开场空镜头，...
        """
        if not scenes:
            return "## 场景列表\n\n*暂无场景数据*"
        
        lines = ["## 场景列表\n"]
        
        for i, scene in enumerate(scenes, 1):
            # 格式化时间戳
            start_str = self._format_timestamp(scene.start)
            end_str = self._format_timestamp(scene.end)
            
            # 场景类型中文名
            type_name = self._get_scene_type_name_cn(scene.type)
            
            # 构建场景描述
            lines.append(f"{i}. **{start_str} - {end_str}** {type_name}")
            lines.append(f"   - 类型: `{scene.type.value}`")
            lines.append(f"   - 评分: {scene.suitability_score:.0f}/100")
            
            if scene.description:
                lines.append(f"   - 描述: {scene.description}")
            
            # 添加额外信息（如果有）
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
            
            lines.append("")  # 空行分隔
        
        return "\n".join(lines)

    def generate_brief_scene_summary(
        self,
        scenes: List[SceneInfo],
        max_scenes: int = 10,
    ) -> str:
        """
        生成简短场景摘要（适用于提示词）
        
        与 generate_scene_context_prompt 类似，但更简洁，
        只包含关键信息，适合作为 LLM 提示词的一部分。
        
        Args:
            scenes: 场景列表
            max_scenes: 最多包含的场景数
            
        Returns:
            简洁的场景描述字符串
        """
        if not scenes:
            return "视频包含0个有效场景。"
        
        # 按 suitability_score 排序取 top
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
        """
        格式化时间戳
        
        Args:
            seconds: 秒数
            
        Returns:
            MM:SS 格式字符串
        """
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def _get_scene_type_name_cn(self, scene_type: SceneType) -> str:
        """
        获取场景类型中文名
        
        Args:
            scene_type: 场景类型
            
        Returns:
            中文名称
        """
        type_names = {
            SceneType.LANDSCAPE: "风景",
            SceneType.B_ROLL: "素材",
            SceneType.ACTION: "动作",
            SceneType.TALKING_HEAD: "人物",
            SceneType.TRANSITION: "转场",
            SceneType.TITLE: "标题",
            SceneType.PRODUCT: "产品",
            SceneType.UNKNOWN: "未知",
        }
        return type_names.get(scene_type, "未知")

    def _describe_brightness(self, brightness: float) -> str:
        """
        描述亮度特征
        
        Args:
            brightness: 亮度值 (0.0-1.0)
            
        Returns:
            中文描述
        """
        if brightness < 0.2:
            return "暗"
        elif brightness < 0.4:
            return "偏暗"
        elif brightness < 0.6:
            return "适中"
        elif brightness < 0.8:
            return "偏亮"
        else:
            return "过亮"

    def _describe_motion(self, motion: float) -> str:
        """
        描述运动特征
        
        Args:
            motion: 运动程度 (0.0-1.0)
            
        Returns:
            中文描述
        """
        if motion < 0.1:
            return "静态"
        elif motion < 0.3:
            return "微动"
        elif motion < 0.5:
            return "适度"
        elif motion < 0.7:
            return "活跃"
        else:
            return "剧烈"


# =========== 便捷函数 ===========

def analyze_video_with_importance(
    video_path: str,
    config: Optional[AnalysisConfig] = None,
) -> List[SceneInfo]:
    """
    分析视频场景并计算重要性评分的便捷函数
    
    Args:
        video_path: 视频文件路径
        config: 分析配置
        
    Returns:
        场景列表（包含 suitability_score）
    """
    analyzer = SceneAnalyzerV2(config)
    return analyzer.analyze_with_importance(video_path)


def extract_key_moments(
    scenes: List[SceneInfo],
    top_k: int = 5,
) -> List[SceneInfo]:
    """
    从场景列表中提取关键时刻的便捷函数
    
    Args:
        scenes: 场景列表
        top_k: 返回数量
        
    Returns:
        关键时刻列表
    """
    analyzer = SceneAnalyzerV2()
    return analyzer.extract_key_moments(scenes, top_k)


if __name__ == '__main__':
    # 演示用法
    import sys
    
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        
        print("=" * 60)
        print("SceneAnalyzerV2 演示")
        print("=" * 60)
        
        analyzer = SceneAnalyzerV2()
        
        print("\n正在分析视频...")
        scenes = analyzer.analyze_with_importance(video_path)
        
        print(f"\n检测到 {len(scenes)} 个场景")
        print("-" * 60)
        
        for scene in scenes:
            print(f"\n场景 {scene.index}")
            print(f"  时间: {scene.start:.2f}s - {scene.end:.2f}s ({scene.duration:.2f}s)")
            print(f"  类型: {scene.type.value}")
            print(f"  亮度: {scene.avg_brightness:.2f}")
            print(f"  运动: {scene.motion_level:.2f}")
            print(f"  音频: {scene.audio_level:.2f}")
            print(f"  评分: {scene.suitability_score:.1f}/100")
            if hasattr(scene, 'narration_importance'):
                print(f"  叙事重要性: {scene.narration_importance:.2f}")
        
        print("\n" + "=" * 60)
        print("关键时刻 (Top 5)")
        print("=" * 60)
        
        key_moments = analyzer.extract_key_moments(scenes, top_k=5)
        for i, scene in enumerate(key_moments, 1):
            print(f"\n{i}. 场景 {scene.index} ({scene.start:.1f}s - {scene.end:.1f}s)")
            print(f"   类型: {scene.type.value}, 评分: {scene.suitability_score:.1f}")
        
        print("\n" + "=" * 60)
        print("场景上下文提示")
        print("=" * 60)
        print(analyzer.generate_scene_context_prompt(scenes))
        
    else:
        print("用法: python scene_analyzer_v2.py <video_path>")
