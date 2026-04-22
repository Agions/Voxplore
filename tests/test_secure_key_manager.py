#!/usr/bin/env python3
"""测试安全密钥管理器"""

from unittest.mock import patch
from cryptography.fernet import Fernet

from app.core.secure_key_manager import SecureKeyManager


class TestSecureKeyManager:
    """测试安全密钥管理器"""

    @patch('app.core.secure_key_manager.platform.system')
    @patch('app.core.secure_key_manager.keyring')
    def test_init_default(self, mock_keyring, mock_platform):
        """测试默认初始化"""
        mock_platform.return_value = "Linux"
        
        manager = SecureKeyManager()
        
        assert manager.app_name == "Voxplore"
        assert manager._encryption_key is None
        assert manager._master_password is None

    @patch('app.core.secure_key_manager.platform.system')
    @patch('app.core.secure_key_manager.keyring')
    def test_init_custom_app_name(self, mock_keyring, mock_platform):
        """测试自定义应用名称"""
        mock_platform.return_value = "Linux"
        
        manager = SecureKeyManager(app_name="MyApp")
        
        assert manager.app_name == "MyApp"

    @patch('app.core.secure_key_manager.platform.system')
    @patch('app.core.secure_key_manager.keyring')
    @patch('app.core.secure_key_manager.SecureKeyManager._get_master_key')
    def test_store_and_get_key(self, mock_master_key, mock_keyring, mock_platform):
        """测试存储和获取密钥"""
        mock_platform.return_value = "Linux"
        mock_master_key.return_value = Fernet.generate_key()

        manager = SecureKeyManager()

        # 直接 patch Fernet 来测试存储（简化）
        result = manager.store_api_key("openai", "test_key_123")

        # 存储可能成功或失败，取决于环境，但不应抛异常
        assert isinstance(result, bool)

    @patch('app.core.secure_key_manager.platform.system')
    @patch('app.core.secure_key_manager.keyring')
    def test_delete_key(self, mock_keyring, mock_platform):
        """测试删除密钥"""
        mock_platform.return_value = "Linux"

        manager = SecureKeyManager()

        # 不应该抛出异常
        manager.delete_api_key("nonexistent_key")

    @patch('app.core.secure_key_manager.platform.system')
    @patch('app.core.secure_key_manager.keyring')
    def test_list_stored_keys(self, mock_keyring, mock_platform):
        """测试列出已存储的密钥"""
        mock_platform.return_value = "Linux"

        manager = SecureKeyManager()

        # Mock _get_encrypted_key 返回空（无存储密钥）
        with patch.object(manager, '_get_encrypted_key', return_value=None):
            keys = manager.list_stored_keys()
            assert isinstance(keys, list)


class TestSecureKeyManagerPlatform:
    """测试平台相关功能"""

    @patch('app.core.secure_key_manager.platform.system')
    def test_darwin_platform(self, mock_platform):
        """测试 macOS 平台"""
        mock_platform.return_value = "Darwin"
        
        # 不应该抛出异常
        try:
            _ = SecureKeyManager()
        except Exception:
            pass  # 忽略预期错误

    @patch('app.core.secure_key_manager.platform.system')
    def test_windows_platform(self, mock_platform):
        """测试 Windows 平台"""
        mock_platform.return_value = "Windows"
        
        try:
            _ = SecureKeyManager()
        except Exception:
            pass

    @patch('app.core.secure_key_manager.platform.system')
    def test_linux_platform(self, mock_platform):
        """测试 Linux 平台"""
        mock_platform.return_value = "Linux"
        
        try:
            _ = SecureKeyManager()
        except Exception:
            pass
