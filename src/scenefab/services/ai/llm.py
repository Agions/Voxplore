"""
LLM 服务
"""
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM 服务
    - 连接池复用
    - 自动批量重试
    - 指数退避
    """

    def __init__(self, config: dict[str, Any]) -> None:
        from scenefab.services.ai.infra import CircuitBreaker, RateLimiter

        self.config = config
        self.name = config.get("name", "unknown")
        self.enabled = config.get("enabled", False)
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "")
        self.model = config.get("model", "")
        self.max_tokens = config.get("max_tokens", 8000)
        self.temperature = config.get("temperature", 0.7)

        self.rate_limiter = RateLimiter(
            rate=config.get("requests_per_second", 10.0),
            burst=config.get("burst_size", 20)
        )
        self.circuit_breaker = CircuitBreaker()

        # HTTP 会话复用
        import requests
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=0
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        self._stats = {
            "requests": 0,
            "errors": 0,
            "total_time": 0.0,
        }

    def generate(
        self,
        prompt: str,
        system: str = "",
        max_retries: int = 3,
        **kwargs
    ) -> str | None:
        if not self.enabled:
            return None

        if not self.circuit_breaker.can_execute():
            return None

        if not self.rate_limiter.acquire(timeout=30.0):
            return None

        start_time = time.time()
        last_error = None

        for attempt in range(max_retries):
            try:
                result = self._call_api(prompt, system, **kwargs)

                self.circuit_breaker.record_success()
                self._stats["requests"] += 1
                self._stats["total_time"] += time.time() - start_time

                return result

            except Exception as e:
                last_error = e
                self._stats["errors"] += 1

                # 指数退避
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 8)
                    time.sleep(wait_time)

        self.circuit_breaker.record_failure()
        logger.error(f"LLM call failed after {max_retries} attempts: {last_error}")
        return None

    def _call_api(
        self,
        prompt: str,
        system: str = "",
        **kwargs
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
        }

        response = self.session.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=kwargs.get("timeout", 60)
        )

        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            raise Exception(f"API error: {response.status_code}, {response.text}")


__all__ = ["LLMService"]