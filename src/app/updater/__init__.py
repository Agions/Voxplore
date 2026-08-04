"""SceneFab 自动升级模块（v2.5 新增）。

提供检测、增量下载、SHA256 校验、原子化安装、回滚的完整闭环：

    from app.updater import UpdaterService, UpdateChannel

    svc = UpdaterService(channel=UpdateChannel.STABLE)
    info = svc.check()                       # 异步 / 同步可切换
    if info is not None:
        svc.download_and_install(info)       # 进度通过 Qt Signal 推送

设计要点：

* 单例友好：模块不强制单例，调用方可按进程注入到 DI 容器；
* 线程模型：``UpdaterService`` 自身是 ``QObject``，长任务在 ``QThread`` 中执行；
* 强校验：所有下载包必走 SHA256 校验，失败自动 fallback 到完整包；
* 原子化替换：macOS/Linux 通过临时目录 + ``os.replace`` 原子切换；
  Windows 通过 ``ctypes`` 调用 ``MoveFileExW(..., MOVEFILE_REPLACE_EXISTING |
  MOVEFILE_WRITE_THROUGH)``；
* 回滚：升级前备份当前 ``app/`` 目录到 ``~/.cache/scenefab/backups/``；
  仅保留最近 3 个版本以避免磁盘膨胀。
"""

from __future__ import annotations

from app.updater.downloader import (
    Downloader,
    DownloadError,
    DownloadProgress,
)
from app.updater.installer import BackupRecord, Installer, InstallError
from app.updater.manifest import (
    UpdateChannel,
    UpdateManifest,
    parse_release_manifest,
    select_best_manifest,
)
from app.updater.service import (
    UpdaterService,
    UpdaterState,
    UpdateStage,
)
from app.updater.verifier import VerificationError, verify_sha256

__all__ = [
    # manifest
    "UpdateChannel",
    "UpdateManifest",
    "parse_release_manifest",
    "select_best_manifest",
    # downloader
    "Downloader",
    "DownloadProgress",
    "DownloadError",
    # verifier
    "verify_sha256",
    "VerificationError",
    # installer
    "Installer",
    "BackupRecord",
    "InstallError",
    # service
    "UpdaterService",
    "UpdaterState",
    "UpdateStage",
]
