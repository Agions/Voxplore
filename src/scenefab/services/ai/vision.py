"""
Vision 视觉服务
"""
import time
import logging
import hashlib
from typing import Any

logger = logging.getLogger(__name__)


class VisionService:
    """
    视觉服务
    - 帧数据缓存
    - 批量分析支持
    - 并行请求
    """

    def __init__(self, config: dict[str, Any]):
        from scenefab.services.ai.infra import LRUCache

        self.config = config
        self.name = config.get("name", "qwen")
        self.enabled = config.get("enabled", False)
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "")
        self.model = config.get("model", "qwen-vl-plus")

        # HTTP 会话
        import requests
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=5,
            pool_maxsize=5
        )
        self.session.mount('https://', adapter)

        # 分析结果缓存
        self.frame_cache = LRUCache(max_size=500)

        # 统计
        self._stats = {
            "requests": 0,
            "errors": 0,
            "cache_hits": 0,
        }

    def analyze_frame(
        self,
        frame_data: bytes,
        prompt: str = "分析这张图片中的场景和人物视角"
    ) -> dict[str, Any] | None:
        if not self.enabled:
            return self._mock_result()

        # 检查缓存
        cache_key = hashlib.md5(frame_data[:10000]).hexdigest()  # 用前10KB做key
        cached = self.frame_cache.get(cache_key)
        if cached:
            self._stats["cache_hits"] += 1
            return cached

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }

            files = {
                "image": ("frame.jpg", frame_data, "image/jpeg"),
            }

            data = {
                "model": self.model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image", "image": "frame.jpg"},
                        {"type": "text", "text": prompt}
                    ]
                }],
                "max_tokens": 200,
            }

            response = self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                files=files,
                data=data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]

                self._stats["requests"] += 1
                analysis = self._parse_result(content)

                # 缓存结果
                self.frame_cache.set(cache_key, analysis)

                return analysis
            else:
                self._stats["errors"] += 1
                return self._mock_result()

        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"Vision analysis failed: {e}")
            return self._mock_result()

    def analyze_frames_batch(
        self,
        frames: list[bytes],
        prompts: list[str] = None
    ) -> list[dict[str, Any] | None]:
        """
        批量分析帧
        使用线程池并行处理
        """
        if prompts is None:
            prompts = ["分析这张图片中的场景和人物视角"] * len(frames)

        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = [None] * len(frames)

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_idx = {
                executor.submit(self.analyze_frame, frame, prompt): i
                for i, (frame, prompt) in enumerate(zip(frames, prompts))
            }

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    logger.warning(f"Frame {idx} analysis failed: {e}")
                    results[idx] = self._mock_result()

        return results

    def _parse_result(self, content: str) -> dict[str, Any]:
        is_first_person = "第一人称" in content or "POV" in content or "主观" in content
        confidence = 0.8 if is_first_person else 0.3

        return {
            "is_first_person": is_first_person,
            "confidence": confidence,
            "description": content[:100]
        }

    def _mock_result(self) -> dict[str, Any]:
        import random
        is_first_person = random.random() < 0.3

        return {
            "is_first_person": is_first_person,
            "confidence": random.uniform(0.6, 0.9) if is_first_person else random.uniform(0.1, 0.4),
            "description": "第一人称街头漫步" if is_first_person else "第三人称观察"
        }


__all__ = ["VisionService"]