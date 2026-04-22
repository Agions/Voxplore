#!/usr/bin/env python3
"""测试异常模块"""


from app.core.exceptions import (
    ErrorCode,
    VoxploreError,
    LLMError,
    ConfigError,
    FileError,
    VideoError,
    NetworkError,
)


class TestErrorCode:
    """测试错误代码枚举"""

    def test_llm_error_codes(self):
        """测试 LLM 错误代码"""
        assert ErrorCode.LLM_API_ERROR.value == "LLM001"
        assert ErrorCode.LLM_INVALID_REQUEST.value == "LLM002"
        assert ErrorCode.LLM_RATE_LIMIT.value == "LLM003"
        assert ErrorCode.LLM_CONNECTION_FAILED.value == "LLM004"
        assert ErrorCode.LLM_KEY_MISSING.value == "LLM005"

    def test_config_error_codes(self):
        """测试配置错误代码"""
        assert ErrorCode.CONFIG_MISSING.value == "CFG001"
        assert ErrorCode.CONFIG_INVALID.value == "CFG002"

    def test_file_error_codes(self):
        """测试文件错误代码"""
        assert ErrorCode.FILE_NOT_FOUND.value == "FILE001"
        assert ErrorCode.FILE_READ_ERROR.value == "FILE002"
        assert ErrorCode.FILE_WRITE_ERROR.value == "FILE003"


class TestVoxploreError:
    """测试基础异常类"""

    def test_basic_creation(self):
        """测试基本创建"""
        err = VoxploreError(
            code=ErrorCode.UNKNOWN_ERROR,
            message="测试错误"
        )
        
        assert err.code == ErrorCode.UNKNOWN_ERROR
        assert err.message == "测试错误"
        assert err.details == {}
        assert err.hint is None

    def test_with_details(self):
        """测试带详情的错误"""
        err = VoxploreError(
            code=ErrorCode.FILE_NOT_FOUND,
            message="文件未找到",
            details={"path": "/test/file.mp4"},
            hint="检查文件路径"
        )
        
        assert err.details["path"] == "/test/file.mp4"
        assert err.hint == "检查文件路径"

    def test_str_representation(self):
        """测试字符串表示"""
        err = VoxploreError(
            code=ErrorCode.CONFIG_MISSING,
            message="配置缺失"
        )
        
        err_str = str(err)
        assert "CFG001" in err_str
        assert "配置缺失" in err_str


class TestLLMError:
    """测试 LLM 异常"""

    def test_rate_limit_detection(self):
        """测试速率限制检测"""
        err = LLMError("Rate limit exceeded")
        
        assert err.code == ErrorCode.LLM_RATE_LIMIT
        assert err.hint is not None
        assert "稍后重试" in err.hint

    def test_invalid_key_detection(self):
        """测试无效密钥检测"""
        err = LLMError("Invalid API key")
        
        assert err.code == ErrorCode.LLM_KEY_MISSING

    def test_connection_error_detection(self):
        """测试连接错误检测"""
        err = LLMError("Connection failed")
        
        assert err.code == ErrorCode.LLM_CONNECTION_FAILED

    def test_with_provider_info(self):
        """测试带提供商信息"""
        err = LLMError(
            "API error",
            provider="openai",
            model="gpt-4"
        )
        
        assert err.details["provider"] == "openai"
        assert err.details["model"] == "gpt-4"


class TestConfigError:
    """测试配置异常"""

    def test_missing_config(self):
        """测试缺失配置"""
        err = ConfigError("API Key 未设置", key="openai_key")
        
        assert err.code == ErrorCode.CONFIG_MISSING
        assert err.details["key"] == "openai_key"

    def test_invalid_config(self):
        """测试无效配置"""
        err = ConfigError("配置格式错误")
        
        assert err.code == ErrorCode.CONFIG_INVALID


class TestFileError:
    """测试文件异常"""

    def test_with_path(self):
        """测试带路径的文件错误"""
        err = FileError(
            "文件读取失败",
            path="/test/video.mp4",
            operation="read"
        )
        
        assert err.details["path"] == "/test/video.mp4"
        assert err.details["operation"] == "read"


class TestVideoError:
    """测试视频异常"""

    def test_format_error(self):
        """测试格式错误"""
        err = VideoError("不支持的视频格式", format="avi")
        
        assert err.code == ErrorCode.VIDEO_FORMAT_ERROR
        assert err.details["format"] == "avi"


class TestNetworkError:
    """测试网络异常"""

    def test_basic_creation(self):
        """测试基本创建"""
        err = NetworkError("网络连接超时")
        
        assert err.code == ErrorCode.NETWORK_ERROR
