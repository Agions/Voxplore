"""
安全配置加载器 ✅ 优化版本
安全地加载 YAML/JSON 配置文件
支持环境变量和 .env 文件
"""

import os
import json
import logging
from typing import Any, Dict, Optional
import yaml
import threading

# ✅ 新增：python-dotenv 支持
try:
    from dotenv import load_dotenv, find_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    def load_dotenv(*args, **kwargs):
        return None
    def find_dotenv(*args, **kwargs):
        return None

from ..utils.security import (
    PathValidator,
    InputSanitizer,
    SecurityError
)

logger = logging.getLogger(__name__)


class SecureConfigLoader:
    """安全配置加载器"""
    
    def __init__(self, allowed_dirs: Optional[list] = None, env_file: Optional[str] = None):
        """
        初始化安全配置加载器
        
        Args:
            allowed_dirs: 允许加载配置的目录列表
            env_file: .env 文件路径（可选）
        """
        # ✅ 加载环境变量
        self._load_environment(env_file)
        
        self.allowed_dirs = allowed_dirs or [
            os.path.expanduser("~/.narrafiilm"),
            os.path.expanduser("~/Voxplore"),
            "/etc/narrafiilm",
            os.path.join(os.path.dirname(__file__), '..', '..', 'config')
        ]
        self.allowed_dirs = [os.path.abspath(d) for d in self.allowed_dirs]
        
        self.path_validator = PathValidator(self.allowed_dirs)
        self.sanitizer = InputSanitizer()
        
        # ✅ 敏感配置项（这些值不会被记录到日志）
        self._sensitive_keys = {
            'api_key', 'api_secret', 'password', 'secret',
            'token', 'access_token', 'refresh_token',
            'private_key', 'public_key'
        }
    
    def _load_environment(self, env_file: Optional[str] = None) -> None:
        """
        加载环境变量 ✅ 新增
        
        优先级：
        1. 系统环境变量（最高）
        2. .env 文件
        3. .env.local 文件（开发环境）
        """
        if not DOTENV_AVAILABLE:
            logger.warning("python-dotenv 未安装，环境变量将仅从系统读取")
            return
        
        # 查找并加载 .env 文件
        if env_file:
            # 指定文件
            load_dotenv(env_file, override=True)
            logger.debug(f"从指定文件加载环境变量: {env_file}")
        else:
            # 自动查找 .env 文件
            env_path = find_dotenv(usecwd=True)
            if env_path:
                load_dotenv(env_path, override=True)
                logger.debug(f"自动加载环境变量: {env_path}")
    
    def get_env(self, key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
        """
        获取环境变量 ✅ 新增便捷方法
        
        Args:
            key: 环境变量名
            default: 默认值
            required: 是否必需（为 True 且未找到时抛出异常）
            
        Returns:
            环境变量值
        """
        value = os.getenv(key, default)
        
        if required and not value:
            raise SecurityError(f"必需的环境变量未设置: {key}")
        
        return value
    
    def get_api_key(self, provider: str, env_var: Optional[str] = None) -> str:
        """
        安全获取 API Key ✅ 新增便捷方法
        
        支持从环境变量读取，优先级：
        1. {PROVIDER}_API_KEY (如 QWEN_API_KEY)
        2. {env_var} 指定的值
        3. API_KEY (通用)
        
        Args:
            provider: 提供商名称 (如 "qwen", "openai")
            env_var: 直接指定的环境变量名
            
        Returns:
            API Key
            
        Raises:
            SecurityError: API Key 未找到
        """
        # 构建可能的环境变量名
        possible_keys = []
        
        if env_var:
            possible_keys.append(env_var)
        
        if provider:
            possible_keys.extend([
                f"{provider.upper()}_API_KEY",
                f"{provider.upper()}_API_TOKEN",
            ])
        
        possible_keys.extend(['API_KEY', 'API_TOKEN', 'OPENAI_API_KEY'])
        
        for key in possible_keys:
            value = os.getenv(key)
            if value:
                logger.debug(f"找到 API Key: {key[:10]}...")
                return value
        
        raise SecurityError(
            f"未找到 {provider} 的 API Key。"
            f"请设置环境变量：{possible_keys[0]}"
        )
    
    def load_yaml(self, config_path: str, resolve_env: bool = True) -> Dict[str, Any]:
        """
        安全加载 YAML 配置文件
        
        Args:
            config_path: 配置文件路径
            resolve_env: 是否解析 ${ENV_VAR} 形式的环境变量引用
            
        Returns:
            配置字典
            
        Raises:
            SecurityError: 安全验证失败
        """
        # 验证路径
        clean_path = self.sanitizer.sanitize_path(config_path)
        result = self.path_validator.validate(clean_path)
        if not result.passed:
            raise SecurityError(f"配置路径验证失败: {result.message}")
        
        # 验证扩展名
        ext_result = self.path_validator.validate_extension(
            clean_path, 
            {'.yaml', '.yml'}
        )
        if not ext_result.passed:
            raise SecurityError(f"配置文件类型不支持: {ext_result.message}")
        
        # 检查文件大小
        try:
            size = os.path.getsize(clean_path)
            if size > 10 * 1024 * 1024:  # 10MB
                raise SecurityError(f"配置文件过大: {size} bytes")
        except Exception as e:
            raise SecurityError(f"无法检查文件大小: {e}")
        
        # 安全加载 YAML
        try:
            with open(clean_path, 'r', encoding='utf-8') as f:
                # 使用 safe_load 防止代码执行
                config = yaml.safe_load(f)
                
            # 验证配置结构
            config = self._validate_config(config)
            
            # ✅ 解析环境变量引用
            if resolve_env:
                config = self._resolve_env_vars(config)
            
            logger.info(f"安全加载配置: {clean_path}")
            return config
            
        except yaml.YAMLError as e:
            raise SecurityError(f"YAML 解析错误: {e}")
        except Exception as e:
            raise SecurityError(f"配置加载失败: {e}")
    
    def load_json(self, config_path: str, resolve_env: bool = True) -> Dict[str, Any]:
        """
        安全加载 JSON 配置文件
        
        Args:
            config_path: 配置文件路径
            resolve_env: 是否解析环境变量引用
            
        Returns:
            配置字典
        """
        # 验证路径
        clean_path = self.sanitizer.sanitize_path(config_path)
        result = self.path_validator.validate(clean_path)
        if not result.passed:
            raise SecurityError(f"配置路径验证失败: {result.message}")
        
        # 验证扩展名
        ext_result = self.path_validator.validate_extension(
            clean_path, 
            {'.json'}
        )
        if not ext_result.passed:
            raise SecurityError(f"配置文件类型不支持: {ext_result.message}")
        
        # 加载 JSON
        try:
            with open(clean_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            config = self._validate_config(config)
            
            # ✅ 解析环境变量引用
            if resolve_env:
                config = self._resolve_env_vars(config)
            
            logger.info(f"安全加载 JSON 配置: {clean_path}")
            return config
            
        except json.JSONDecodeError as e:
            raise SecurityError(f"JSON 解析错误: {e}")
        except Exception as e:
            raise SecurityError(f"配置加载失败: {e}")
    
    def _resolve_env_vars(self, obj: Any, depth: int = 0) -> Any:
        """
        递归解析配置中的 ${ENV_VAR} 形式的环境变量引用 ✅ 新增
        
        Args:
            obj: 配置对象
            depth: 递归深度（防止无限循环）
            
        Returns:
            解析后的配置
        """
        if depth > 10:
            logger.warning("环境变量解析超过最大深度，跳过")
            return obj
        
        if isinstance(obj, dict):
            return {k: self._resolve_env_vars(v, depth + 1) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_env_vars(item, depth + 1) for item in obj]
        elif isinstance(obj, str):
            return self._substitute_env_vars(obj)
        else:
            return obj
    
    def _substitute_env_vars(self, value: str) -> str:
        """
        替换字符串中的 ${ENV_VAR} 为实际值
        
        支持格式：
        - ${VAR_NAME} - 基本用法
        - ${VAR_NAME:-default} - 带默认值
        """
        import re
        
        def replacer(match):
            var_expr = match.group(1)
            
            # 处理默认值语法 ${VAR:-default}
            if ':-' in var_expr:
                var_name, default = var_expr.split(':-', 1)
                return os.getenv(var_name.strip(), default.strip())
            else:
                return os.getenv(var_expr.strip(), value)
        
        # 匹配 ${VAR} 或 ${VAR:-default}
        return re.sub(r'\$\{([^}]+)\}', replacer, value)
    
    def _validate_config(self, config: Any) -> Dict[str, Any]:
        """
        验证配置结构
        
        Args:
            config: 配置数据
            
        Returns:
            验证后的配置
            
        Raises:
            SecurityError: 配置验证失败
        """
        if config is None:
            return {}
        
        if not isinstance(config, dict):
            raise SecurityError("配置根元素必须是对象")
        
        # 递归清理配置值
        return self._sanitize_config(config)
    
    def _sanitize_config(self, obj: Any, depth: int = 0) -> Any:
        """递归清理配置值"""
        if depth > 10:
            return obj
            
        if isinstance(obj, dict):
            return {k: self._sanitize_config(v, depth + 1) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._sanitize_config(item, depth + 1) for item in obj]
        elif isinstance(obj, str):
            # 清理字符串配置值
            return self.sanitizer.sanitize_text(obj, max_length=10000)
        else:
            return obj
    
    def _mask_sensitive(self, value: str) -> str:
        """掩码敏感信息（用于日志）"""
        if len(value) <= 8:
            return "***"
        return value[:4] + "***" + value[-4:]
    
    def save_yaml(self, config: Dict[str, Any], config_path: str) -> None:
        """
        安全保存 YAML 配置
        
        Args:
            config: 配置字典
            config_path: 保存路径
        """
        # 验证路径
        clean_path = self.sanitizer.sanitize_path(config_path)
        result = self.path_validator.validate(clean_path)
        if not result.passed:
            raise SecurityError(f"保存路径验证失败: {result.message}")
        
        # 验证扩展名
        ext_result = self.path_validator.validate_extension(
            clean_path, 
            {'.yaml', '.yml'}
        )
        if not ext_result.passed:
            raise SecurityError(f"配置文件类型不支持: {ext_result.message}")
        
        # 确保目录存在
        dir_path = os.path.dirname(clean_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # 安全保存
        try:
            with open(clean_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(
                    config, 
                    f, 
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False
                )
            logger.info(f"安全保存配置: {clean_path}")
        except Exception as e:
            raise SecurityError(f"配置保存失败: {e}")


# ============ 全局实例 ============

_config_loader: Optional[SecureConfigLoader] = None
_config_loader_lock = threading.Lock()


def get_config_loader() -> SecureConfigLoader:
    """获取全局配置加载器"""
    global _config_loader
    if _config_loader is None:
        with _config_loader_lock:
            if _config_loader is None:
                _config_loader = SecureConfigLoader()
    return _config_loader


def safe_load_yaml(config_path: str) -> Dict[str, Any]:
    """安全加载 YAML 配置的便捷函数"""
    return get_config_loader().load_yaml(config_path)


def safe_load_json(config_path: str) -> Dict[str, Any]:
    """安全加载 JSON 配置的便捷函数"""
    return get_config_loader().load_json(config_path)


def safe_save_yaml(config: Dict[str, Any], config_path: str) -> None:
    """安全保存 YAML 配置的便捷函数"""
    get_config_loader().save_yaml(config, config_path)


# ✅ 新增便捷函数
def get_api_key(provider: str) -> str:
    """获取 API Key 的便捷函数"""
    return get_config_loader().get_api_key(provider)
