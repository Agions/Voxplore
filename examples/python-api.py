"""
SceneFab Python API 使用示例

本示例展示如何使用 SceneFab 的 Python API 进行视频解说生成。
"""

import asyncio
from pathlib import Path


# ============================================
# 1. 基础配置
# ============================================

def setup_config():
    """配置 SceneFab"""
    from scenefab.settings import Settings

    settings = Settings()
    settings.default_llm = "deepseek"
    settings.log_level = "INFO"
    return settings


# ============================================
# 2. 单视频解说生成
# ============================================

async def generate_commentary(video_path: str, output_dir: str):
    """
    为单个视频生成解说

    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
    """
    from scenefab.pipeline.narration_state_machine import NarrationStateMachine
    from scenefab.pipeline.narration_context import NarrationContext, Persona, NarrationStyle, Platform

    # 创建上下文
    context = NarrationContext(
        persona=Persona.DOCUMENTARY,
        style=NarrationStyle.SUSPENSE,
        platform=Platform.DOUYIN,
        target_duration=60,  # 目标时长 60 秒
    )

    # 创建状态机
    state_machine = NarrationStateMachine()

    # 运行生产流程
    result = await state_machine.run(
        video_path=video_path,
        context=context,
        output_dir=output_dir,
    )

    print(f"解说生成完成: {result.output_path}")
    return result


# ============================================
# 3. 批量处理
# ============================================

async def batch_process(series_dir: str, output_dir: str):
    """
    批量处理短剧整季

    Args:
        series_dir: 剧集目录
        output_dir: 输出目录
    """
    from scenefab.core.batch_processor import BatchProcessor

    processor = BatchProcessor(
        max_workers=2,
        retry_count=3,
    )

    # 扫描剧集
    episodes = list(Path(series_dir).glob("*.mp4"))
    print(f"找到 {len(episodes)} 集")

    # 批量处理
    results = await processor.process_batch(
        episodes=episodes,
        output_dir=output_dir,
        style="suspense",
        platform="douyin",
    )

    for result in results:
        print(f"  {result.episode}: {result.status}")

    return results


# ============================================
# 4. 视频理解
# ============================================

async def analyze_video(video_path: str):
    """
    分析视频内容

    Args:
        video_path: 视频文件路径
    """
    from scenefab.services.video.scene_analyzer import SceneAnalyzer

    analyzer = SceneAnalyzer()

    # 分析场景
    scenes = await analyzer.analyze(video_path)

    print(f"识别到 {len(scenes)} 个场景:")
    for i, scene in enumerate(scenes, 1):
        print(f"  场景 {i}: {scene.start_time:.1f}s - {scene.end_time:.1f}s")
        print(f"    描述: {scene.description}")

    return scenes


# ============================================
# 5. TTS 配音
# ============================================

async def synthesize_voice(text: str, output_path: str):
    """
    合成配音

    Args:
        text: 解说稿文本
        output_path: 音频输出路径
    """
    from scenefab.services.ai.tts_service import TTSService

    tts = TTSService()

    # 合成配音
    result = await tts.synthesize(
        text=text,
        voice="zh-CN-XiaoxiaoNeural",
        rate=1.0,
        pitch=0,
    )

    # 保存音频
    result.save(output_path)
    print(f"配音已保存: {output_path}")

    return result


# ============================================
# 6. 主程序
# ============================================

async def main():
    """主程序示例"""

    # 配置
    settings = setup_config()

    # 示例：单视频解说
    video_path = "./input/movie.mp4"
    output_dir = "./output"

    if Path(video_path).exists():
        result = await generate_commentary(video_path, output_dir)
        print(f"生成完成: {result.output_path}")
    else:
        print(f"视频文件不存在: {video_path}")
        print("请修改 video_path 为实际视频路径")


if __name__ == "__main__":
    asyncio.run(main())
