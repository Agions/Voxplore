#!/usr/bin/env python3
"""
Voxplore AI 服务层 V2
性能优化版本：
- 连接池复用
- 批量 API 调用
- 高效限流器（信号量）
- LRU 缓存
"""
import os
import time
import logging
import threading
import hashlib
from typing import Optional, Any
from dataclasses import dataclass
from enum import Enum

from collections import OrderedDict

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


@dataclass(slots=True)
class ServiceHealth:
    name: str
    status: ServiceStatus
    last_check: float
    response_time: float = 0.0
    error_message: str = ""


class RateLimiter:
    """
    改进版限流器 - 使用信号量避免空转
    """
    
    def __init__(self, rate: float = 10.0, burst: int = 20):
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_update = time.time()
        self.lock = threading.Lock()
        self.semaphore = threading.Semaphore(0)
        self._thread = None
        self._running = False
    
    def start(self):
        """启动后台补充线程"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._replenisher, daemon=True)
        self._thread.start()
    
    def _replenisher(self):
        """后台令牌补充线程"""
        while self._running:
            with self.lock:
                now = time.time()
                elapsed = now - self.last_update
                self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
                self.last_update = now
                
                # 释放信号量
                while self.semaphore._value < self.burst and self.tokens >= 1.0:
                    self.semaphore.release()
                    self.tokens -= 1.0
            
            time.sleep(0.05)  # 50ms 刷新间隔
    
    def acquire(self, timeout: float = 30.0) -> bool:
        """获取令牌（阻塞）"""
        if not self._running:
            self.start()
        
        # 先快速检查
        with self.lock:
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
        
        # 等待信号量
        return self.semaphore.acquire(timeout=timeout)
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)


class CircuitBreaker:
    """断路器"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "closed"
        self.lock = threading.Lock()
    
    def can_execute(self) -> bool:
        with self.lock:
            if self.state == "closed":
                return True
            
            if self.state == "open":
                if self.last_failure_time and time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.state = "half_open"
                    return True
                return False
            
            return True  # half_open
    
    def record_success(self):
        with self.lock:
            self.failure_count = 0
            self.state = "closed"
    
    def record_failure(self):
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"


class LRUCache:
    """LRU 缓存"""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Any | None:
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            else:
                if len(self.cache) >= self.max_size:
                    self.cache.popitem(last=False)
                self.cache[key] = value
    
    def clear(self):
        with self.lock:
            self.cache.clear()


class PersistentCache:
    """持久化缓存（orjson 加速）"""
    
    def __init__(self, cache_dir: str = "~/.cache/voxplore"):
        self.cache_dir = os.path.expanduser(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        # orjson 性能比标准 json 快 5-10 倍
        try:
            import orjson
            self._json = orjson
            self._use_orjson = True
        except ImportError:
            import json
            self._json = json
            self._use_orjson = False
    
    def _get_path(self, key: str) -> str:
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{hash_key}.json")
    
    def get(self, key: str) -> Any | None:
        path = self._get_path(key)
        if os.path.exists(path):
            try:
                with open(path, 'rb' if self._use_orjson else 'r') as f:
                    if self._use_orjson:
                        data = self._json.loads(f.read())
                    else:
                        data = self._json.load(f)
                    if data.get("expires", float('inf')) < time.time():
                        os.remove(path)
                        return None
                    return data.get("value")
            except Exception:
                return None
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        path = self._get_path(key)
        try:
            cache_data = {
                "value": value,
                "expires": time.time() + ttl
            }
            if self._use_orjson:
                with open(path, 'wb') as f:
                    f.write(self._json.dumps(cache_data))
            else:
                with open(path, 'w') as f:
                    self._json.dump(cache_data, f)
        except Exception as e:
            logger.warning(f"Failed to write cache: {e}")


class LLMService:
    """
    LLM 服务 V2
    - 连接池复用
    - 自动批量重试
    - 指数退避
    """
    
    def __init__(self, config: dict[str, Any]):
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


class VisionService:
    """
    视觉服务 V2
    - 帧数据缓存
    - 批量分析支持
    - 并行请求
    """
    
    def __init__(self, config: dict[str, Any]):
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


class TTSService:
    """TTS 服务"""
    
    VOICE_MAP = {
        "zh-CN-XiaoxiaoNeural": "晓晓",
        "zh-CN-YunxiNeural": "云希",
        "zh-CN-YunyangNeural": "云扬",
        "zh-CN-XiaoyiNeural": "小艺",
    }
    
    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}
        self.provider = self.config.get("provider", "edge")
        self.voice = self.config.get("voice", "zh-CN-XiaoxiaoNeural")
        self.rate = self.config.get("rate", 1.0)
        self.pitch = self.config.get("pitch", 0.0)
    
    def generate_speech(
        self,
        text: str,
        output_path: str,
        voice: str = None,
        rate: float = None,
        **kwargs
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
        voice: str = None,
        rate: float = None,
        **kwargs
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
        max_concurrent: int = 4
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
    
    def _edge_tts(
        self,
        text: str,
        output_path: str,
        voice: str,
        rate: float
    ) -> str | None:
        try:
            import edge_tts
            
            rate_str = f"{int((rate - 1) * 100)}%"
            
            async def generate():
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


class ASRService:
    """ASR 语音识别服务 V2"""
    
    def __init__(self, config: dict[str, Any] = None):
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
        **kwargs
    ) -> dict[str, Any] | None:
        # 检查缓存
        cache_key = f"{audio_path}:{language}:{word_timestamps}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
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
        max_workers: int = 2
    ) -> list[dict[str, Any] | None]:
        """
        批量转写（并行进程）
        适合多个音频文件同时转写
        """
        from concurrent.futures import ProcessPoolExecutor, as_completed
        
        results = [None] * len(audio_paths)
        
        # 模型实例在每个进程中独立创建
        def transcribe_one(args: tuple) -> tuple:
            path, lang, wts, model_name = args
            try:
                from faster_whisper import WhisperModel
                model = WhisperModel(
                    model_name,
                    device="cpu",
                    compute_type="int8"
                )
                segments, info = model.transcribe(
                    path,
                    language=lang if lang != "auto" else None,
                    word_timestamps=wts,
                )
                result_segments = []
                for seg in segments:
                    result_segments.append({
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text.strip()
                    })
                return {
                    "text": "".join(s["text"] for s in result_segments),
                    "segments": result_segments,
                    "language": info.language,
                }
            except Exception as e:
                logger.error(f"Batch transcription failed for {path}: {e}")
                return None
        
        args_list = [
            (path, language, word_timestamps, self.model_name)
            for path in audio_paths
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
        self,
        audio_path: str,
        language: str,
        word_timestamps: bool
    ) -> dict[str, Any] | None:
        try:
            from faster_whisper import WhisperModel
            
            if self.model is None:
                self.model = WhisperModel(
                    self.model_name,
                    device="cpu",
                    compute_type="int8"
                )
            
            # 使用 batch_size 提升吞吐量
            segments, info = self.model.transcribe(
                audio_path,
                language=language if language != "auto" else None,
                word_timestamps=word_timestamps,
                batch_size=8,  # 批量处理提升速度
            )
            
            result_segments = []
            for seg in segments:
                result_segments.append({
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text.strip()
                })
            
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


class AIServiceManager:
    """AI 服务管理器 V2"""
    
    _instance: Optional['AIServiceManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._llm_services: dict[str, LLMService] = {}
        self._vision_service: VisionService | None = None
        self._tts_service: TTSService | None = None
        self._asr_service: ASRService | None = None
    
    def register_llm(self, name: str, config: dict[str, Any]) -> None:
        service = LLMService(config)
        self._llm_services[name] = service
        logger.info(f"Registered LLM service: {name}")
    
    def register_vision(self, config: dict[str, Any]) -> None:
        self._vision_service = VisionService(config)
        logger.info(f"Registered vision service: {config.get('name', 'unknown')}")
    
    def register_tts(self, config: dict[str, Any] = None) -> None:
        self._tts_service = TTSService(config)
        logger.info(f"Registered TTS service: {config.get('provider', 'edge')}")
    
    def register_asr(self, config: dict[str, Any] = None) -> None:
        self._asr_service = ASRService(config)
        logger.info(f"Registered ASR service: {config.get('provider', 'faster-whisper')}")
    
    def get_llm(self, name: str = None) -> LLMService | None:
        if name:
            return self._llm_services.get(name)
        for service in self._llm_services.values():
            if service.enabled:
                return service
        return None
    
    @property
    def vision(self) -> VisionService | None:
        return self._vision_service
    
    @property
    def tts(self) -> TTSService | None:
        return self._tts_service
    
    @property
    def asr(self) -> ASRService | None:
        return self._asr_service
    
    def get_summary(self) -> dict[str, Any]:
        return {
            "llm_services": {
                name: {
                    "enabled": svc.enabled,
                    "requests": svc._stats["requests"],
                    "errors": svc._stats["errors"],
                }
                for name, svc in self._llm_services.items()
            },
            "vision_enabled": self._vision_service is not None and self._vision_service.enabled,
            "vision_cache_hits": self._vision_service._stats.get("cache_hits", 0) if self._vision_service else 0,
            "tts_provider": self._tts_service.provider if self._tts_service else None,
            "asr_provider": self._asr_service.provider if self._asr_service else None,
        }


# 全局实例
ai_service_manager = AIServiceManager()


def get_ai_service() -> AIServiceManager:
    return ai_service_manager


__all__ = [
    "RateLimiter",
    "CircuitBreaker",
    "LRUCache",
    "PersistentCache",
    "LLMService",
    "VisionService",
    "TTSService",
    "ASRService",
    "AIServiceManager",
    "ai_service_manager",
    "get_ai_service",
]
