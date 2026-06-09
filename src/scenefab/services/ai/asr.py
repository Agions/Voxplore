"""
ASR 语音识别服务
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ASRService:
    """ASR 语音识别服务"""

    def __init__(self, config: dict[str, Any] = None) -> None:  # type: ignore[assignment]
        from scenefab.services.ai.infra import PersistentCache

        self.config = config or {}
        self.provider = self.config.get("provider", "faster-whisper")
        self.model_name = self.config.get("model", "large-v3")
        self.model = None
        self.cache = PersistentCache()

    def transcribe(
        self,
        audio_path: str,
        language: str = "zh",
        word_timestamps: bool = True,
        **kwargs,
    ) -> dict[str, Any] | None:
        # 检查缓存
        cache_key = f"{audio_path}:{language}:{word_timestamps}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached  # type: ignore[no-any-return]

        if self.provider == "faster-whisper":
            result = self._faster_whisper(audio_path, language, word_timestamps)
        elif self.provider == "sensevoice":
            result = self._sensevoice(audio_path, **kwargs)
        else:
            logger.error(f"Unknown ASR provider: {self.provider}")
            return None

        # 缓存结果
        if result:
            self.cache.set(cache_key, result, ttl=3600)

        return result

    def transcribe_batch(
        self,
        audio_paths: list[str],
        language: str = "zh",
        word_timestamps: bool = True,
        max_workers: int = 2,
    ) -> list[dict[str, Any] | None]:
        """
        批量转写（并行进程）
        适合多个音频文件同时转写
        """
        from concurrent.futures import ProcessPoolExecutor, as_completed

        results: list[dict[str, Any] | None] = [None] * len(audio_paths)

        # 模型实例在每个进程中独立创建
        def transcribe_one(args: tuple) -> tuple:
            path, lang, wts, model_name = args
            try:
                from faster_whisper import WhisperModel

                model = WhisperModel(model_name, device="cpu", compute_type="int8")
                segments, info = model.transcribe(
                    path,
                    language=lang if lang != "auto" else None,
                    word_timestamps=wts,
                )
                result_segments = []
                for seg in segments:
                    result_segments.append(
                        {"start": seg.start, "end": seg.end, "text": seg.text.strip()}
                    )
                return {
                    "text": "".join(s["text"] for s in result_segments),
                    "segments": result_segments,
                    "language": info.language,
                }
            except Exception as e:
                logger.error(f"Batch transcription failed for {path}: {e}")
                return None

        args_list = [
            (path, language, word_timestamps, self.model_name) for path in audio_paths
        ]

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(transcribe_one, args): i
                for i, args in enumerate(args_list)
            }

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    logger.error(f"Process failed for {audio_paths[idx]}: {e}")
                    results[idx] = None

        return results

    def _faster_whisper(
        self, audio_path: str, language: str, word_timestamps: bool
    ) -> dict[str, Any] | None:
        try:
            from faster_whisper import WhisperModel

            if self.model is None:
                self.model = WhisperModel(
                    self.model_name, device="cpu", compute_type="int8"
                )

            # 使用 batch_size 提升吞吐量
            segments, info = self.model.transcribe(  # type: ignore[attr-defined]
                audio_path,
                language=language if language != "auto" else None,
                word_timestamps=word_timestamps,
                batch_size=8,  # 批量处理提升速度
            )

            result_segments = []
            for seg in segments:
                result_segments.append(
                    {"start": seg.start, "end": seg.end, "text": seg.text.strip()}
                )

            return {
                "text": "".join(s["text"] for s in result_segments),
                "segments": result_segments,
                "language": info.language,
                "language_probability": info.language_probability,
            }

        except ImportError:
            logger.error("faster-whisper is not installed")
            return None
        except Exception as e:
            logger.error(f"Faster-Whisper transcription failed: {e}")
            return None

    def _sensevoice(self, audio_path: str, **kwargs) -> dict[str, Any] | None:
        logger.warning("SenseVoice integration not implemented yet")
        return None


__all__ = ["ASRService"]
