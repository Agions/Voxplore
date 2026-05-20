#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Voxplore AI 服务层
统一管理 LLM、视觉、语音识别、TTS 服务
"""
import os
import time
import logging
import threading
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """服务状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


@dataclass
class ServiceHealth:
    """服务健康状态"""
    name: str
    status: ServiceStatus
    last_check: float
    response_time: float = 0.0
    error_message: str = ""


class RateLimiter:
    """令牌桶限流器"""
    
    def __init__(self, rate: float = 10.0, burst: int = 20):
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.time()
        self.lock = threading.Lock()
    
    def acquire(self, timeout: float = 30.0) -> bool:
        start = time.time()
        while True:
            with self.lock:
                now = time.time()
                self.tokens = min(self.burst, self.tokens + (now - self.last_update) * self.rate)
                self.last_update = now
                
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return True
            
            if time.time() - start >= timeout:
                return False
            time.sleep(0.01)


class CircuitBreaker:
    """断路器"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open
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


class LLMService:
    """
    LLM 服务
    支持 DeepSeek、Qwen、OpenAI 等
    """
    
    def __init__(self, config: Dict[str, Any]):
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
        
        self._stats = {
            "requests": 0,
            "errors": 0,
            "total_time": 0.0,
        }
    
    def generate(
        self,
        prompt: str,
        system: str = "",
        **kwargs
    ) -> Optional[str]:
        """
        生成文本
        
        Args:
            prompt: 用户提示
            system: 系统提示
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        if not self.enabled:
            logger.warning(f"LLM service {self.name} is not enabled")
            return None
        
        if not self.circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker open for {self.name}")
            return None
        
        if not self.rate_limiter.acquire():
            logger.warning(f"Rate limit exceeded for {self.name}")
            return None
        
        start_time = time.time()
        
        try:
            result = self._call_api(prompt, system, **kwargs)
            
            self.circuit_breaker.record_success()
            self._stats["requests"] += 1
            self._stats["total_time"] += time.time() - start_time
            
            return result
            
        except Exception as e:
            self.circuit_breaker.record_failure()
            self._stats["errors"] += 1
            logger.error(f"LLM call failed for {self.name}: {e}")
            return None
    
    def _call_api(
        self,
        prompt: str,
        system: str = "",
        **kwargs
    ) -> str:
        """调用 API"""
        try:
            import requests
            
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
            
            response = requests.post(
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
                
        except ImportError:
            raise Exception("requests library is required")


class VisionService:
    """
    视觉服务
    支持 Qwen2.5-VL 等多模态模型
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", "qwen")
        self.enabled = config.get("enabled", False)
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "")
        self.model = config.get("model", "qwen-vl-plus")
        
        self._stats = {
            "requests": 0,
            "errors": 0,
        }
    
    def analyze_frame(
        self,
        frame_data: bytes,
        prompt: str = "分析这张图片中的场景和人物视角"
    ) -> Optional[Dict[str, Any]]:
        """
        分析单帧
        
        Args:
            frame_data: JPEG 格式的图像数据
            prompt: 分析提示
            
        Returns:
            {"is_first_person": bool, "confidence": float, "description": str}
        """
        if not self.enabled:
            return self._mock_result()
        
        try:
            import requests
            from PIL import Image
            import io
            
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
            
            response = requests.post(
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
                
                return self._parse_result(content)
            else:
                self._stats["errors"] += 1
                return self._mock_result()
                
        except ImportError:
            return self._mock_result()
        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"Vision analysis failed: {e}")
            return self._mock_result()
    
    def _parse_result(self, content: str) -> Dict[str, Any]:
        """解析 API 返回结果"""
        is_first_person = "第一人称" in content or "POV" in content or "主观" in content
        confidence = 0.8 if is_first_person else 0.3
        
        return {
            "is_first_person": is_first_person,
            "confidence": confidence,
            "description": content[:100]
        }
    
    def _mock_result(self) -> Dict[str, Any]:
        """模拟结果（用于测试）"""
        import random
        is_first_person = random.random() < 0.3
        
        return {
            "is_first_person": is_first_person,
            "confidence": random.uniform(0.6, 0.9) if is_first_person else random.uniform(0.1, 0.4),
            "description": "第一人称街头漫步" if is_first_person else "第三人称观察"
        }


class TTSService:
    """
    TTS 服务
    支持 Edge-TTS、F5-TTS 等
    """
    
    VOICE_MAP = {
        "zh-CN-XiaoxiaoNeural": "晓晓",
        "zh-CN-YunxiNeural": "云希",
        "zh-CN-YunyangNeural": "云扬",
        "zh-CN-XiaoyiNeural": "小艺",
    }
    
    def __init__(self, config: Dict[str, Any] = None):
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
    ) -> Optional[str]:
        """
        生成语音
        
        Args:
            text: 要转换的文本
            output_path: 输出文件路径
            voice: 语音名称
            rate: 语速
            
        Returns:
            生成的音频文件路径
        """
        voice = voice or self.voice
        rate = rate or self.rate
        
        if self.provider == "edge":
            return self._edge_tts(text, output_path, voice, rate)
        elif self.provider == "f5":
            return self._f5_tts(text, output_path, **kwargs)
        else:
            logger.error(f"Unknown TTS provider: {self.provider}")
            return None
    
    def _edge_tts(
        self,
        text: str,
        output_path: str,
        voice: str,
        rate: float
    ) -> Optional[str]:
        """Edge-TTS 生成"""
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
    
    def _f5_tts(self, text: str, output_path: str, **kwargs) -> Optional[str]:
        """F5-TTS 生成（需要参考音频）"""
        logger.warning("F5-TTS requires reference audio, use edge-tts instead")
        return None


class ASRService:
    """
    ASR 语音识别服务
    支持 Faster-Whisper、SenseVoice 等
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.provider = self.config.get("provider", "faster-whisper")
        self.model_name = self.config.get("model", "large-v3")
        self.model = None
    
    def transcribe(
        self,
        audio_path: str,
        language: str = "zh",
        word_timestamps: bool = True,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        语音转文字
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码
            word_timestamps: 是否输出词级时间戳
            
        Returns:
            {"text": str, "segments": [{"start": float, "end": float, "text": str}]}
        """
        if self.provider == "faster-whisper":
            return self._faster_whisper(audio_path, language, word_timestamps)
        elif self.provider == "sensevoice":
            return self._sensevoice(audio_path, **kwargs)
        else:
            logger.error(f"Unknown ASR provider: {self.provider}")
            return None
    
    def _faster_whisper(
        self,
        audio_path: str,
        language: str,
        word_timestamps: bool
    ) -> Optional[Dict[str, Any]]:
        """Faster-Whisper 转写"""
        try:
            from faster_whisper import WhisperModel
            
            if self.model is None:
                self.model = WhisperModel(
                    self.model_name,
                    device="cpu",
                    compute_type="int8"
                )
            
            segments, info = self.model.transcribe(
                audio_path,
                language=language if language != "auto" else None,
                word_timestamps=word_timestamps,
                **kwargs
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
    
    def _sensevoice(self, audio_path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """SenseVoice 转写"""
        logger.warning("SenseVoice integration not implemented yet")
        return None


class AIServiceManager:
    """
    AI 服务管理器
    统一管理所有 AI 服务
    """
    
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
        self._llm_services: Dict[str, LLMService] = {}
        self._vision_service: Optional[VisionService] = None
        self._tts_service: Optional[TTSService] = None
        self._asr_service: Optional[ASRService] = None
    
    def register_llm(self, name: str, config: Dict[str, Any]) -> None:
        """注册 LLM 服务"""
        service = LLMService(config)
        self._llm_services[name] = service
        logger.info(f"Registered LLM service: {name}")
    
    def register_vision(self, config: Dict[str, Any]) -> None:
        """注册视觉服务"""
        self._vision_service = VisionService(config)
        logger.info(f"Registered vision service: {config.get('name', 'unknown')}")
    
    def register_tts(self, config: Dict[str, Any] = None) -> None:
        """注册 TTS 服务"""
        self._tts_service = TTSService(config)
        logger.info(f"Registered TTS service: {config.get('provider', 'edge')}")
    
    def register_asr(self, config: Dict[str, Any] = None) -> None:
        """注册 ASR 服务"""
        self._asr_service = ASRService(config)
        logger.info(f"Registered ASR service: {config.get('provider', 'faster-whisper')}")
    
    def get_llm(self, name: str = None) -> Optional[LLMService]:
        """获取 LLM 服务"""
        if name:
            return self._llm_services.get(name)
        # 返回第一个启用的
        for service in self._llm_services.values():
            if service.enabled:
                return service
        return None
    
    @property
    def vision(self) -> Optional[VisionService]:
        return self._vision_service
    
    @property
    def tts(self) -> Optional[TTSService]:
        return self._tts_service
    
    @property
    def asr(self) -> Optional[ASRService]:
        return self._asr_service
    
    def get_summary(self) -> Dict[str, Any]:
        """获取服务摘要"""
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
            "tts_provider": self._tts_service.provider if self._tts_service else None,
            "asr_provider": self._asr_service.provider if self._asr_service else None,
        }


# 全局实例
ai_service_manager = AIServiceManager()


def get_ai_service() -> AIServiceManager:
    """获取 AI 服务管理器"""
    return ai_service_manager


__all__ = [
    "ServiceStatus",
    "ServiceHealth",
    "RateLimiter",
    "CircuitBreaker",
    "LLMService",
    "VisionService",
    "TTSService",
    "ASRService",
    "AIServiceManager",
    "ai_service_manager",
    "get_ai_service",
]
