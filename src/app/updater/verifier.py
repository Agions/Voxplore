"""升级包 SHA256 校验器。

为什么独立模块：

* 升级包进入生产目录前必须经过完整性校验，否则可能植入恶意代码；
* 校验逻辑独立于下载器，便于单元测试与替换算法（如未来支持 minisign）。
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_CHUNK = 64 * 1024


class VerificationError(ValueError):
    """校验失败：sha256 不匹配或参数非法。"""


def compute_sha256(file_path: Path, *, chunk_size: int = _CHUNK) -> str:
    """计算文件 SHA256（小写十六进制）。"""

    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def verify_sha256(file_path: Path, expected_sha256: str) -> bool:
    """校验文件 SHA256 是否等于 ``expected_sha256``。

    Args:
        file_path: 待校验文件。
        expected_sha256: 期望的 SHA256（小写或大写十六进制均可）。

    Returns:
        True 表示校验通过。

    Raises:
        VerificationError: 文件不存在、期望值格式非法，或哈希不匹配。
    """
    if not expected_sha256:
        raise VerificationError("expected sha256 is empty")

    expected = expected_sha256.strip().lower()
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise VerificationError(f"invalid sha256 format: {expected_sha256!r}")

    if not file_path.exists():
        raise VerificationError(f"file not found: {file_path}")

    actual = compute_sha256(file_path)
    if actual != expected:
        logger.warning(
            "SHA256 mismatch for %s: expected=%s actual=%s",
            file_path,
            expected,
            actual,
        )
        raise VerificationError(
            f"sha256 mismatch: expected={expected[:12]}... actual={actual[:12]}..."
        )
    return True


__all__ = ["verify_sha256", "compute_sha256", "VerificationError"]
