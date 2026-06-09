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
        texts = [n.text for n in narrations]
        output_paths = self._build_output_paths(output_dir, len(narrations))
        rates = self._compute_rates(narrations)
        _ = rates  # 保留以备扩展（与原行为一致：仅计算，未传递）

        items = self._build_tts_items(texts, output_paths, voice)
        audio_files = self._run_streaming_generation(
            items, narrations, progress_callback, max_concurrent
        )

        return self._finalize_audio(
            audio_files, narrations, output_dir, voice, progress_callback
        )

    @staticmethod
    def _build_output_paths(output_dir: str, count: int) -> list[str]:
        """构建每个 narration 的输出文件路径列表。"""
        return [
            os.path.join(output_dir, f"narration_{i:03d}.mp3")
            for i in range(count)
        ]

    @staticmethod
    def _compute_rates(narrations: list[NarrationBlock]) -> list[float]:
        """根据文本长度与时间窗估算每个 narration 的语速。"""
        rates: list[float] = []
        for narration in narrations:
            duration = narration.end_time - narration.start_time
            text_duration = len(narration.text) / 5.0
            rate = max(0.5, min(2.0, text_duration / duration))
            rates.append(rate)
        return rates

    @staticmethod
    def _build_tts_items(
        texts: list[str], output_paths: list[str], voice: str
    ) -> list[tuple]:
        """打包 (text, path, voice) 三元组供 TTS 批量接口使用。"""
        return [
            (text, path, voice)
            for text, path in zip(texts, output_paths, strict=False)
        ]

    def _run_streaming_generation(
        self,
        items: list[tuple],
        narrations: list[NarrationBlock],
        progress_callback: Callable | None,
        max_concurrent: int,
    ) -> list[str]:
        """调用流式/异步批量生成并返回已存在的音频文件路径列表。"""
        import asyncio

        if hasattr(self.tts, "generate_batch_streaming"):
            streaming_cb = self._make_streaming_progress_callback(
                progress_callback
            )
            audio_files = asyncio.run(
                self.tts.generate_batch_streaming(
                    items, 1.0, max_concurrent, streaming_cb
                )
            )
        else:
            # 回退到普通异步批量
            audio_files = asyncio.run(
                self.tts.generate_batch_async(items, 1.0, max_concurrent)
            )

        return [f for f in audio_files if f and os.path.exists(f)]

    @staticmethod
    def _make_streaming_progress_callback(
        progress_callback: Callable | None,
    ) -> Callable:
        """包装流式生成的进度回调，转换为整体任务级进度。"""

        def streaming_progress_callback(index, total, ts_info):
            if progress_callback:
                # 粗略估计：已完成 index 个任务
                progress_callback(index + 1, total)

        return streaming_progress_callback

    def _finalize_audio(
        self,
        audio_files: list[str],
        narrations: list[NarrationBlock],
        output_dir: str,
        voice: str,
        progress_callback: Callable | None,
    ) -> AudioTrack | None:
        """拼接/复制音频并构造最终 AudioTrack。"""
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
