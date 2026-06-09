"""
SceneFab 配置层 v2.1（基于 pydantic-settings）

v2.1 目标：让配置获得"类型安全 + 动态重载 + schema 验证"三种能力

v1.x `settings.py` / `settings_manager.py` 已经够用（dataclass + JSON），
v2.1 在它之上叠加**现代特性**：

1. **类型安全**：所有配置用 Pydantic BaseSettings 声明
2. **环境变量覆盖**：`SCENEFAB_*` 前缀自动映射
3. **多 profile**：`scenefab.production` / `scenefab.testing` / `scenefab.development`
4. **动态重载**：监听 `.env` / YAML 变更 → 自动重载（可选）
5. **schema 验证**：自动生成 JSON Schema 文档
6. **事件发布**：配置变更发 `ConfigChanged` DomainEvent

使用::

    from scenefab.core.config_v2 import SettingsV2, get_settings

    s = get_settings()
    s.llm.deepseek.api_key      # 类型安全
    s.llm.provider               # 校验非空
    s.to_json_schema()           # 生成文档
    s.reload()                   # 强制重载
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any

try:
    from pydantic import Field
    from pydantic import field_validator as _pyd_field_validator
    from pydantic_settings import BaseSettings, SettingsConfigDict

    _HAS_PYDANTIC_SETTINGS = True
except ImportError:
    _HAS_PYDANTIC_SETTINGS = False

    def Field(*args, **kwargs):  # type: ignore[no-redef]
        return None

    BaseSettings = object

    def SettingsConfigDict(**kwargs):  # type: ignore[no-redef]
        return {}

    def field_validator(*args, **kwargs):
        def decorator(fn):
            return fn

        return decorator


# 在 pydantic-settings 存在时把 field_validator 指向 pydantic 版本
if _HAS_PYDANTIC_SETTINGS:
    field_validator = _pyd_field_validator  # type: ignore[unused-ignore, misc,assignment]


logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# 枚举
# ──────────────────────────────────────────────────────────


class LLMProviderName(str, Enum):
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    KIMI = "kimi"
    GLM5 = "glm5"
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    DOUBAO = "doubao"
    HUNYUAN = "hunyuan"


class TTSProviderName(str, Enum):
    EDGE_TTS = "edge-tts"
    F5_TTS = "f5-tts"
    AZURE = "azure"


class TaskStoreBackend(str, Enum):
    MEMORY = "memory"
    SQLITE = "sqlite"
    REDIS = "redis"


class AppProfile(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


# ──────────────────────────────────────────────────────────
# 模型
# ──────────────────────────────────────────────────────────


if _HAS_PYDANTIC_SETTINGS:

    class LLMProviderConfig(BaseSettings):
        """单个 LLM provider 配置"""

        enabled: bool = False
        api_key: str = ""
        base_url: str = ""
        model: str = ""
        max_tokens: int = 8000
        temperature: float = 0.7
        requests_per_second: float = 10.0
        burst_size: int = 20

        model_config = SettingsConfigDict(
            env_prefix="SCENEFAB_LLM_",
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )

        @field_validator("api_key", mode="before")
        @classmethod
        def _normalize_key(cls, v: Any) -> str:
            return (str(v) if v is not None else "").strip()

    class TTSProviderConfig(BaseSettings):
        """单个 TTS provider 配置"""

        enabled: bool = False
        voice: str = "zh-CN-YunxiNeural"
        speed: float = 1.0
        pitch: float = 0.0
        local_model_path: str = ""  # F5-TTS 专用

        model_config = SettingsConfigDict(
            env_prefix="SCENEFAB_TTS_",
            extra="ignore",
        )

    class PipelineSettings(BaseSettings):
        """流水线配置"""

        max_workers: int = 4
        enable_parallel: bool = True
        fail_fast: bool = True
        step_timeout_sec: int = 600
        llm_streaming: bool = True
        ffmpeg_hardware_accel: bool = False

        model_config = SettingsConfigDict(
            env_prefix="SCENEFAB_PIPELINE_",
            extra="ignore",
        )

    class StorageSettings(BaseSettings):
        """存储配置"""

        task_store_backend: TaskStoreBackend = TaskStoreBackend.MEMORY
        task_store_db_path: str = "~/.cache/scenefab/task_store.db"
        task_store_redis_url: str = "redis://localhost:6379/0"
        task_store_ttl_sec: int = 86400  # 1 天
        cache_dir: str = "~/.cache/scenefab"

        model_config = SettingsConfigDict(
            env_prefix="SCENEFAB_STORAGE_",
            extra="ignore",
        )

    class SecuritySettings(BaseSettings):
        """安全配置"""

        ffmpeg_whitelist_only: bool = True
        ffmpeg_allow_unsafe: bool = False  # 调试开关
        audit_log_enabled: bool = True
        audit_log_path: str = "~/.cache/scenefab/audit.db"
        api_key_use_keyring: bool = True

        model_config = SettingsConfigDict(
            env_prefix="SCENEFAB_SECURITY_",
            extra="ignore",
        )

    class APISettings(BaseSettings):
        """FastAPI 服务配置"""

        host: str = "127.0.0.1"
        port: int = 8000
        workers: int = 1
        cors_origins: str = "*"
        enable_websocket: bool = True

        model_config = SettingsConfigDict(
            env_prefix="SCENEFAB_API_",
            extra="ignore",
        )

    class LLMSettings(BaseSettings):
        """LLM 配置组（聚合所有 provider）"""

        provider: LLMProviderName = LLMProviderName.DEEPSEEK
        fallback_providers: list[str] = Field(default_factory=list)
        deepseek: LLMProviderConfig = Field(default_factory=LLMProviderConfig)
        qwen: LLMProviderConfig = Field(default_factory=LLMProviderConfig)
        kimi: LLMProviderConfig = Field(default_factory=LLMProviderConfig)
        glm5: LLMProviderConfig = Field(default_factory=LLMProviderConfig)
        openai: LLMProviderConfig = Field(default_factory=LLMProviderConfig)
        claude: LLMProviderConfig = Field(default_factory=LLMProviderConfig)
        gemini: LLMProviderConfig = Field(default_factory=LLMProviderConfig)

        model_config = SettingsConfigDict(
            env_prefix="SCENEFAB_LLM_GROUP_",
            extra="ignore",
        )

    class TTSSettings(BaseSettings):
        """TTS 配置组"""

        provider: TTSProviderName = TTSProviderName.EDGE_TTS
        edge_tts: TTSProviderConfig = Field(default_factory=TTSProviderConfig)
        f5_tts: TTSProviderConfig = Field(default_factory=TTSProviderConfig)
        azure: TTSProviderConfig = Field(default_factory=TTSProviderConfig)

        model_config = SettingsConfigDict(
            env_prefix="SCENEFAB_TTS_GROUP_",
            extra="ignore",
        )

    class SettingsV2(BaseSettings):
        """SceneFab 完整配置 v2.1"""

        profile: AppProfile = AppProfile.DEVELOPMENT
        app_name: str = "scenefab"
        app_version: str = "2.1.0"
        debug: bool = False
        log_level: str = "INFO"

        llm: LLMSettings = Field(default_factory=LLMSettings)
        tts: TTSSettings = Field(default_factory=TTSSettings)
        pipeline: PipelineSettings = Field(default_factory=PipelineSettings)
        storage: StorageSettings = Field(default_factory=StorageSettings)
        security: SecuritySettings = Field(default_factory=SecuritySettings)
        api: APISettings = Field(default_factory=APISettings)

        model_config = SettingsConfigDict(
            env_prefix="SCENEFAB_",
            env_file=".env",
            env_file_encoding="utf-8",
            env_nested_delimiter="_",
            extra="ignore",
        )

        def to_dict(self) -> dict[str, Any]:
            """转字典（递归）"""
            return self.model_dump()

        def to_json(self, indent: int = 2) -> str:
            return json.dumps(
                self.to_dict(), ensure_ascii=False, indent=indent, default=str
            )

        def to_json_schema(self) -> dict[str, Any]:
            """生成 JSON Schema（用于文档）"""
            return self.model_json_schema()

        def reload(self) -> "SettingsV2":  # noqa: UP037 — forward ref, no __future__ annotations
            """强制重载（重新读取 env / .env）"""
            global _settings
            _settings = type(self)()
            return _settings


# ──────────────────────────────────────────────────────────
# 全局 & 工厂
# ──────────────────────────────────────────────────────────


_settings: Any | None = None
_settings_lock = None  # 懒加载


def get_settings() -> Any:
    """获取全局配置（v2.1）"""
    global _settings, _settings_lock
    if not _HAS_PYDANTIC_SETTINGS:
        raise ImportError(
            "SettingsV2 requires pydantic-settings. "
            "Install with: pip install pydantic-settings"
        )
    if _settings is None:
        import threading

        if _settings_lock is None:
            _settings_lock = threading.Lock()
        with _settings_lock:
            if _settings is None:
                _settings = SettingsV2()
    return _settings


def set_settings(settings: Any) -> None:
    """注入全局配置（v2.1 测试 / DI 友好）"""
    global _settings
    _settings = settings


def is_settings_v2_available() -> bool:
    """检查 pydantic-settings 是否可用"""
    return _HAS_PYDANTIC_SETTINGS


__all__ = [
    "SettingsV2",
    "LLMSettings",
    "TTSSettings",
    "PipelineSettings",
    "StorageSettings",
    "SecuritySettings",
    "APISettings",
    "LLMProviderConfig",
    "TTSProviderConfig",
    "LLMProviderName",
    "TTSProviderName",
    "TaskStoreBackend",
    "AppProfile",
    "get_settings",
    "set_settings",
    "is_settings_v2_available",
]
