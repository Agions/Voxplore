"""
安全密钥管理器 - 解决API密钥明文存储问题
实现企业级密钥加密存储和管理
"""

import os
import json
import base64
from typing import Dict, Optional, Any, List
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import keyring
import platform
import hashlib
import logging
import threading


class SecureKeyManager:
    """安全密钥管理器 - 修复API密钥安全问题"""

    def __init__(self, app_name: str = "Voxplore"):
        self.app_name = app_name
        self.logger = logging.getLogger(__name__)
        self._encryption_key: Optional[bytes] = None
        self._master_password: Optional[str] = None

        # 尝试初始化系统密钥库
        self._init_keyring()

    def _init_keyring(self) -> None:
        """初始化系统密钥库"""
        try:
            # 检查系统密钥库可用性
            if platform.system() == "Darwin":  # macOS
                # 使用安全的方式初始化macOS密钥库
                try:
                    from keyring.backends import macOS
                    keyring.set_keyring(macOS.Keyring())
                except (ImportError, AttributeError):
                    # 尝试另一种方式
                    try:
                        from keyring.backends import OSX
                        keyring.set_keyring(OSX.Keyring())
                    except (ImportError, AttributeError):
                        self.logger.debug("macOS keyring backend (OSX) init failed, skipping")
            elif platform.system() == "Windows":
                try:
                    from keyring.backends import Windows
                    keyring.set_keyring(Windows.WinVaultKeyring())
                except (ImportError, AttributeError):
                    self.logger.debug("Windows keyring backend init failed, skipping")
            elif platform.system() == "Linux":
                try:
                    from keyring.backends import SecretService
                    keyring.set_keyring(SecretService.Keyring())
                except (ImportError, AttributeError):
                    try:
                        from keyring.backends import Gnome
                        keyring.set_keyring(Gnome.Keyring())
                    except (ImportError, AttributeError):
                        self.logger.debug("Linux keyring backend (Gnome) init failed, skipping")

            # 测试密钥库功能
            test_key = f"{self.app_name}_test"
            keyring.set_password(self.app_name, test_key, "test")
            keyring.delete_password(self.app_name, test_key)

            self.logger.info("System keyring initialized successfully")
        except Exception as e:
            self.logger.warning(f"System keyring not available: {e}")

    def _get_master_key(self) -> bytes:
        """获取主加密密钥"""
        if self._encryption_key is None:
            try:
                # 尝试从系统密钥库获取
                master_password = keyring.get_password(self.app_name, "master_key")
                if not master_password:
                    # 生成新的主密钥
                    master_password = base64.urlsafe_b64encode(os.urandom(32)).decode()
                    keyring.set_password(self.app_name, "master_key", master_password)
                    self.logger.info("Generated new master key")

                # 使用PBKDF2衍生密钥
                password = master_password.encode()
                salt = hashlib.sha256(self.app_name.encode()).digest()[:16]
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=480000,  # OWASP 建议最低 480,000 次
                )
                self._encryption_key = base64.urlsafe_b64encode(kdf.derive(password))

            except Exception as e:
                self.logger.error(f"Failed to get master key: {e}")
                # 降级到基于文件的加密
                self._encryption_key = self._get_file_based_key()

        return self._encryption_key

    def _get_file_based_key(self) -> bytes:
        """获取基于文件的加密密钥（降级方案）"""
        key_file = Path.home() / f".{self.app_name.lower()}" / "master.key"
        key_file.parent.mkdir(exist_ok=True)

        if key_file.exists():
            try:
                with open(key_file, 'rb') as f:
                    return f.read()
            except Exception as e:
                self.logger.error(f"Failed to read key file: {e}")

        # 生成新密钥
        key = Fernet.generate_key()
        try:
            with open(key_file, 'wb') as f:
                f.write(key)
            # 设置文件权限（仅用户可读）
            os.chmod(key_file, 0o600)
            self.logger.info("Generated new file-based encryption key")
        except Exception as e:
            self.logger.error(f"Failed to save key file: {e}")

        return key

    def store_api_key(self, provider: str, api_key: str, metadata: Dict[str, Any] = None) -> bool:
        """安全存储API密钥"""
        try:
            key_data = {
                "api_key": api_key,
                "provider": provider,
                "metadata": metadata or {},
                "created_at": str(Path().cwd().stat().st_mtime),
                "app_version": "2.0.0"
            }

            # 首先尝试系统密钥库
            try:
                service_name = f"{self.app_name}_{provider}"
                keyring.set_password(service_name, "api_key", json.dumps(key_data))
                self.logger.info(f"API key for {provider} stored in system keyring")
                return True
            except Exception as e:
                self.logger.warning(f"System keyring failed: {e}, using encrypted file storage")

            # 降级到加密文件存储
            return self._store_encrypted_key(provider, key_data)

        except Exception as e:
            self.logger.error(f"Failed to store API key for {provider}: {e}")
            return False

    def _store_encrypted_key(self, provider: str, key_data: Dict[str, Any]) -> bool:
        """使用加密文件存储API密钥"""
        try:
            encryption_key = self._get_master_key()
            cipher = Fernet(encryption_key)

            # 加密数据
            encrypted_data = cipher.encrypt(json.dumps(key_data).encode())

            # 存储到安全目录
            secure_dir = Path.home() / f".{self.app_name.lower()}" / "keys"
            secure_dir.mkdir(parents=True, exist_ok=True)

            key_file = secure_dir / f"{provider}.key"
            with open(key_file, 'wb') as f:
                f.write(encrypted_data)

            # 设置文件权限
            os.chmod(key_file, 0o600)

            self.logger.info(f"API key for {provider} stored in encrypted file")
            return True

        except Exception as e:
            self.logger.error(f"Failed to store encrypted key for {provider}: {e}")
            return False

    def get_api_key(self, provider: str) -> Optional[Dict[str, Any]]:
        """安全获取API密钥"""
        try:
            # 首先尝试系统密钥库
            try:
                service_name = f"{self.app_name}_{provider}"
                key_data_str = keyring.get_password(service_name, "api_key")
                if key_data_str:
                    key_data = json.loads(key_data_str)
                    return key_data
            except Exception as e:
                # keyring 访问失败，降级到加密文件
                self.logger.warning(f"keyring access failed, falling back to encrypted file: {e}")

            # 降级到加密文件
            return self._get_encrypted_key(provider)

        except Exception as e:
            self.logger.error(f"Failed to get API key for {provider}: {e}")
            return None

    def _get_encrypted_key(self, provider: str) -> Optional[Dict[str, Any]]:
        """从加密文件获取API密钥"""
        try:
            secure_dir = Path.home() / f".{self.app_name.lower()}" / "keys"
            key_file = secure_dir / f"{provider}.key"

            if not key_file.exists():
                return None

            encryption_key = self._get_master_key()
            cipher = Fernet(encryption_key)

            with open(key_file, 'rb') as f:
                encrypted_data = f.read()

            # 解密数据
            decrypted_data = cipher.decrypt(encrypted_data)
            key_data = json.loads(decrypted_data.decode())

            return key_data

        except Exception as e:
            self.logger.error(f"Failed to get encrypted key for {provider}: {e}")
            return None

    def delete_api_key(self, provider: str) -> bool:
        """删除API密钥"""
        try:
            success = False

            # 删除系统密钥库中的密钥
            try:
                service_name = f"{self.app_name}_{provider}"
                keyring.delete_password(service_name, "api_key")
                success = True
                self.logger.info(f"Deleted API key for {provider} from system keyring")
            except Exception as e:
                self.logger.warning(f"Failed to delete key from system keyring: {e}")

            # 删除加密文件
            try:
                secure_dir = Path.home() / f".{self.app_name.lower()}" / "keys"
                key_file = secure_dir / f"{provider}.key"
                if key_file.exists():
                    key_file.unlink()
                    success = True
                    self.logger.info(f"Deleted encrypted key file for {provider}")
            except Exception as e:
                self.logger.error(f"Failed to delete encrypted key file: {e}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to delete API key for {provider}: {e}")
            return False

    def list_stored_keys(self) -> List[str]:
        """列出所有存储的密钥提供商"""
        providers = set()

        # 检查加密文件
        try:
            secure_dir = Path.home() / f".{self.app_name.lower()}" / "keys"
            if secure_dir.exists():
                for key_file in secure_dir.glob("*.key"):
                    providers.add(key_file.stem)
        except Exception as e:
            self.logger.error(f"Failed to list encrypted keys: {e}")

        return list(providers)

    def rotate_master_key(self) -> bool:
        """轮换主密钥"""
        try:
            # 获取所有存储的密钥
            stored_providers = self.list_stored_keys()
            stored_keys = {}

            # 读取所有现有密钥
            for provider in stored_providers:
                key_data = self.get_api_key(provider)
                if key_data:
                    stored_keys[provider] = key_data

            # 生成新的主密钥
            self._encryption_key = None
            try:
                keyring.delete_password(self.app_name, "master_key")
            except Exception as e:
                self.logger.debug(f"Failed to delete old master key: {e}")

            # 重新存储所有密钥（使用新的主密钥）
            for provider, key_data in stored_keys.items():
                self.store_api_key(provider, key_data["api_key"], key_data.get("metadata"))

            self.logger.info("Master key rotated successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to rotate master key: {e}")
            return False

    def validate_key_integrity(self) -> Dict[str, bool]:
        """验证密钥完整性"""
        results = {}

        for provider in self.list_stored_keys():
            try:
                key_data = self.get_api_key(provider)
                results[provider] = key_data is not None and "api_key" in key_data
            except Exception as e:
                self.logger.debug(f"Integrity check failed for {provider}: {e}")
                results[provider] = False

        return results

    def get_security_status(self) -> Dict[str, Any]:
        """获取安全状态"""
        return {
            "keyring_available": self._is_keyring_available(),
            "stored_keys_count": len(self.list_stored_keys()),
            "encryption_method": "system_keyring" if self._is_keyring_available() else "file_based",
            "key_integrity": self.validate_key_integrity()
        }

    def _is_keyring_available(self) -> bool:
        """检查系统密钥库是否可用"""
        try:
            test_key = f"{self.app_name}_test_availability"
            keyring.set_password(self.app_name, test_key, "test")
            keyring.delete_password(self.app_name, test_key)
            return True
        except Exception as e:
            self.logger.debug(f"Keyring unavailable: {e}")
            return False


# 全局安全密钥管理器实例
_secure_key_manager: Optional[SecureKeyManager] = None
_secure_key_lock = threading.Lock()


def get_secure_key_manager() -> SecureKeyManager:
    """获取全局安全密钥管理器实例"""
    global _secure_key_manager
    if _secure_key_manager is None:
        with _secure_key_lock:
            if _secure_key_manager is None:
                _secure_key_manager = SecureKeyManager()
    return _secure_key_manager