#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Voxplore 使用示例
"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voxplore.config import get_config
from voxplore.models import NarrationStyle, EmotionType, VideoSegment
from voxplore.pipeline import VoxplorePipeline, PipelineConfig
from voxplore.exporters import JianyingExporter, SubtitleExporter, VideoExporter
from voxplore.video import VideoAnalyzer


def example_analyze_video():
    """示例：分析视频"""
    print("=" * 50)
    print("示例1: 分析视频")
    print("=" * 50)
    
    # 获取视频信息
    # info = VideoAnalyzer.get_video_info("your_video.mp4")
    # print(f"时长: {info['duration']:.1f}秒")
    # print(f"分辨率: {info['width']}x{info['height']}")
    
    print("请提供视频路径后运行此示例")


def example_process_video():
    """示例：处理视频"""
    print("=" * 50)
    print("示例2: 处理视频生成解说")
    print("=" * 50)
    
    # 配置
    config = PipelineConfig(
        min_segment_duration=9.0,
        max_segment_duration=60.0,
        frame_sample_interval=1.0,
        min_confidence=0.6,
    )
    
    # 创建流水线
    pipeline = VoxplorePipeline(config)
    
    # 处理视频
    # project = pipeline.process(
    #     video_path="your_video.mp4",
    #     context="这是一个关于旅行的故事",
    #     emotion=EmotionType.NEUTRAL,
    #     style=NarrationStyle.DOCUMENTARY,
    #     voice="zh-CN-XiaoxiaoNeural",
    # )
    
    print("请提供视频路径后运行此示例")


def example_export_jianying():
    """示例：导出剪映草稿"""
    print("=" * 50)
    print("示例3: 导出剪映草稿")
    print("=" * 50)
    
    # from voxplore.models import VideoProject
    # 
    # # 假设已有项目
    # project = VideoProject(name="我的解说视频")
    # 
    # # 导出剪映草稿
    # exporter = JianyingExporter()
    # draft_path = exporter.export(project, output_dir="./output")
    # print(f"草稿已导出到: {draft_path}")
    
    print("请先生成项目后运行此示例")


def example_batch_processing():
    """示例：批量处理"""
    print("=" * 50)
    print("示例4: 批量处理视频")
    print("=" * 50)
    
    # import glob
    # 
    # video_files = glob.glob("videos/*.mp4")
    # 
    # pipeline = VoxplorePipeline()
    # 
    # for video_path in video_files:
    #     try:
    #         project = pipeline.process(video_path)
    #         print(f"✅ {video_path}: {len(project.segments)} 个片段")
    #     except Exception as e:
    #         print(f"❌ {video_path}: {e}")
    
    print("请提供视频文件夹后运行此示例")


def main():
    """运行所有示例"""
    print("\n🎬 Voxplore 使用示例\n")
    
    examples = [
        ("分析视频", example_analyze_video),
        ("处理视频", example_process_video),
        ("导出剪映", example_export_jianying),
        ("批量处理", example_batch_processing),
    ]
    
    for i, (name, func) in enumerate(examples, 1):
        try:
            func()
        except Exception as e:
            print(f"示例 {i} 执行出错: {e}")
        print()


if __name__ == "__main__":
    main()
