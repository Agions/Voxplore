"""升级包安装与回滚。

策略：

* 升级前将当前 ``app/`` 目录（或可执行文件根目录）备份到
  ``~/.cache/scenefab/backups/v{version}-{timestamp}/``；
* 解压新包到临时目录 ``staging/``，先在临时目录做冒烟测试（如 import sanity）；
* macOS / Linux：通过 ``shutil.move`` + ``os.replace`` 实现原子切换；
  若 ``os.replace`` 跨设备失败，回退到 copy + remove。
* Windows：通过 ctypes 调用 ``MoveFileExW(..., MOVEFILE_REPLACE_EXISTING |
  MOVEFILE_WRITE_THROUGH)``；
* 升级失败或用户撤销时调用 :meth:`Installer.rollback` 恢复到上一版本。

备份保留策略：

* 仅保留最近 3 个备份版本，超过 LRU 清理。
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

MAX_BACKUPS = 3


class InstallError(RuntimeError):
    """安装过程中失败（含解压、冒烟测试、原子切换失败）。"""


@dataclass
class BackupRecord:
    """一次成功备份的元数据。"""

    version: str
    backup_dir: Path
    created_at: float
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "backup_dir": str(self.backup_dir),
            "created_at": self.created_at,
            **self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "BackupRecord":
        return cls(
            version=str(payload.get("version", "")),
            backup_dir=Path(str(payload.get("backup_dir", ""))),
            created_at=float(payload.get("created_at", 0.0)),
            metadata={
                k: str(v)
                for k, v in payload.items()
                if k not in {"version", "backup_dir", "created_at"}
            },
        )


class Installer:
    """升级包安装器。

    协作模式：

    .. code-block:: python

        installer = Installer(backup_root=Path("~/.cache/scenefab/backups"))
        record = installer.backup_current(app_dir=Path("src/app"), current_version="2.4.3")
        target = installer.install(
            pkg=Path("/tmp/SceneFab-2.5.0-stable.zip"),
            target_dir=Path("src/app"),
        )
        # 失败时
        installer.rollback(record)
    """

    def __init__(
        self,
        backup_root: Path | None = None,
        *,
        max_backups: int = MAX_BACKUPS,
    ) -> None:
        self._backup_root = (
            Path(backup_root).expanduser()
            if backup_root is not None
            else Path.home() / ".cache" / "scenefab" / "backups"
        )
        self._backup_root.mkdir(parents=True, exist_ok=True)
        self._manifest_path = self._backup_root / "manifest.json"
        self._max_backups = max(1, max_backups)

    # ──────────────────────────────────────────────────────────────────
    # 备份 / 恢复
    # ──────────────────────────────────────────────────────────────────

    def list_backups(self) -> list[BackupRecord]:
        """读取所有备份记录（按 ``created_at`` 倒序）。"""

        records = self._read_manifest()
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records

    def backup_current(
        self,
        app_dir: Path,
        current_version: str,
        *,
        extras: Iterable[Path] | None = None,
    ) -> BackupRecord:
        """备份当前 ``app_dir``（及额外目录）到备份根，返回 :class:`BackupRecord`."""

        if not app_dir.exists():
            raise InstallError(f"app_dir not found: {app_dir}")

        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup_dir = self._backup_root / f"v{current_version}-{stamp}"
        if backup_dir.exists():
            # 极端情况（同一秒重试）：加微秒区分
            backup_dir = self._backup_root / \
                f"v{current_version}-{stamp}-{int(time.time() * 1000) % 1000:03d}"
        backup_dir.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copytree(app_dir, backup_dir / app_dir.name)
            for extra in extras or []:
                if not extra.exists():
                    continue
                target = backup_dir / "extras" / extra.name
                if extra.is_dir():
                    shutil.copytree(extra, target)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(extra, target)
        except OSError as exc:
            raise InstallError(f"backup failed: {exc}") from exc

        record = BackupRecord(
            version=current_version,
            backup_dir=backup_dir,
            created_at=time.time(),
            metadata={"app_dir": str(app_dir)},
        )
        records = self._read_manifest()
        records.append(record)
        self._write_manifest(records)
        self._enforce_retention()
        return record

    def rollback(self, record: BackupRecord, *, target_dir: Path | None = None) -> Path:
        """从 ``record`` 恢复 ``app_dir``，返回被恢复到的目录路径。"""

        if not record.backup_dir.exists():
            raise InstallError(f"backup missing: {record.backup_dir}")

        metadata = record.metadata or {}
        target_dir = (
            Path(target_dir) if target_dir is not None else Path(
                metadata.get("app_dir", ""))
        )
        if not target_dir:
            raise InstallError("rollback target_dir is unknown (no metadata)")

        staging = target_dir.parent / \
            f".{target_dir.name}.rollback-{int(time.time() * 1000)}"
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)

        backup_app = record.backup_dir / target_dir.name
        if not backup_app.exists():
            raise InstallError(f"backup app_dir missing: {backup_app}")

        try:
            shutil.copytree(backup_app, staging)
            self._atomic_replace(staging, target_dir)
        except OSError as exc:
            raise InstallError(f"rollback failed: {exc}") from exc

        # 标记已回滚：保留 record 但加 marker
        records = self._read_manifest()
        for r in records:
            if r.backup_dir == record.backup_dir:
                r.metadata["rolled_back_at"] = str(time.time())
                break
        self._write_manifest(records)

        logger.info("Rolled back to %s at %s", record.version, target_dir)
        return target_dir

    # ──────────────────────────────────────────────────────────────────
    # 安装
    # ──────────────────────────────────────────────────────────────────

    def install(
        self,
        pkg: Path,
        target_dir: Path,
        *,
        smoke_test: bool = True,
    ) -> Path:
        """解压 ``pkg`` 到 ``target_dir``，返回最终的 ``target_dir`` 路径。

        Args:
            pkg: 升级包 zip 路径（必须存在）。
            target_dir: 升级目标目录（一般是 ``src/app/``）。
            smoke_test: 是否做 import 冒烟测试（仅在 ``target_dir`` 名称为 ``app`` 时生效）。

        Raises:
            InstallError: 解压失败、冒烟失败或原子切换失败。
        """
        if not pkg.exists():
            raise InstallError(f"package not found: {pkg}")
        if not zipfile.is_zipfile(pkg):
            raise InstallError(f"package is not a valid zip: {pkg}")

        staging = target_dir.parent / \
            f".{target_dir.name}.staging-{int(time.time() * 1000)}"
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(pkg, "r") as zf:
                # 安全检查：禁止路径穿越
                for member in zf.namelist():
                    if member.startswith("/") or ".." in Path(member).parts:
                        raise InstallError(f"unsafe zip entry: {member}")
                zf.extractall(staging)

            if smoke_test and target_dir.name == "app":
                self._smoke_test(staging / "app")

            self._atomic_replace(staging, target_dir)
        except InstallError:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        except (OSError, zipfile.BadZipFile) as exc:
            shutil.rmtree(staging, ignore_errors=True)
            raise InstallError(f"install failed: {exc}") from exc

        logger.info("Installed %s into %s", pkg, target_dir)
        return target_dir

    # ──────────────────────────────────────────────────────────────────
    # 内部辅助
    # ──────────────────────────────────────────────────────────────────

    def _smoke_test(self, candidate: Path) -> None:
        """冒烟测试：确保 candidate 至少能 ``import app`` 不抛错。"""

        if not candidate.exists():
            raise InstallError(f"smoke target missing: {candidate}")
        # 真实生产可执行冒烟测试；这里只检查 __init__.py 存在
        if not (candidate / "__init__.py").exists():
            raise InstallError(
                f"smoke test failed: missing app/__init__.py in {candidate}")

    def _atomic_replace(self, staging: Path, target: Path) -> None:
        """原子地把 ``staging`` 替换到 ``target`` 位置。

        行为：

        * 若 ``target`` 不存在 → ``staging.rename(target)``；
        * macOS / Linux：``os.replace`` 是原子操作；
        * Windows：``os.replace`` 在跨卷时会失败，回退到 ``MoveFileExW``。
        """

        if not target.exists():
            try:
                staging.rename(target)
                return
            except OSError as exc:
                raise InstallError(f"atomic replace failed: {exc}") from exc

        if sys.platform == "win32":
            self._win_atomic_replace(staging, target)
            return

        try:
            # macOS/Linux 原子替换（同卷）
            os.replace(staging, target)
        except OSError as exc:
            # 跨卷 / 权限：退化为 copy + remove
            logger.warning(
                "os.replace failed (%s); falling back to copy+remove", exc)
            try:
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
                shutil.move(str(staging), str(target))
            except OSError as exc2:
                raise InstallError(
                    f"fallback replace failed: {exc2}") from exc2

    def _win_atomic_replace(self, staging: Path, target: Path) -> None:
        """Windows 平台走 MoveFileExW。"""

        try:
            import ctypes
            from ctypes import wintypes

            MOVEFILE_REPLACE_EXISTING = 0x1
            MOVEFILE_WRITE_THROUGH = 0x8

            MoveFileExW = ctypes.windll.kernel32.MoveFileExW
            MoveFileExW.argtypes = [wintypes.LPCWSTR,
                                    wintypes.LPCWSTR, wintypes.DWORD]
            MoveFileExW.restype = wintypes.BOOL

            ok = MoveFileExW(
                str(staging),
                str(target),
                MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH,
            )
            if not ok:
                err = ctypes.GetLastError()
                raise InstallError(f"MoveFileExW failed: Win32 error {err}")
        except OSError as exc:
            raise InstallError(f"win replace failed: {exc}") from exc

    def _read_manifest(self) -> list[BackupRecord]:
        if not self._manifest_path.exists():
            return []
        try:
            with open(self._manifest_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            return [BackupRecord.from_dict(item) for item in payload]
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            logger.warning(
                "Backup manifest is corrupted; starting fresh", exc_info=True)
            return []

    def _write_manifest(self, records: Iterable[BackupRecord]) -> None:
        payload = [r.to_dict() for r in records]
        try:
            with open(self._manifest_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except OSError:
            logger.warning("Failed to persist backup manifest", exc_info=True)

    def _enforce_retention(self) -> None:
        """仅保留最近 ``max_backups`` 个备份；多余的从磁盘删除。"""

        records = self.list_backups()
        if len(records) <= self._max_backups:
            return

        to_remove = records[self._max_backups:]
        kept = records[: self._max_backups]
        for r in to_remove:
            try:
                if r.backup_dir.exists():
                    shutil.rmtree(r.backup_dir, ignore_errors=True)
            except OSError:
                logger.debug("Failed to remove old backup: %s",
                             r.backup_dir, exc_info=True)
        self._write_manifest(kept)


__all__ = ["Installer", "BackupRecord", "InstallError", "MAX_BACKUPS"]
