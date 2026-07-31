"""升级服务主控（``UpdaterService``）。

设计要点：

* 自身是 ``QObject``，所有 UI 状态变更通过 Qt Signal 推送，
  这样调用方无需关心线程边界；
* 复用现有 :mod:`app.update.checker` 做版本检测；
  复用 :mod:`app.core.audit` 写审计；
* 长任务（下载 / 校验 / 安装 / 回滚）放到 :class:`app.core.base_worker.BaseWorker`
  的子类中，避免阻塞 GUI 主线程；
* 暴露 ``UpdaterState`` 枚举作为状态机的快照，
  任何回调都可以直接读取 ``service.state`` 而无需订阅完整信号链。
"""

from __future__ import annotations

import logging
import shutil
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import httpx

from app.updater.downloader import DownloadError, Downloader, DownloadProgress
from app.updater.installer import BackupRecord, Installer, InstallError
from app.updater.manifest import (
    UpdateChannel,
    UpdateManifest,
    parse_release_manifest,
    select_best_manifest,
)
from app.updater.verifier import VerificationError, verify_sha256


logger = logging.getLogger(__name__)


GITHUB_API_RELEASES_LATEST = (
    "https://api.github.com/repos/Agions/scene-fab/releases/latest"
)


class UpdateStage(str, Enum):
    """升级阶段标签（用于 UI 状态机映射）。"""

    IDLE = "idle"
    CHECKING = "checking"
    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    INSTALLING = "installing"
    DONE = "done"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class UpdaterState:
    """当前升级服务状态（线程安全快照）。"""

    stage: UpdateStage = UpdateStage.IDLE
    manifest: UpdateManifest | None = None
    progress_percent: float = 0.0
    progress_speed_bps: float = 0.0
    last_error: str = ""
    backup_record: BackupRecord | None = None


# ──────────────────────────────────────────────────────────────────────
# PySide6 信号（懒导入）
# ──────────────────────────────────────────────────────────────────────


def _build_signals() -> Any:
    """懒加载 :class:`PySide6.QtCore.QObject` 信号定义。"""

    try:
        from PySide6.QtCore import QObject, Signal
    except ImportError:
        return None

    class _Signals(QObject):
        stage_changed = Signal(str)              # UpdateStage
        progress_changed = Signal(int, str)      # percent (0-100), message
        update_available = Signal(object)        # UpdateManifest
        update_unavailable = Signal()
        install_complete = Signal(str)           # new version
        rolled_back = Signal(str)                # recovered version
        error_occurred = Signal(str, str)        # code, message

    return _Signals()


class UpdaterService:
    """升级服务主控。

    用法::

        service = UpdaterService(
            channel=UpdateChannel.STABLE,
            download_cache=Path("~/.cache/scenefab/updates").expanduser(),
            app_dir=Path("src/app"),
        )
        service.stage_changed.connect(...)
        service.progress_changed.connect(...)

        # 1) 检测
        manifest = service.check()

        # 2) 安装（异步推送进度）
        service.download_and_install(manifest)

        # 3) 回滚（任意时刻）
        service.rollback_to(manifest.version)
    """

    def __init__(
        self,
        *,
        channel: UpdateChannel = UpdateChannel.STABLE,
        download_cache: Path | None = None,
        app_dir: Path | None = None,
        current_version: str | None = None,
        api_url: str = GITHUB_API_RELEASES_LATEST,
        auto_fallback_full: bool = True,
    ) -> None:
        self._channel = channel
        self._download_cache = (
            Path(download_cache).expanduser()
            if download_cache is not None
            else Path.home() / ".cache" / "scenefab" / "updates"
        )
        self._download_cache.mkdir(parents=True, exist_ok=True)
        self._app_dir = (
            Path(app_dir) if app_dir is not None else self._guess_app_dir()
        )
        self._api_url = api_url
        self._auto_fallback_full = auto_fallback_full

        # current_version 可能晚于实例化注入（首启动时 update.checker 已就绪）
        if current_version is None:
            from app.utils.version import get_version_string

            current_version = get_version_string()
        self._current_version = current_version

        self._signals = _build_signals()
        self._state = UpdaterState()
        self._state_lock = threading.Lock()

        self._downloader = Downloader()
        self._installer = Installer()

    # ──────────────────────────────────────────────────────────────────
    # 公共属性
    # ──────────────────────────────────────────────────────────────────

    @property
    def state(self) -> UpdaterState:
        """获取当前状态快照（线程安全）。"""

        with self._state_lock:
            return UpdaterState(
                stage=self._state.stage,
                manifest=self._state.manifest,
                progress_percent=self._state.progress_percent,
                progress_speed_bps=self._state.progress_speed_bps,
                last_error=self._state.last_error,
                backup_record=self._state.backup_record,
            )

    @property
    def signals(self) -> Any:
        """暴露 :class:`QObject` 信号（可能为 None 当 PySide6 不可用）。"""

        return self._signals

    # 为常见信号提供便捷属性访问（IDE 自动补全友好）
    if True:  # 始终定义（运行时由 _signals 是否存在决定是否可用）

        @property
        def stage_changed(self) -> Any:
            return getattr(self._signals, "stage_changed", None)

        @property
        def progress_changed(self) -> Any:
            return getattr(self._signals, "progress_changed", None)

        @property
        def update_available(self) -> Any:
            return getattr(self._signals, "update_available", None)

        @property
        def update_unavailable(self) -> Any:
            return getattr(self._signals, "update_unavailable", None)

        @property
        def install_complete(self) -> Any:
            return getattr(self._signals, "install_complete", None)

        @property
        def rolled_back(self) -> Any:
            return getattr(self._signals, "rolled_back", None)

        @property
        def error_occurred(self) -> Any:
            return getattr(self._signals, "error_occurred", None)

    # ──────────────────────────────────────────────────────────────────
    # 检测
    # ──────────────────────────────────────────────────────────────────

    def check(self, *, timeout: float = 10.0) -> UpdateManifest | None:
        """从 GitHub Releases 查询最新版本；返回最佳 manifest 或 None。"""

        self._emit_stage(UpdateStage.CHECKING)
        try:
            payload = self._fetch_release_payload(timeout=timeout)
        except (httpx.HTTPError, OSError) as exc:
            logger.warning("Update check failed: %s", exc)
            self._emit_error("UPDATE_CHECK_FAILED", str(exc))
            self._emit_stage(UpdateStage.FAILED)
            return None

        manifests = parse_release_manifest(payload, self._channel)
        manifest = select_best_manifest(manifests, self._current_version)
        if manifest is None:
            self._emit_stage(UpdateStage.IDLE)
            if self.update_unavailable is not None:
                self.update_unavailable.emit()
            return None

        with self._state_lock:
            self._state.manifest = manifest
            self._state.last_error = ""
        self._emit_stage(UpdateStage.AVAILABLE)
        if self.update_available is not None:
            self.update_available.emit(manifest)
        return manifest

    # ──────────────────────────────────────────────────────────────────
    # 下载 + 安装
    # ──────────────────────────────────────────────────────────────────

    def download_and_install(
        self,
        manifest: UpdateManifest | None = None,
        *,
        worker: Any | None = None,
    ) -> bool:
        """下载并安装指定 manifest（默认使用最近一次 check 的结果）。

        Args:
            manifest: 要安装的清单；None 时使用 ``state.manifest``。
            worker: 可选 ``BaseWorker`` 实例，用于上报进度（见
                :meth:`_report_progress`）。

        Returns:
            True 表示安装成功，False 表示失败或回滚后失败。
        """

        target_manifest = manifest or self.state.manifest
        if target_manifest is None:
            self._emit_error("NO_MANIFEST", "no manifest provided")
            self._emit_stage(UpdateStage.FAILED)
            return False

        try:
            self._stage_download(target_manifest, worker=worker)
            self._stage_verify(target_manifest, worker=worker)
            backup = self._stage_backup()
            self._stage_install(target_manifest, backup, worker=worker)
        except (DownloadError, VerificationError, InstallError, OSError) as exc:
            logger.exception("Update flow failed")
            self._emit_error("UPDATE_FAILED", str(exc))
            self._emit_stage(UpdateStage.FAILED)
            return False

        with self._state_lock:
            self._current_version = target_manifest.version
            self._state.stage = UpdateStage.DONE
            self._state.progress_percent = 100.0
        self._emit_stage(UpdateStage.DONE)
        if self.install_complete is not None:
            self.install_complete.emit(target_manifest.version)
        return True

    # ──────────────────────────────────────────────────────────────────
    # 回滚
    # ──────────────────────────────────────────────────────────────────

    def rollback_to(self, version: str | None = None) -> bool:
        """回滚到指定版本（默认最近一次备份）。"""

        records = self._installer.list_backups()
        if not records:
            self._emit_error("NO_BACKUP", "no backup available")
            return False

        target = None
        if version is not None:
            for r in records:
                if r.version == version:
                    target = r
                    break
        if target is None:
            target = records[0]

        try:
            self._installer.rollback(target)
        except InstallError as exc:
            self._emit_error("ROLLBACK_FAILED", str(exc))
            return False

        with self._state_lock:
            self._current_version = target.version
            self._state.backup_record = target
            self._state.stage = UpdateStage.ROLLED_BACK
            self._state.last_error = ""
        self._emit_stage(UpdateStage.ROLLED_BACK)
        if self.rolled_back is not None:
            self.rolled_back.emit(target.version)
        return True

    # ──────────────────────────────────────────────────────────────────
    # 阶段实现
    # ──────────────────────────────────────────────────────────────────

    def _stage_download(
        self,
        manifest: UpdateManifest,
        *,
        worker: Any | None,
    ) -> Path:
        """下载到 download_cache，返回本地路径。"""

        self._emit_stage(UpdateStage.DOWNLOADING)
        dest = self._download_cache / manifest.asset_name

        # 当 dest 已存在且 sha256 已匹配时直接跳过
        if dest.exists() and verify_sha256(dest, manifest.sha256):
            self._report_progress(100.0, "download cached", worker=worker)
            return dest

        def _on_progress(progress: DownloadProgress) -> None:
            self._report_progress(
                progress.percent, "downloading", worker=worker)
            with self._state_lock:
                self._state.progress_speed_bps = progress.speed_bps

        try:
            return self._downloader.download(
                manifest.download_url, dest, on_progress=_on_progress
            )
        except DownloadError as exc:
            # 自动 fallback 完整包
            if (
                self._auto_fallback_full
                and manifest.is_delta
            ):
                logger.warning(
                    "delta download failed (%s); falling back to full package", exc
                )
                fallback = self._find_full_manifest(manifest)
                if fallback is not None:
                    with self._state_lock:
                        self._state.manifest = fallback
                    return self._stage_download(fallback, worker=worker)
            raise

    def _stage_verify(
        self,
        manifest: UpdateManifest,
        *,
        worker: Any | None,
    ) -> None:
        """校验下载包 sha256。"""

        self._emit_stage(UpdateStage.VERIFYING)
        self._report_progress(0.0, "verifying sha256", worker=worker)
        pkg = self._download_cache / manifest.asset_name
        try:
            verify_sha256(pkg, manifest.sha256)
        except VerificationError:
            # 校验失败：尝试 fallback 到完整包
            if (
                self._auto_fallback_full
                and manifest.is_delta
                and pkg.exists()
            ):
                try:
                    pkg.unlink()
                except OSError:
                    pass
                fallback = self._find_full_manifest(manifest)
                if fallback is not None:
                    logger.info(
                        "delta verification failed; falling back to full")
                    with self._state_lock:
                        self._state.manifest = fallback
                    self._stage_download(fallback, worker=worker)
                    self._stage_verify(fallback, worker=worker)
                    return
            raise

        self._report_progress(100.0, "verified", worker=worker)

    def _stage_backup(self) -> BackupRecord:
        """在安装前备份当前 ``app_dir``。"""

        if self._app_dir is None or not self._app_dir.exists():
            raise InstallError(f"app_dir unavailable: {self._app_dir}")

        record = self._installer.backup_current(
            app_dir=self._app_dir,
            current_version=self._current_version,
        )
        with self._state_lock:
            self._state.backup_record = record
        return record

    def _stage_install(
        self,
        manifest: UpdateManifest,
        backup: BackupRecord,
        *,
        worker: Any | None,
    ) -> None:
        """执行原子化安装。"""

        if self._app_dir is None:
            raise InstallError("app_dir unknown")

        self._emit_stage(UpdateStage.INSTALLING)
        self._report_progress(0.0, "extracting", worker=worker)
        pkg = self._download_cache / manifest.asset_name
        try:
            self._installer.install(pkg=pkg, target_dir=self._app_dir)
        except InstallError:
            # 失败自动回滚
            try:
                self._installer.rollback(backup, target_dir=self._app_dir)
            except InstallError as rb_exc:
                logger.error("Rollback failed: %s", rb_exc)
            raise

        self._report_progress(100.0, "installed", worker=worker)

    # ──────────────────────────────────────────────────────────────────
    # 内部辅助
    # ──────────────────────────────────────────────────────────────────

    def _find_full_manifest(
        self, delta: UpdateManifest
    ) -> UpdateManifest | None:
        """在最新 release 中找与 delta 同版本的完整包 manifest。"""

        try:
            payload = self._fetch_release_payload(timeout=10.0)
        except (httpx.HTTPError, OSError):
            return None
        for m in parse_release_manifest(payload, self._channel):
            if not m.is_delta and m.version == delta.version and m.sha256:
                return m
        return None

    def _fetch_release_payload(self, *, timeout: float) -> dict[str, Any]:
        """从 GitHub API 拉取 release JSON。"""

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SceneFab-Updater/1.0",
        }
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(self._api_url, headers=headers)
        response.raise_for_status()
        return response.json()

    def _report_progress(
        self,
        percent: float,
        message: str,
        *,
        worker: Any | None,
    ) -> None:
        """同时推 Qt Signal + Worker 进度（如果提供）。"""

        with self._state_lock:
            self._state.progress_percent = percent
        if self.progress_changed is not None:
            try:
                self.progress_changed.emit(int(percent), message)
            except (RuntimeError, TypeError):
                pass
        if worker is not None and hasattr(worker, "emit_progress"):
            try:
                total = 100 if percent > 0 else 0
                worker.emit_progress(int(percent), total, message)
            except (RuntimeError, TypeError):
                pass

    def _emit_stage(self, stage: UpdateStage) -> None:
        with self._state_lock:
            self._state.stage = stage
        if self.stage_changed is not None:
            try:
                self.stage_changed.emit(stage.value)
            except (RuntimeError, TypeError):
                pass

    def _emit_error(self, code: str, message: str) -> None:
        with self._state_lock:
            self._state.last_error = f"{code}: {message}"
        if self.error_occurred is not None:
            try:
                self.error_occurred.emit(code, message)
            except (RuntimeError, TypeError):
                pass

    @staticmethod
    def _guess_app_dir() -> Path | None:
        """尽力猜测当前 ``app/`` 源码目录；找不到返回 None。"""

        # 兼容源码运行 / 安装包运行两种情况
        candidates: list[Path] = []
        try:
            import app as _app_pkg

            pkg_path = Path(getattr(_app_pkg, "__file__", "")).resolve()
            if pkg_path.name == "__init__.py":
                candidates.append(pkg_path.parent)
        except (ImportError, AttributeError):
            pass

        cwd_app = Path.cwd() / "src" / "app"
        if cwd_app.exists():
            candidates.append(cwd_app)

        return candidates[0] if candidates else None

    # ──────────────────────────────────────────────────────────────────
    # 兼容旧 :func:`app.update.check_update` 的便捷封装
    # ──────────────────────────────────────────────────────────────────

    @classmethod
    def from_settings(
        cls,
        settings_manager: Any | None = None,
        **kwargs: Any,
    ) -> "UpdaterService":
        """从 ``ProjectSettingsManager`` 读 channel 配置后构造实例。"""

        channel = UpdateChannel.STABLE
        try:
            if settings_manager is not None:
                raw = settings_manager.get_setting("update.channel")
                if isinstance(raw, str) and raw in {c.value for c in UpdateChannel}:
                    channel = UpdateChannel(raw)
        except (AttributeError, KeyError):
            pass

        app_dir = cls._guess_app_dir()
        return cls(channel=channel, app_dir=app_dir, **kwargs)

    def cleanup_downloads(self, *, keep: int = 5) -> int:
        """清理 :attr:`_download_cache` 中除当前 manifest 外的旧文件。"""

        keep_names: set[str] = set()
        if self.state.manifest is not None:
            keep_names.add(self.state.manifest.asset_name)

        removed = 0
        for entry in self._download_cache.iterdir():
            if entry.name in keep_names or entry.name.startswith("."):
                continue
            try:
                if entry.is_dir():
                    shutil.rmtree(entry)
                else:
                    entry.unlink()
                removed += 1
            except OSError as exc:
                logger.debug("Failed to remove %s: %s", entry, exc)
        return removed


# 兼容旧版 :mod:`app.update.checker` 的导出别名
def check_update_via_service(
    service: UpdaterService | None = None,
    **kwargs: Any,
) -> UpdateManifest | None:
    """便捷封装：复用现有 service 或临时构造一个。"""

    svc = service or UpdaterService(**kwargs)
    return svc.check()


__all__ = [
    "UpdaterService",
    "UpdaterState",
    "UpdateStage",
    "GITHUB_API_RELEASES_LATEST",
    "check_update_via_service",
]
