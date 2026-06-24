#!/usr/bin/env python3

"""
SceneFab 错误处理和异常模块
提供自定义异常和错误处理功能
"""

from enum import Enum
from typing import Any


class ErrorCode(Enum):
    """错误代码枚举"""

    # LLM 相关错误
    LLM_API_ERROR = "LLM001"
    LLM_INVALID_REQUEST = "LLM002"
    LLM_RATE_LIMIT = "LLM003"
    LLM_CONNECTION_FAILED = "LLM004"
    LLM_KEY_MISSING = "LLM005"
    LLM_INVALID_RESPONSE = "LLM006"

    # 配置相关错误
    CONFIG_MISSING = "CFG001"
    CONFIG_INVALID = "CFG002"

    # 文件操作错误
    FILE_NOT_FOUND = "FILE001"
    FILE_READ_ERROR = "FILE002"
    FILE_WRITE_ERROR = "FILE003"

    # 视频处理错误
    VIDEO_PROCESS_ERROR = "VID001"
    VIDEO_FORMAT_ERROR = "VID002"

    # 语音合成错误
    TTS_ERROR = "TTS001"

    # 网络错误
    NETWORK_ERROR = "NET001"

    # 系统错误
    SYSTEM_ERROR = "SYS001"

    # 未知错误
    UNKNOWN_ERROR = "UNK001"


class SceneFabError(Exception):
    """SceneFab 基础异常类"""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
        hint: str | None = None,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.hint = hint

        super().__init__(f"[{code.value}] {message}")

    def __str__(self) -> str:
        result = f"[{self.code.value}] {self.message}"

        if self.hint:
            result += f"\n💡 提示: {self.hint}"

        if self.details:
            result += f"\n📋 详情: {self.details}"

        return result


class ConfigError(SceneFabError):
    """配置错误"""

    def __init__(self, message: str, key: str | None = None):
        code = (
            ErrorCode.CONFIG_MISSING
            if "未设置" in message
            else ErrorCode.CONFIG_INVALID
        )
        hint = "请检查配置文件 config/llm.yaml" if key else None

        super().__init__(
            code=code, message=message, details={"key": key} if key else None, hint=hint
        )


class FileError(SceneFabError):
    """文件操作错误"""

    def __init__(
        self, message: str, path: str | None = None, operation: str | None = None
    ):
        code = ErrorCode.FILE_NOT_FOUND
        hint = None

        if "read" in message.lower():
            code = ErrorCode.FILE_READ_ERROR
        elif "write" in message.lower():
            code = ErrorCode.FILE_WRITE_ERROR

        if path:
            hint = f"请检查文件路径: {path}"

        super().__init__(
            code=code,
            message=message,
            details={"path": path, "operation": operation}
            if (path or operation)
            else None,
            hint=hint,
        )


class VideoError(SceneFabError):
    """视频处理错误"""

    def __init__(
        self,
        message: str,
        video_path: str | None = None,
        format: str | None = None,
    ):
        # Auto-detect format error from message or format param
        if format and ("不支持" in message or "unsupported" in message.lower()):
            code = ErrorCode.VIDEO_FORMAT_ERROR
        else:
            code = ErrorCode.VIDEO_PROCESS_ERROR

        hint = "请确保 FFmpeg 已正确安装" if "ffmpeg" in message.lower() else None

        details: dict[str, Any] = {}
        if video_path:
            details["video_path"] = video_path
        if format:
            details["format"] = format

        super().__init__(code=code, message=message, details=details or None, hint=hint)


class TTSError(SceneFabError):
    """语音合成错误"""

    def __init__(self, message: str, voice: str | None = None):
        hint = "请检查 TTS API 配置" if "api" in message.lower() else None

        super().__init__(
            code=ErrorCode.TTS_ERROR,
            message=message,
            details={"voice": voice} if voice else None,
            hint=hint,
        )


class NetworkError(SceneFabError):
    """网络错误"""

    def __init__(self, message: str, url: str | None = None):
        hint = "请检查网络连接" if "connection" in message.lower() else None

        super().__init__(
            code=ErrorCode.NETWORK_ERROR,
            message=message,
            details={"url": url} if url else None,
            hint=hint,
        )


class ProviderError(SceneFabError):
    """AI Provider 错误"""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        model: str | None = None,
    ):
        code = ErrorCode.LLM_API_ERROR
        hint = "请检查 Provider 配置和 API 密钥"

        details: dict[str, Any] = {}
        if provider:
            details["provider"] = provider
        if model:
            details["model"] = model

        super().__init__(
            code=code,
            message=message,
            details=details or None,
            hint=hint,
        )


class RateLimitError(ProviderError):
    """API 速率限制错误"""

    def __init__(
        self,
        message: str = "API 速率限制",
        provider: str | None = None,
        retry_after: float | None = None,
    ):
        details: dict[str, Any] = {"retry_after": retry_after} if retry_after else {}
        if provider:
            details["provider"] = provider

        super().__init__(  # type: ignore[call-arg]
            message=message,
            provider=provider,
            details=details,
        )


class CircuitOpenError(ProviderError):
    """熔断器打开错误"""

    def __init__(
        self,
        message: str = "服务熔断器已打开",
        provider: str | None = None,
        failure_count: int | None = None,
    ):
        details: dict[str, Any] = {}
        if failure_count is not None:
            details["failure_count"] = failure_count
        if provider:
            details["provider"] = provider

        super().__init__(  # type: ignore[call-arg]
            message=message,
            provider=provider,
            details=details,
        )


class ExportError(SceneFabError):
    """导出错误"""

    def __init__(
        self,
        message: str,
        format: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        hint = "请检查 FFmpeg 是否正确安装" if "ffmpeg" in message.lower() else None

        export_details: dict[str, Any] = dict(details or {})
        if format:
            export_details["format"] = format

        super().__init__(
            code=ErrorCode.VIDEO_PROCESS_ERROR,
            message=message,
            details=export_details or None,
            hint=hint,
        )


class ProjectError(SceneFabError):
    """项目管理错误"""

    def __init__(
        self,
        message: str,
        project_id: str | None = None,
        operation: str | None = None,
    ):
        hint = None
        code = ErrorCode.FILE_NOT_FOUND

        if "not found" in message.lower() or "不存在" in message:
            code = ErrorCode.FILE_NOT_FOUND
            hint = "请检查项目路径是否正确"
        elif "load" in message.lower() or "加载" in message:
            hint = "请检查项目文件是否损坏"
        elif "save" in message.lower() or "保存" in message:
            hint = "请检查磁盘空间和写入权限"

        super().__init__(
            code=code,
            message=message,
            details={
                "project_id": project_id,
                "operation": operation,
            }
            if project_id or operation
            else None,
            hint=hint,
        )


# =============================================================================
# 服务层错误（从 registry_models.py 迁移）
# =============================================================================
class ServiceError(SceneFabError):
    """服务层错误基类"""

    pass


class ServiceNotFoundError(ServiceError):
    """服务未找到错误"""

    def __init__(self, service_name: str):
        super().__init__(
            code=ErrorCode.SYSTEM_ERROR,
            message=f"服务未注册: {service_name}",
            details={"service": service_name},
            hint="请检查服务是否已注册",
        )


class ServiceDependencyError(ServiceError):
    """服务依赖错误"""

    def __init__(
        self,
        message: str,
        service: str | None = None,
        dependency: str | None = None,
    ):
        details: dict[str, Any] = {}
        if service:
            details["service"] = service
        if dependency:
            details["dependency"] = dependency

        super().__init__(
            code=ErrorCode.SYSTEM_ERROR,
            message=message,
            details=details or None,
        )


class ServiceInitializationError(ServiceError):
    """服务初始化错误"""

    def __init__(self, service: str, reason: str):
        super().__init__(
            code=ErrorCode.SYSTEM_ERROR,
            message=f"服务初始化失败 [{service}]: {reason}",
            details={"service": service, "reason": reason},
        )


class ServiceTimeoutError(ServiceError):
    """服务超时错误"""

    def __init__(self, service: str, timeout: float):
        super().__init__(
            code=ErrorCode.SYSTEM_ERROR,
            message=f"服务响应超时 [{service}]: {timeout}s",
            details={"service": service, "timeout": timeout},
        )


def format_error_message(error: Exception) -> str:
    """格式化错误消息，用于用户界面显示"""

    if isinstance(error, SceneFabError):
        return str(error)

    # 处理其他异常
    error_name = type(error).__name__
    error_message = str(error)

    result = f"❌ {error_name}"

    if error_message:
        result += f"\n{error_message}"

    # 添加通用提示
    if "connection" in error_message.lower():
        result += "\n💡 请检查网络连接"
    elif "file" in error_message.lower():
        result += "\n💡 请检查文件路径和权限"
    else:
        result += "\n💡 如问题持续，请查看日志或联系技术支持"

    return result


def get_error_hint(code: ErrorCode) -> str:
    """根据错误代码获取提示信息"""

    hints = {
        ErrorCode.LLM_API_ERROR: "LLM API 调用失败，请稍后重试",
        ErrorCode.LLM_INVALID_REQUEST: "LLM 请求格式错误，请检查参数",
        ErrorCode.LLM_RATE_LIMIT: "API 调用频率超限，请稍后重试",
        ErrorCode.LLM_CONNECTION_FAILED: "无法连接到 LLM 服务，请检查网络",
        ErrorCode.LLM_KEY_MISSING: "LLM API 密钥未设置，请在配置中添加",
        ErrorCode.LLM_INVALID_RESPONSE: "LLM 返回的数据格式错误",
        ErrorCode.CONFIG_MISSING: "缺少必要配置，请检查配置文件",
        ErrorCode.CONFIG_INVALID: "配置格式错误，请检查配置文件",
        ErrorCode.FILE_NOT_FOUND: "文件不存在，请检查路径",
        ErrorCode.FILE_READ_ERROR: "文件读取失败，请检查权限",
        ErrorCode.FILE_WRITE_ERROR: "文件写入失败，请检查权限和磁盘空间",
        ErrorCode.VIDEO_PROCESS_ERROR: "视频处理失败，请确保 FFmpeg 已正确安装",
        ErrorCode.VIDEO_FORMAT_ERROR: "视频格式不支持",
        ErrorCode.TTS_ERROR: "语音合成失败，请检查 TTS 配置",
        ErrorCode.NETWORK_ERROR: "网络连接失败，请检查网络设置",
        ErrorCode.UNKNOWN_ERROR: "未知错误，请查看日志获取更多信息",
    }

    return hints.get(code, "请查看日志获取更多信息")


__all__ = [
    "ErrorCode",
    "SceneFabError",
    "ConfigError",
    "FileError",
    "VideoError",
    "TTSError",
    "NetworkError",
    "ProviderError",
    "RateLimitError",
    "CircuitOpenError",
    "ExportError",
    "ProjectError",
    "ServiceError",
    "ServiceNotFoundError",
    "ServiceDependencyError",
    "ServiceInitializationError",
    "ServiceTimeoutError",
    "get_error_hint",
]
