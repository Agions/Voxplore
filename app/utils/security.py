"""
安全工具模块
提供安全验证、输入清理、命令执行等功能
彻底杜绝常见安全漏洞
"""

import os
import re
import subprocess
from typing import Optional, List, Any, Dict
from pathlib import Path
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# ============================================
# 常量定义
# ============================================

# 允许的文件扩展名白名单
ALLOWED_VIDEO_EXTENSIONS = {
    '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm',
    '.m4v', '.mpg', '.mpeg', '.3gp', '.3g2', '.ts', '.mts'
}

ALLOWED_IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'
}

ALLOWED_AUDIO_EXTENSIONS = {
    '.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.wma'
}

ALLOWED_DOCUMENT_EXTENSIONS = {
    '.txt', '.md', '.json', '.yaml', '.yml', '.xml', '.srt', '.ass', '.vtt', '.lrc'
}

# 危险路径模式
DANGEROUS_PATH_PATTERNS = [
    r'\.\.',           # 路径穿越
    r'^/etc',
    r'^/proc',
    r'^/sys',
    r'^/root',
    r'Windows/System32',
    r'Windows/cmd\.exe',
    r'etc/passwd',
    r'etc/shadow',
]

# 危险命令关键词
DANGEROUS_COMMAND_KEYWORDS = [
    'rm -rf',
    'mkfs',
    'dd if=',
    '> /dev/sd',
    'chmod 777',
    r'wget.*\|',
    r'curl.*\|',
    'nc -e',
    '/bin/sh',
    'bash -i',
    'eval ',
    'exec ',
]


# ============================================
# 安全验证结果
# ============================================

@dataclass
class SecurityCheckResult:
    """安全检查结果"""
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None


# ============================================
# 路径安全
# ============================================

class PathValidator:
    """路径安全验证器"""
    
    def __init__(self, allowed_base_dirs: Optional[List[str]] = None):
        """
        初始化路径验证器
        
        Args:
            allowed_base_dirs: 允许访问的基础目录列表
        """
        self.allowed_base_dirs = allowed_base_dirs or []
    
    def validate(self, path: str, allow_absolute: bool = True) -> SecurityCheckResult:
        """
        验证路径安全性
        
        Args:
            path: 待验证的路径
            allow_absolute: 是否允许绝对路径
            
        Returns:
            SecurityCheckResult: 验证结果
        """
        if not path:
            return SecurityCheckResult(False, "路径不能为空")
        
        # 检查路径穿越
        if '..' in Path(path).parts:
            return SecurityCheckResult(False, "路径包含非法穿越")
        
        # 检查危险路径模式
        for pattern in DANGEROUS_PATH_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                return SecurityCheckResult(False, f"路径包含危险模式: {pattern}")
        
        # 转换为绝对路径
        try:
            abs_path = os.path.abspath(path)
        except Exception as e:
            return SecurityCheckResult(False, f"路径解析失败: {e}")
        
        # 检查是否在允许的基础目录内
        if self.allowed_base_dirs:
            in_allowed = False
            for base_dir in self.allowed_base_dirs:
                base_abs = os.path.abspath(base_dir)
                if abs_path.startswith(base_abs):
                    in_allowed = True
                    break
            
            if not in_allowed:
                return SecurityCheckResult(
                    False, 
                    f"路径不在允许的目录内: {self.allowed_base_dirs}"
                )
        
        return SecurityCheckResult(True, "路径验证通过", {"abs_path": abs_path})
    
    def validate_extension(self, path: str, allowed_extensions: set) -> SecurityCheckResult:
        """验证文件扩展名"""
        ext = os.path.splitext(path)[1].lower()
        
        if ext not in allowed_extensions:
            return SecurityCheckResult(
                False, 
                f"不允许的文件类型: {ext}",
                {"extension": ext, "allowed": list(allowed_extensions)}
            )
        
        return SecurityCheckResult(True, "扩展名验证通过")


# ============================================
# 命令安全
# ============================================

class CommandValidator:
    """命令安全验证器"""
    
    def __init__(self, allowed_commands: Optional[List[str]] = None):
        """
        初始化命令验证器
        
        Args:
            allowed_commands: 允许执行的命令白名单
        """
        self.allowed_commands = allowed_commands or ['ffmpeg', 'ffprobe']
    
    def validate(self, cmd: List[str]) -> SecurityCheckResult:
        """
        验证命令安全性
        
        Args:
            cmd: 命令列表
            
        Returns:
            SecurityCheckResult: 验证结果
        """
        if not cmd:
            return SecurityCheckResult(False, "命令不能为空")
        
        # 检查危险命令
        cmd_str = ' '.join(cmd)
        for keyword in DANGEROUS_COMMAND_KEYWORDS:
            if keyword in cmd_str:
                return SecurityCheckResult(
                    False, 
                    f"命令包含危险关键词: {keyword}",
                    {"keyword": keyword}
                )
        
        # 检查命令白名单
        if self.allowed_commands:
            if cmd[0] not in self.allowed_commands:
                return SecurityCheckResult(
                    False,
                    f"不允许执行的命令: {cmd[0]}",
                    {"command": cmd[0], "allowed": self.allowed_commands}
                )
        
        return SecurityCheckResult(True, "命令验证通过", {"command": cmd[0]})


# ============================================
# 安全执行器
# ============================================

class SecureExecutor:
    """安全的命令执行器"""
    
    def __init__(
        self,
        allowed_base_dirs: Optional[List[str]] = None,
        allowed_commands: Optional[List[str]] = None
    ):
        self.path_validator = PathValidator(allowed_base_dirs)
        self.command_validator = CommandValidator(allowed_commands)
    
    def run(
        self,
        cmd: List[str],
        timeout: int = 30,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None
    ) -> subprocess.CompletedProcess:
        """
        安全执行命令
        
        Args:
            cmd: 命令列表
            timeout: 超时时间（秒）
            cwd: 工作目录
            env: 环境变量
            
        Returns:
            subprocess.CompletedProcess: 执行结果
            
        Raises:
            SecurityError: 安全验证失败
        """
        # 验证命令
        cmd_result = self.command_validator.validate(cmd)
        if not cmd_result.passed:
            raise SecurityError(f"命令验证失败: {cmd_result.message}")
        
        # 验证工作目录
        if cwd:
            cwd_result = self.path_validator.validate(cwd)
            if not cwd_result.passed:
                raise SecurityError(f"工作目录验证失败: {cwd_result.message}")
        
        # 清理环境变量
        safe_env = self._sanitize_env(env)
        
        # 执行命令
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                env=safe_env,
                shell=False  # 强制不使用 shell
            )
            return result
            
        except subprocess.TimeoutExpired:
            raise SecurityError(f"命令执行超时: {timeout}秒")
        except Exception as e:
            raise SecurityError(f"命令执行失败: {e}")
    
    def _sanitize_env(self, env: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """清理环境变量，移除危险变量"""
        if env is None:
            return None
            
        # 危险环境变量
        dangerous_vars = {
            'LD_PRELOAD', 'LD_LIBRARY_PATH', 'DYLD_INSERT_LIBRARIES',
            'DYLD_LIBRARY_PATH', 'BASH_ENV', 'ENV', 'IFS', 'PS1', 'PS2'
        }
        
        safe_env = {k: v for k, v in env.items() if k not in dangerous_vars}
        
        # 添加 PATH 限制
        safe_env['PATH'] = '/usr/bin:/bin:/usr/local/bin'
        
        return safe_env


# ============================================
# 输入清理
# ============================================

class InputSanitizer:
    """输入清理器"""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        清理文件名
        
        - 移除危险字符
        - 防止路径穿越
        - 限制长度
        """
        if not filename:
            return "unnamed"
        
        # 移除路径分隔符
        filename = os.path.basename(filename)
        
        # 移除危险字符
        filename = re.sub(r'[^\w\s\-\.]', '', filename)
        
        # 限制长度
        max_length = 255
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            filename = name[:max_length - len(ext)] + ext
        
        # 防止空文件名
        if not filename.strip():
            filename = "unnamed"
        
        return filename
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 10000) -> str:
        """清理文本输入"""
        if not text:
            return ""
        
        # 移除控制字符
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        # 限制长度
        if len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    @staticmethod
    def sanitize_path(path: str) -> str:
        """清理路径输入"""
        if not path:
            return ""
        
        # 标准化路径
        path = os.path.normpath(path)
        
        # 移除危险模式
        path = path.replace('..', '')
        
        return path


# ============================================
# 文件操作安全
# ============================================

class SecureFileHandler:
    """安全文件处理器"""
    
    def __init__(
        self,
        allowed_base_dirs: Optional[List[str]] = None,
        allowed_extensions: Optional[Dict[str, set]] = None
    ):
        self.path_validator = PathValidator(allowed_base_dirs)
        self.allowed_extensions = allowed_extensions or {
            'video': ALLOWED_VIDEO_EXTENSIONS,
            'image': ALLOWED_IMAGE_EXTENSIONS,
            'audio': ALLOWED_AUDIO_EXTENSIONS,
            'document': ALLOWED_DOCUMENT_EXTENSIONS,
        }
    
    def read(
        self, 
        path: str, 
        mode: str = 'r',
        max_size: int = 100 * 1024 * 1024,  # 100MB
        category: str = 'document'
    ) -> str:
        """
        安全读取文件
        
        Args:
            path: 文件路径
            mode: 读取模式
            max_size: 最大文件大小
            category: 文件类别
            
        Returns:
            文件内容
            
        Raises:
            SecurityError: 安全验证失败
        """
        # 验证路径
        result = self.path_validator.validate(path)
        if not result.passed:
            raise SecurityError(f"路径验证失败: {result.message}")
        
        # 验证扩展名
        allowed = self.allowed_extensions.get(category, ALLOWED_DOCUMENT_EXTENSIONS)
        ext_result = self.path_validator.validate_extension(path, allowed)
        if not ext_result.passed:
            raise SecurityError(f"扩展名验证失败: {ext_result.message}")
        
        # 检查文件大小
        try:
            size = os.path.getsize(path)
            if size > max_size:
                raise SecurityError(f"文件过大: {size} > {max_size}")
        except Exception as e:
            raise SecurityError(f"无法获取文件大小: {e}")
        
        # 读取文件
        try:
            with open(path, mode) as f:
                return f.read()
        except Exception as e:
            raise SecurityError(f"文件读取失败: {e}")
    
    def write(
        self,
        path: str,
        content: str,
        mode: str = 'w',
        category: str = 'document'
    ) -> None:
        """安全写入文件"""
        # 验证路径
        result = self.path_validator.validate(path)
        if not result.passed:
            raise SecurityError(f"路径验证失败: {result.message}")
        
        # 验证扩展名
        allowed = self.allowed_extensions.get(category, ALLOWED_DOCUMENT_EXTENSIONS)
        ext_result = self.path_validator.validate_extension(path, allowed)
        if not ext_result.passed:
            raise SecurityError(f"扩展名验证失败: {ext_result.message}")
        
        # 确保目录存在
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # 写入文件
        try:
            with open(path, mode) as f:
                f.write(content)
        except Exception as e:
            raise SecurityError(f"文件写入失败: {e}")


# ============================================
# 异常定义
# ============================================

class SecurityError(Exception):
    """安全相关异常"""
    pass


# ============================================
# 便捷函数
# ============================================

def create_secure_executor(allowed_dirs: Optional[List[str]] = None) -> SecureExecutor:
    """创建安全的命令执行器"""
    return SecureExecutor(
        allowed_base_dirs=allowed_dirs or [os.path.expanduser("~/")],
        allowed_commands=['ffmpeg', 'ffprobe', 'python', 'python3']
    )


def create_secure_file_handler(allowed_dirs: Optional[List[str]] = None) -> SecureFileHandler:
    """创建安全的文件处理器"""
    return SecureFileHandler(
        allowed_base_dirs=allowed_dirs or [os.path.expanduser("~/")]
    )


def validate_video_path(path: str, base_dir: Optional[str] = None) -> SecurityCheckResult:
    """验证视频路径"""
    handler = SecureFileHandler(
        allowed_base_dirs=[base_dir] if base_dir else None
    )
    result = handler.path_validator.validate(path)
    if result.passed:
        result = handler.path_validator.validate_extension(
            path, 
            ALLOWED_VIDEO_EXTENSIONS
        )
    return result
