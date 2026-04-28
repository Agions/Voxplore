"""
AI Provider Registry
AI Provider 注册中心 - 替代硬编码的 Provider 列表
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum


class ProviderType(Enum):
    """Provider 类型"""
    VIDEO_ANALYSIS = "video_analysis"   # 视频理解模型
    SCRIPT_LLM = "script_llm"           # 脚本生成模型
    VOICE_TTS = "voice_tts"             # 语音合成


@dataclass
class ProviderConfig:
    """Provider 配置"""
    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str = ""
    enabled: bool = True
    timeout: int = 120
    max_retries: int = 3
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderMetadata:
    """Provider 元数据"""
    id: str
    name: str
    provider_type: ProviderType
    description: str
    capabilities: List[str]
    models: List[str]
    requires_api_key: bool
    is_local: bool = False
    homepage: Optional[str] = None


class BaseLLMAdapter(ABC):
    """
    LLM Adapter 基类

    所有 AI Provider 通过 Adapter 模式接入:
    - 统一的接口
    - 可插拔
    - 支持多 Provider 负载均衡
    """

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._client: Optional[Any] = None

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Provider 唯一标识"""
        ...

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Provider 类型"""
        ...

    @property
    def metadata(self) -> ProviderMetadata:
        """Provider 元数据"""
        return ProviderMetadata(
            id=self.provider_id,
            name=self.config.name,
            provider_type=self.provider_type,
            description="",
            capabilities=[],
            models=[self.config.model] if self.config.model else [],
            requires_api_key=bool(self.config.api_key),
            is_local=self.config.base_url and "localhost" in self.config.base_url
        )

    @abstractmethod
    async def initialize(self) -> None:
        """初始化 Client"""
        ...

    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> str:
        """同步补全"""
        ...

    @abstractmethod
    async def complete_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """流式补全"""
        ...

    @abstractmethod
    async def close(self) -> None:
        """关闭连接"""
        ...

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, *args):
        await self.close()


class VideoAnalysisAdapter(BaseLLMAdapter):
    """视频理解 Adapter - Qwen2.5-VL 等"""
    provider_type = ProviderType.VIDEO_ANALYSIS

    @abstractmethod
    async def analyze_video(self, video_path: str, frames: List[float]) -> Dict[str, Any]:
        """
        分析视频

        Returns:
            {
                "scenes": [...],
                "keyframes": [...],
                "transcriptions": [...]
            }
        """
        ...


class ScriptLLMAdapter(BaseLLMAdapter):
    """脚本生成 Adapter - DeepSeek-V4, Qwen-Plus 等"""
    provider_type = ProviderType.SCRIPT_LLM

    @abstractmethod
    async def generate_script(
        self,
        context: str,
        emotion: str,
        style: str,
        max_tokens: Optional[int] = None,
    ) -> str:
        """生成解说脚本"""
        ...

    @abstractmethod
    async def generate_script_stream(
        self,
        context: str,
        emotion: str,
        style: str,
    ) -> AsyncIterator[str]:
        """流式生成脚本"""
        ...


class TTSAdapter(BaseLLMAdapter):
    """语音合成 Adapter - Edge-TTS, F5-TTS 等"""
    provider_type = ProviderType.VOICE_TTS

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """
        合成语音

        Args:
            text: 要合成的文本
            voice_id: 音色 ID
            output_path: 输出文件路径

        Returns:
            生成的音频文件路径
        """
        ...

    @abstractmethod
    async def list_voices(self, language: Optional[str] = None) -> List[Dict[str, str]]:
        """列出可用音色"""
        ...
