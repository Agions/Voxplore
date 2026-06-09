"""TTS (Text-to-Speech) audio generation for narration blocks."""

import logging
import os
from collections.abc import Callable

from ..models.media import AudioTrack
from ..models.narration import NarrationBlock

logger = logging.getLogger(__name__)


class TTSGenerator:
    """TTS 配音生成器 V2"""

    def __init__(self, tts_service=None):
        from ..services import get_ai_service_manager

        ai_service_manager = get_ai_service_manager()
        self.tts = tts_service or ai_service_manager.tts

    def generate(
        self,
        narrations: list[NarrationBlock],
        output_dir: str,
        voice: str = "zh-CN-XiaoxiaoNeural",
        progress_callback: Callable | None = None,
        use_async: bool = True,
        max_concurrent: int = 4,
    ) -> AudioTrack | None:
        """
        生成配音

        Args:
            use_async: 使用异步并行生成（默认开启）
            max_concurrent: 最大并发数
        """
        os.makedirs(output_dir, exist_ok=True)

        if use_async and hasattr(self.tts, "generate_batch_async"):
            # 使用异步并行生成
            return self._generate_async(
                narrations, output_dir, voice, progress_callback, max_concurrent
            )
        else:
            # 回退到串行生成
            return self._generate_sync(narrations, output_dir, voice, progress_callback)

    def _generate_async(
        self,
        narrations: list[NarrationBlock],
        output_dir: str,
        voice: str,
        progress_callback: Callable | None,
        max_concurrent: int,
    ) -> AudioTrack | None:
        """异步并行流式生成配音（边生成边通知进度）"""
        import asyncio

        texts = [n.text for n in narrations]
        output_paths = [
            os.path.join(output_dir, f"narration_{i:03d}.mp3")
            for i in range(len(narrations))
        ]
        rates = []

        for _i, narration in enumerate(narrations):
            duration = narration.end_time - narration.start_time
            text_duration = len(narration.text) / 5.0
            rate = max(0.5, min(2.0, text_duration / duration))
            rates.append(rate)

        # 构建进度回调包装器
        def make_progress_wrapper(narr_idx: int):
            def wrapper(done: bool, info: dict = None):
                if progress_callback and info:
                    # 转换句子级进度为整体进度
                    progress_callback(narr_idx + 1, len(narrations))

            return wrapper

        # 使用流式批量生成
        items = [
            (text, path, voice) for text, path in zip(texts, output_paths, strict=False)
        ]

        if hasattr(self.tts, "generate_batch_streaming"):
            # 使用新的流式异步方法
            async def run_streaming():
                return await self.tts.generate_batch_streaming(
                    items, 1.0, max_concurrent, make_progress_wrapper(0)
                )

            # 包装回调支持多任务并发进度
            def streaming_progress_callback(index, total, ts_info):
                if progress_callback:
                    # 粗略估计：已完成 index 个任务
                    progress_callback(index + 1, total)

            async def run_with_callback():
                return await self.tts.generate_batch_streaming(
                    items, 1.0, max_concurrent, streaming_progress_callback
                )

            audio_files = asyncio.run(run_with_callback())
        else:
            # 回退到普通异步批量
            audio_files = asyncio.run(
                self.tts.generate_batch_async(items, 1.0, max_concurrent)
            )

        audio_files = [f for f in audio_files if f and os.path.exists(f)]

        if not audio_files:
            logger.warning("No audio files generated")
            return None

        total_duration = sum(n.end_time - n.start_time for n in narrations)
        final_audio = os.path.join(output_dir, "final_narration.mp3")

        if len(audio_files) == 1:
            import shutil

            shutil.copy(audio_files[0], final_audio)
        else:
            self._concatenate_audio(audio_files, final_audio)

        if progress_callback:
            progress_callback(len(narrations), len(narrations))

        return AudioTrack(
            audio_path=final_audio, duration=total_duration, voice=voice, rate=1.0
        )

    def _generate_sync(
        self,
        narrations: list[NarrationBlock],
        output_dir: str,
        voice: str,
        progress_callback: Callable | None,
    ) -> AudioTrack | None:
        """串行生成配音（回退方案）"""
        audio_files = []
        total_duration = 0.0

        for i, narration in enumerate(narrations):
            text = narration.text
            output_path = os.path.join(output_dir, f"narration_{i:03d}.mp3")

            duration = narration.end_time - narration.start_time
            text_duration = len(text) / 5.0
            rate = max(0.5, min(2.0, text_duration / duration))

            if self.tts:
                result = self.tts.generate_speech(
                    text=text, output_path=output_path, voice=voice, rate=rate
                )

                if result and os.path.exists(result):
                    audio_files.append(result)
                    total_duration += duration
                else:
                    logger.warning(f"TTS generation failed for block {i}")
            else:
                logger.warning("No TTS service available")

            if progress_callback:
                progress_callback(i + 1, len(narrations))

        if not audio_files:
            return None

        final_audio = os.path.join(output_dir, "final_narration.mp3")

        if len(audio_files) == 1:
            import shutil

            shutil.copy(audio_files[0], final_audio)
        else:
            self._concatenate_audio(audio_files, final_audio)

        return AudioTrack(
            audio_path=final_audio, duration=total_duration, voice=voice, rate=1.0
        )

    def _concatenate_audio(self, audio_files: list[str], output_path: str) -> bool:
        try:
            import subprocess

            list_file = output_path + ".list.txt"
            with open(list_file, "w") as f:
                for af in audio_files:
                    f.write(f"file '{af}'\n")

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    list_file,
                    "-c",
                    "copy",
                    output_path,
                ],
                capture_output=True,
                check=True,
            )

            os.remove(list_file)
            return True

        except Exception as e:
            logger.error(f"Audio concatenation failed: {e}")
            return False
