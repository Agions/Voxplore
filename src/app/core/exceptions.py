from enum import Enum
from typing import Any


class ErrorCode(Enum):
    LLM_API_ERROR = "LLM001"
    LLM_INVALID_REQUEST = "LLM002"
    LLM_RATE_LIMIT = "LLM003"
    LLM_CONNECTION_FAILED = "LLM004"
    LLM_KEY_MISSING = "LLM005"
    LLM_INVALID_RESPONSE = "LLM006"

    CONFIG_MISSING = "CFG001"
    CONFIG_INVALID = "CFG002"

    FILE_NOT_FOUND = "FILE001"
    FILE_READ_ERROR = "FILE002"
    FILE_WRITE_ERROR = "FILE003"

    VIDEO_PROCESS_ERROR = "VID001"
    VIDEO_FORMAT_ERROR = "VID002"

    TTS_ERROR = "TTS001"

    NETWORK_ERROR = "NET001"

    SYSTEM_ERROR = "SYS001"

    UNKNOWN_ERROR = "UNK001"


class SceneFabError(Exception):
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
            result += f"\n{self.hint}"
        if self.details:
            result += f"\n{self.details}"
        return result


class ConfigError(SceneFabError):
    def __init__(self, message: str, key: str | None = None):
        code = (
            ErrorCode.CONFIG_MISSING
            if "unset" in message.lower() or "未设置" in message
            else ErrorCode.CONFIG_INVALID
        )
        hint = "Please check config/llm.yaml" if key else None
        super().__init__(
            code=code, message=message, details={"key": key} if key else None, hint=hint
        )


class FileError(SceneFabError):
    def __init__(self, message: str, path: str | None = None, operation: str | None = None):
        code = ErrorCode.FILE_NOT_FOUND
        hint = None
        if "read" in message.lower():
            code = ErrorCode.FILE_READ_ERROR
        elif "write" in message.lower():
            code = ErrorCode.FILE_WRITE_ERROR
        if path:
            hint = f"Check path: {path}"
        super().__init__(
            code=code,
            message=message,
            details={"path": path, "operation": operation} if (path or operation) else None,
            hint=hint,
        )


class VideoError(SceneFabError):
    def __init__(self, message: str, video_path: str | None = None, format: str | None = None):
        if format and ("unsupported" in message.lower() or "不支持" in message):
            code = ErrorCode.VIDEO_FORMAT_ERROR
        else:
            code = ErrorCode.VIDEO_PROCESS_ERROR
        hint = "Ensure FFmpeg is installed" if "ffmpeg" in message.lower() else None
        details: dict[str, Any] = {}
        if video_path:
            details["video_path"] = video_path
        if format:
            details["format"] = format
        super().__init__(code=code, message=message, details=details or None, hint=hint)


class TTSError(SceneFabError):
    def __init__(self, message: str, voice: str | None = None):
        hint = "Check TTS API config" if "api" in message.lower() else None
        super().__init__(
            code=ErrorCode.TTS_ERROR,
            message=message,
            details={"voice": voice} if voice else None,
            hint=hint,
        )


class NetworkError(SceneFabError):
    def __init__(self, message: str, url: str | None = None):
        hint = "Check network connection" if "connection" in message.lower() else None
        super().__init__(
            code=ErrorCode.NETWORK_ERROR,
            message=message,
            details={"url": url} if url else None,
            hint=hint,
        )


class ProviderError(SceneFabError):
    def __init__(self, message: str, provider: str | None = None, model: str | None = None):
        details: dict[str, Any] = {}
        if provider:
            details["provider"] = provider
        if model:
            details["model"] = model
        super().__init__(
            code=ErrorCode.LLM_API_ERROR,
            message=message,
            details=details or None,
            hint="Check Provider config and API key",
        )


class RateLimitError(ProviderError):
    def __init__(self, message: str = "API rate limit", provider: str | None = None, retry_after: float | None = None):
        details: dict[str, Any] = {}
        if retry_after is not None:
            details["retry_after"] = retry_after
        if provider:
            details["provider"] = provider
        super().__init__(message=message, provider=provider)


class CircuitOpenError(ProviderError):
    def __init__(self, message: str = "Circuit breaker is OPEN", provider: str | None = None, failure_count: int | None = None):
        details: dict[str, Any] = {}
        if failure_count is not None:
            details["failure_count"] = failure_count
        if provider:
            details["provider"] = provider
        super().__init__(message=message, provider=provider)


class ExportError(SceneFabError):
    def __init__(self, message: str, format: str | None = None, details: dict[str, Any] | None = None):
        hint = "Ensure FFmpeg is installed" if "ffmpeg" in message.lower() else None
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
    def __init__(self, message: str, project_id: str | None = None, operation: str | None = None):
        hint = None
        if "not found" in message.lower() or "不存在" in message:
            hint = "Check project path"
        elif "load" in message.lower() or "加载" in message:
            hint = "Check if project file is corrupted"
        elif "save" in message.lower() or "保存" in message:
            hint = "Check disk space and write permissions"
        super().__init__(
            code=ErrorCode.FILE_NOT_FOUND,
            message=message,
            details={
                "project_id": project_id,
                "operation": operation,
            } if project_id or operation else None,
            hint=hint,
        )


class ServiceError(SceneFabError):
    def __init__(self, message: str, code: ErrorCode = ErrorCode.SYSTEM_ERROR, details: dict[str, Any] | None = None):
        super().__init__(code=code, message=message, details=details)


class ServiceNotFoundError(ServiceError):
    def __init__(self, service_name: str):
        super().__init__(
            message=f"Service not registered: {service_name}",
            code=ErrorCode.SYSTEM_ERROR,
            details={"service": service_name},
        )


class ServiceDependencyError(ServiceError):
    def __init__(self, message: str, service: str | None = None, dependency: str | None = None):
        details: dict[str, Any] = {}
        if service:
            details["service"] = service
        if dependency:
            details["dependency"] = dependency
        super().__init__(message=message, code=ErrorCode.SYSTEM_ERROR, details=details or None)


class ServiceInitializationError(ServiceError):
    def __init__(self, service: str, reason: str):
        super().__init__(
            message=f"Service init failed [{service}]: {reason}",
            code=ErrorCode.SYSTEM_ERROR,
            details={"service": service, "reason": reason},
        )


def format_error_message(error: Exception) -> str:
    if isinstance(error, SceneFabError):
        return str(error)
    error_name = type(error).__name__
    error_message = str(error)
    result = f"{error_name}"
    if error_message:
        result += f"\n{error_message}"
    if "connection" in error_message.lower():
        result += "\nCheck network connection"
    elif "file" in error_message.lower():
        result += "\nCheck file path and permissions"
    else:
        result += "\nCheck logs or contact support"
    return result


def get_error_hint(code: ErrorCode) -> str:
    hints = {
        ErrorCode.LLM_API_ERROR: "LLM API call failed, retry later",
        ErrorCode.LLM_INVALID_REQUEST: "Invalid LLM request format",
        ErrorCode.LLM_RATE_LIMIT: "API rate limit exceeded",
        ErrorCode.LLM_CONNECTION_FAILED: "Cannot connect to LLM service",
        ErrorCode.LLM_KEY_MISSING: "LLM API key not set",
        ErrorCode.LLM_INVALID_RESPONSE: "Invalid LLM response format",
        ErrorCode.CONFIG_MISSING: "Missing configuration",
        ErrorCode.CONFIG_INVALID: "Invalid configuration",
        ErrorCode.FILE_NOT_FOUND: "File not found",
        ErrorCode.FILE_READ_ERROR: "File read failed",
        ErrorCode.FILE_WRITE_ERROR: "File write failed",
        ErrorCode.VIDEO_PROCESS_ERROR: "Video processing failed",
        ErrorCode.VIDEO_FORMAT_ERROR: "Unsupported video format",
        ErrorCode.TTS_ERROR: "TTS failed",
        ErrorCode.NETWORK_ERROR: "Network connection failed",
        ErrorCode.UNKNOWN_ERROR: "Unknown error",
    }
    return hints.get(code, "Check logs for details")


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
    "get_error_hint",
]
