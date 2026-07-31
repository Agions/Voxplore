"""升级包下载器。

支持流式下载 + 进度回调 + 断点续传。

进度计算：

* 通过响应头 ``Content-Length`` 拿到总字节数；
* 每次读 chunk 时累加 ``bytes_done``；
* 进度回调签名 ``(bytes_done: int, total: int | None, speed_bps: float)``；
* UI 层把 ``bytes_done / total`` 渲染为百分比。

断点续传：

* 若目标文件已存在且服务端支持 ``Range``，从已下载字节处续传；
* 若服务端返回 ``416 Range Not Satisfiable``，视为已完成（已下载 = 完整）。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx


logger = logging.getLogger(__name__)

ProgressCallback = Callable[["DownloadProgress"], None]


class DownloadError(RuntimeError):
    """下载失败（含网络错误、超时、HTTP 非 2xx）。"""


@dataclass
class DownloadProgress:
    """下载进度快照。"""

    bytes_done: int
    total_bytes: int | None
    speed_bps: float  # bytes / second
    started_at: float

    @property
    def percent(self) -> float:
        if not self.total_bytes or self.total_bytes <= 0:
            return 0.0
        return min(100.0, self.bytes_done * 100.0 / self.total_bytes)


class Downloader:
    """流式 HTTP 下载器。

    线程安全：单实例不应在多个线程同时调用 ``download``。
    """

    DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
    DEFAULT_CHUNK = 64 * 1024  # 64 KiB

    def __init__(
        self,
        *,
        timeout: httpx.Timeout | None = None,
        chunk_size: int = DEFAULT_CHUNK,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._timeout = timeout or self.DEFAULT_TIMEOUT
        self._chunk_size = chunk_size
        self._headers = {
            "User-Agent": "SceneFab-Updater/1.0",
            "Accept": "application/octet-stream",
            **(headers or {}),
        }

    def download(
        self,
        url: str,
        dest: Path,
        *,
        on_progress: ProgressCallback | None = None,
        resume: bool = True,
    ) -> Path:
        """下载 ``url`` 到 ``dest``，返回最终路径。

        Args:
            url: 远程 URL。
            dest: 本地目标文件路径；父目录会自动创建。
            on_progress: 进度回调（可选）。
            resume: 是否启用断点续传（仅当目标文件已存在时生效）。

        Raises:
            DownloadError: 网络错误或非 2xx 响应。
        """
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)

        existing = dest.stat().st_size if (resume and dest.exists()) else 0
        headers = dict(self._headers)
        if existing > 0:
            headers["Range"] = f"bytes={existing}-"

        started_at = time.perf_counter()
        last_emit = started_at
        last_bytes = existing

        try:
            with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
                with client.stream("GET", url, headers=headers) as response:
                    status = response.status_code

                    # 服务端不支持 Range → 重头下载
                    if status == 200 and existing > 0:
                        existing = 0
                        dest.unlink(missing_ok=True)
                    if status == 416:
                        # 已下载完成
                        if on_progress:
                            total = int(response.headers.get(
                                "Content-Length", existing))
                            on_progress(
                                DownloadProgress(
                                    bytes_done=existing,
                                    total_bytes=total or existing,
                                    speed_bps=0.0,
                                    started_at=started_at,
                                )
                            )
                        return dest
                    if status not in (200, 206):
                        raise DownloadError(
                            f"HTTP {status} downloading {url}: "
                            f"{response.headers.get('content-type', '')}"
                        )

                    total_header = response.headers.get("Content-Length")
                    # 206 响应 Content-Length 表示剩余字节数；与 existing 相加得到完整大小
                    if status == 206 and total_header:
                        total_bytes = int(total_header) + existing
                    else:
                        total_bytes = int(
                            total_header) if total_header else None

                    mode = "ab"
                    open_file = dest.open(mode)

                    try:
                        bytes_done = existing
                        with open_file as f:
                            for chunk in response.iter_bytes(chunk_size=self._chunk_size):
                                if not chunk:
                                    continue
                                f.write(chunk)
                                bytes_done += len(chunk)

                                now = time.perf_counter()
                                if on_progress is not None and (now - last_emit) >= 0.2:
                                    speed = (bytes_done - last_bytes) / \
                                        max(now - last_emit, 1e-6)
                                    on_progress(
                                        DownloadProgress(
                                            bytes_done=bytes_done,
                                            total_bytes=total_bytes,
                                            speed_bps=speed,
                                            started_at=started_at,
                                        )
                                    )
                                    last_emit = now
                                    last_bytes = bytes_done
                    finally:
                        if not f.closed:
                            f.close()

            if on_progress is not None:
                on_progress(
                    DownloadProgress(
                        bytes_done=bytes_done,
                        total_bytes=total_bytes or bytes_done,
                        speed_bps=0.0,
                        started_at=started_at,
                    )
                )

            return dest

        except httpx.HTTPError as exc:
            logger.warning("Download failed for %s: %s", url, exc)
            raise DownloadError(f"network error: {exc}") from exc
        except OSError as exc:
            raise DownloadError(f"io error: {exc}") from exc


__all__ = ["Downloader", "DownloadProgress", "DownloadError"]
