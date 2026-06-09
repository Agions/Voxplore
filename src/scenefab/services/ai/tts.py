"""
TTS 文本转语音服务
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TTSService:
    """TTS 服务"""

    VOICE_MAP = {
        "zh-CN-XiaoxiaoNeural": "晓晓",
        "zh-CN-YunxiNeural": "云希",
        "zh-CN-YunyangNeural": "云扬",
        "zh-CN-XiaoyiNeural": "小艺",
    }

    def __init__(self, config: dict[str, Any] = None) -> None:  # type: ignore[assignment]
        self.config = config or {}
        self.provider = self.config.get("provider", "edge")
        self.voice = self.config.get("voice", "zh-CN-XiaoxiaoNeural")
        self.rate = self.config.get("rate", 1.0)
        self.pitch = self.config.get("pitch", 0.0)

    def generate_speech(
        self,
        text: str,
        output_path: str,
        voice: str = None,  # type: ignore[assignment]
        rate: float = None,  # type: ignore[assignment]
        **kwargs,
    ) -> str | None:
        voice = voice or self.voice
        rate = rate or self.rate

        if self.provider == "edge":
            return self._edge_tts(text, output_path, voice, rate)
        elif self.provider == "f5":
            return self._f5_tts(text, output_path, **kwargs)
        else:
            logger.error(f"Unknown TTS provider: {self.provider}")
            return None

    async def generate_speech_async(
        self,
        text: str,
        output_path: str,
        voice: str = None,  # type: ignore[assignment]
        rate: float = None,  # type: ignore[assignment]
        **kwargs,
    ) -> str | None:
        """
        异步生成语音（edge-tts 原生支持异步）
        适合批量并行合成多个音频
        """
        voice = voice or self.voice
        rate = rate or self.rate

        if self.provider != "edge":
            # 非 edge provider 回退到同步
            return self.generate_speech(text, output_path, voice, rate)

        try:
            import edge_tts

            rate_str = f"{int((rate - 1) * 100)}%"
            communicate = edge_tts.Communicate(text, voice, rate=rate_str)
            await communicate.save(output_path)
            return output_path

        except ImportError:
            logger.error("edge-tts is not installed")
            return None
        except Exception as e:
            logger.error(f"Edge-TTS async generation failed: {e}")
            return None

    @staticmethod
    async def generate_batch_async(
        items: list[tuple[str, str, str]],  # (text, output_path, voice)
        rate: float = 1.0,
        max_concurrent: int = 4,
    ) -> list[str | None]:
        """
        批量异步生成语音
        items: [(text, output_path, voice), ...]
        max_concurrent: 最大并发数
        """
        import asyncio

        import edge_tts

        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_one(text: str, output_path: str, voice: str) -> str | None:
            async with semaphore:
                try:
                    rate_str = f"{int((rate - 1) * 100)}%"
                    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
                    await communicate.save(output_path)
                    return output_path
                except Exception as e:
                    logger.error(f"TTS failed for {output_path}: {e}")
                    return None

        tasks = [generate_one(text, path, voice) for text, path, voice in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [r if not isinstance(r, Exception) else None for r in results]

    @staticmethod
    async def generate_batch_streaming(
        items: list[tuple[str, str, str]],  # (text, output_path, voice)
        rate: float = 1.0,
        max_concurrent: int = 4,
        progress_callback=None,
    ) -> list[str | None]:
        """
        批量异步流式生成语音，边生成边写入文件，每片断完成即触发回调

        Args:
            items: [(text, output_path, voice), ...]
            rate: 语速倍率
            max_concurrent: 最大并发数
            progress_callback: 进度回调，signature: callback(index, total, timestamp_dict)
        """
        import asyncio

        import edge_tts

        semaphore = asyncio.Semaphore(max_concurrent)
        completed_count = 0

        async def generate_one(
            index: int, text: str, output_path: str, voice: str
        ) -> str | None:
            nonlocal completed_count
            async with semaphore:
                try:
                    rate_str = f"{int((rate - 1) * 100)}%"
                    communicate = edge_tts.Communicate(text, voice, rate=rate_str)

                    # 流式写入
                    with open(output_path, "wb") as f:
                        async for chunk in communicate.stream():
                            if chunk["type"] == "audio":
                                f.write(chunk["data"])
                            elif (
                                chunk["type"] == "SentenceBoundary"
                                and progress_callback
                            ):
                                progress_callback(
                                    index,
                                    len(items),
                                    {
                                        "text": chunk["text"],
                                        "start": chunk["offset"] / 10_000_000,
                                        "end": (chunk["offset"] + chunk["duration"])
                                        / 10_000_000,
                                    },
                                )

                    return output_path
                except Exception as e:
                    logger.error(f"TTS streaming failed for {output_path}: {e}")
                    return None

        tasks = [
            generate_one(i, text, path, voice)
            for i, (text, path, voice) in enumerate(items)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [r if not isinstance(r, Exception) else None for r in results]

    def _edge_tts(
        self, text: str, output_path: str, voice: str, rate: float
    ) -> str | None:
        try:
            import edge_tts

            rate_str = f"{int((rate - 1) * 100)}%"

            async def generate() -> None:
                communicate = edge_tts.Communicate(text, voice, rate=rate_str)
                await communicate.save(output_path)

            import asyncio

            asyncio.run(generate())
            return output_path

        except ImportError:
            logger.error("edge-tts is not installed")
            return None
        except Exception as e:
            logger.error(f"Edge-TTS generation failed: {e}")
            return None

    def _f5_tts(self, text: str, output_path: str, **kwargs) -> str | None:
        logger.warning("F5-TTS requires reference audio, use edge-tts instead")
        return None


__all__ = ["TTSService"]
