#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Voxplore 命令行界面
"""
import os
import sys
import argparse
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voxplore.config import get_config
from voxplore.models import NarrationStyle, EmotionType
from voxplore.pipeline import VoxplorePipeline, PipelineConfig
from voxplore.exporters import JianyingExporter, SubtitleExporter, VideoExporter, ExportConfig
from voxplore.ai_services import ai_service_manager


def setup_logging(verbose: bool = False):
    """设置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )


def init_services():
    """初始化 AI 服务"""
    config = get_config()
    
    # 注册 LLM 服务
    for name, llm_config in config.llm_providers.items():
        if llm_config.enabled:
            ai_service_manager.register_llm(name, {
                "name": name,
                "enabled": llm_config.enabled,
                "api_key": llm_config.api_key,
                "base_url": llm_config.base_url,
                "model": llm_config.model,
                "max_tokens": llm_config.max_tokens,
                "temperature": llm_config.temperature,
            })
    
    # 注册视觉服务
    qwen_config = config.llm_providers.get("qwen")
    if qwen_config and qwen_config.enabled:
        ai_service_manager.register_vision({
            "name": "qwen",
            "enabled": True,
            "api_key": qwen_config.api_key,
            "base_url": qwen_config.base_url,
            "model": qwen_config.model,
        })
    
    # 注册 TTS
    ai_service_manager.register_tts({
        "provider": config.tts.provider,
        "voice": config.tts.voice,
        "rate": config.tts.rate,
    })
    
    # 注册 ASR
    ai_service_manager.register_asr({
        "provider": "faster-whisper",
        "model": "large-v3",
    })


def cmd_analyze(args):
    """分析视频"""
    from voxplore.video import VideoAnalyzer
    
    print(f"📹 正在分析视频: {args.video}")
    
    info = VideoAnalyzer.get_video_info(args.video)
    
    print(f"\n📊 视频信息:")
    print(f"  时长: {info['duration']:.1f} 秒")
    print(f"  分辨率: {info['width']}x{info['height']}")
    print(f"  帧率: {info['fps']:.1f} fps")
    print(f"  大小: {info['size'] / 1024 / 1024:.1f} MB")
    
    if args.scenes:
        print(f"\n🔍 检测场景变化...")
        scenes = VideoAnalyzer.detect_scenes(args.video)
        print(f"  发现 {len(scenes)} 个场景")
        for i, (start, end) in enumerate(scenes[:5]):
            print(f"    场景 {i+1}: {start:.1f}s - {end:.1f}s ({(end-start):.1f}s)")
        if len(scenes) > 5:
            print(f"    ... 还有 {len(scenes) - 5} 个场景")


def cmd_process(args):
    """处理视频"""
    init_services()
    
    print(f"🎬 开始处理视频: {args.video}")
    print(f"   风格: {args.style}")
    print(f"   情感: {args.emotion}")
    
    # 创建流水线
    pipeline_config = PipelineConfig(
        min_segment_duration=9.0,
        max_segment_duration=60.0,
        frame_sample_interval=1.0,
    )
    
    pipeline = VoxplorePipeline(pipeline_config)
    
    # 进度回调
    def progress_callback(progress, message):
        bar = "█" * int(progress * 30) + "░" * (30 - int(progress * 30))
        print(f"\r[{bar}] {progress*100:.0f}% {message}", end="", flush=True)
    
    # 处理
    style = NarrationStyle(args.style.lower())
    emotion = EmotionType(args.emotion.lower())
    
    try:
        project = pipeline.process(
            video_path=args.video,
            context=args.context or "",
            emotion=emotion,
            style=style,
            voice=args.voice,
            progress_callback=progress_callback,
            output_dir=args.output or "./output"
        )
        
        print(f"\n\n✅ 处理完成!")
        print(f"   提取片段: {len(project.segments)}")
        print(f"   情感峰值: {len(project.emotion_peaks)}")
        print(f"   解说块: {len(project.narration_blocks)}")
        
        if args.export:
            export_project(project, args)
        
    except Exception as e:
        print(f"\n\n❌ 处理失败: {e}")
        return 1
    
    return 0


def export_project(project, args):
    """导出项目"""
    output_dir = args.output or "./output"
    
    if args.format == "jianying":
        print(f"\n📦 导出剪映草稿...")
        exporter = JianyingExporter()
        draft_path = exporter.export(project, output_dir)
        print(f"   草稿路径: {draft_path}")
    
    elif args.format == "mp4":
        print(f"\n📦 导出 MP4 视频...")
        exporter = VideoExporter()
        output_path = os.path.join(output_dir, f"{project.name}.mp4")
        success = exporter.export(project, output_path)
        if success:
            print(f"   视频路径: {output_path}")
    
    elif args.format == "srt":
        print(f"\n📦 导出字幕...")
        output_path = os.path.join(output_dir, f"{project.name}.srt")
        SubtitleExporter.export_srt(project.subtitles, output_path)
        print(f"   字幕路径: {output_path}")


def cmd_batch(args):
    """批量处理（优化版 - 并行）"""
    init_services()
    
    video_files = []
    for pattern in args.patterns:
        video_files.extend(Path(".").glob(pattern))
    
    video_files = [str(v) for v in video_files if v.suffix.lower() in [".mp4", ".mov", ".avi"]]
    
    if not video_files:
        print("❌ 未找到视频文件")
        return 1
    
    print(f"📁 找到 {len(video_files)} 个视频文件")
    
    # 根据文件数量决定并行度
    max_workers = min(args.workers or 4, len(video_files))
    
    pipeline = VoxplorePipeline()
    results = []
    completed = 0
    
    def process_one(video: str) -> tuple:
        try:
            project = pipeline.process(video)
            return (video, True, len(project.segments), None)
        except Exception as e:
            return (video, False, 0, str(e))
    
    # 并行处理
    if max_workers > 1 and len(video_files) > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        print(f"⚡ 使用 {max_workers} 个 worker 并行处理")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_one, v): v for v in video_files}
            
            for future in as_completed(futures):
                video, success, count, error = future.result()
                completed += 1
                
                if success:
                    print(f"[{completed}/{len(video_files)}] ✅ {video}: {count} 个片段")
                else:
                    print(f"[{completed}/{len(video_files)}] ❌ {video}: {error}")
                
                results.append((video, success))
    else:
        # 串行处理
        for i, video in enumerate(video_files):
            print(f"\n[{i+1}/{len(video_files)}] 处理: {video}")
            
            try:
                project = pipeline.process(video)
                print(f"   ✅ 完成: {len(project.segments)} 个片段")
                results.append((video, True))
            except Exception as e:
                print(f"   ❌ 失败: {e}")
                results.append((video, False))
    
    # 汇总
    success_count = sum(1 for _, s in results if s)
    print(f"\n📊 完成: {success_count}/{len(video_files)} 成功")
    
    return 0 if success_count == len(video_files) else 1


def main():
    parser = argparse.ArgumentParser(
        description="Voxplore - AI 视频解说工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # analyze 命令
    analyze_parser = subparsers.add_parser("analyze", help="分析视频")
    analyze_parser.add_argument("video", help="视频文件路径")
    analyze_parser.add_argument("--scenes", action="store_true", help="检测场景")
    
    # process 命令
    process_parser = subparsers.add_parser("process", help="处理视频")
    process_parser.add_argument("video", help="视频文件路径")
    process_parser.add_argument("-o", "--output", help="输出目录")
    process_parser.add_argument("-s", "--style", default="documentary", 
                                choices=["healing", "mysterious", "inspirational", 
                                        "nostalgic", "romantic", "humorous", "documentary"],
                                help="解说风格")
    process_parser.add_argument("-e", "--emotion", default="neutral",
                               choices=["calm", "excited", "emotional", "mysterious", "neutral"],
                               help="情感类型")
    process_parser.add_argument("-c", "--context", help="背景上下文")
    process_parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural", help="配音语音")
    process_parser.add_argument("--export", action="store_true", help="处理后导出")
    process_parser.add_argument("--format", default="jianying",
                               choices=["jianying", "mp4", "srt"],
                               help="导出格式")
    
    # batch 命令
    batch_parser = subparsers.add_parser("batch", help="批量处理")
    batch_parser.add_argument("patterns", nargs="+", help="文件匹配模式，如 *.mp4")
    batch_parser.add_argument("-w", "--workers", type=int, default=4, help="并行 worker 数")
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    if args.command is None:
        parser.print_help()
        return 0
    
    if args.command == "analyze":
        return cmd_analyze(args)
    elif args.command == "process":
        return cmd_process(args)
    elif args.command == "batch":
        return cmd_batch(args)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
