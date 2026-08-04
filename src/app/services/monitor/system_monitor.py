#!/usr/bin/env python3
"""SystemMonitor · 1Hz 采集系统资源并发布 ``system.metric`` 事件（Phase 2）。

设计要点
---------

* **低开销**：在独立守护线程里以 1Hz 采样 ``psutil``；不阻塞 UI 线程。
* **弱依赖**：``psutil`` 已经在 ``requirements.txt`` 里被现有组件依赖，
  我们把它做成软依赖 —— 缺失时 monitor 仍然能启停，只是所有指标都是 0。
* **零业务耦合**：不缓存也不解读采样值，只通过
  :py:meth:`UnifiedEventBus.publish_event` 投递
  :py:class:`app.core.event_types.SystemMetricSampled` 事件，让
  ViewModel / 日志 / 监盘组件各自订阅。
* **生命周期**::

      monitor = SystemMonitor(event_bus=bus, hz=1.0)
      monitor.start()   # 非阻塞；启动守护线程
      ...
      monitor.stop()    # 线程安全退出，幂等

  与 ``Application`` 服务的 ``start()`` / ``shutdown()`` 命名一致，
  便于挂到 :py:class:`app.core.di_container.DIContainer`。
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import ClassVar

from app.core.event_types import SystemMetricSampled
from app.core.unified_event_bus import UnifiedEventBus

logger = logging.getLogger(__name__)

try:  # pragma: no cover — 在打包环境做软依赖
    import psutil

    _HAS_PSUTIL = True
except Exception:  # noqa: BLE001
    psutil = None
    _HAS_PSUTIL = False

__all__ = ["SystemMonitor"]


class SystemMonitor:
    """1Hz 周期采样 + 事件发布器。

    Parameters
    ----------
    event_bus : UnifiedEventBus
        事件总线；monitor 在每次采样后调用
        :py:meth:`bus.publish_event(SystemMetricSampled(...))`。
    hz : float, default ``1.0``
        采样频率（每秒）。低于 0.2Hz 会被忽略并抛出 ``ValueError``。
    sink : callable, optional
        可选回调 ``(SystemMetricSampled) -> None``。常用于测试 —— 在
        总线之外额外捕获一次采样结果。
    """

    EVENT_NAME: ClassVar[str] = SystemMetricSampled.event_name

    def __init__(
        self,
        event_bus: UnifiedEventBus,
        *,
        hz: float = 1.0,
        sink: Callable[[SystemMetricSampled], None] | None = None,
    ) -> None:
        if event_bus is None:
            raise ValueError("event_bus is required")
        if hz <= 0 or hz > 100:
            raise ValueError(f"hz must be in (0, 100], got {hz!r}")

        self._bus = event_bus
        self._interval = 1.0 / float(hz)
        self._sink = sink

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

        self._published_count = 0
        self._start_time: float | None = None

        # psutil 第一次 ``cpu_percent`` 需要一次 warm-up，让后续采样有意义
        self._cpu_warm = False

    # ──────────────────────────────────────────────────────────
    # 生命周期
    # ──────────────────────────────────────────────────────────

    def start(self) -> bool:
        """启动守护采样线程（幂等）。"""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                logger.debug("SystemMonitor already running")
                return True
            self._stop_event.clear()
            thread = threading.Thread(
                target=self._run,
                name="SystemMonitor",
                daemon=True,
            )
            self._thread = thread
            self._start_time = time.monotonic()
            thread.start()
            return True

    def stop(self, timeout: float = 2.0) -> None:
        """请求线程退出并最多等待 ``timeout`` 秒。"""
        thread = self._thread
        if thread is None:
            return
        self._stop_event.set()
        thread.join(timeout=timeout)
        if thread.is_alive():
            logger.warning("SystemMonitor thread did not exit in time")
        else:
            self._thread = None
            self._start_time = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def published_count(self) -> int:
        return self._published_count

    # ──────────────────────────────────────────────────────────
    # 内部
    # ──────────────────────────────────────────────────────────

    def _run(self) -> None:
        logger.debug(
            "SystemMonitor thread started (interval=%.3fs)", self._interval)
        try:
            while not self._stop_event.is_set():
                loop_start = time.monotonic()
                try:
                    payload = self._sample()
                    self._dispatch(payload)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("SystemMonitor sample failed: %s", exc)

                elapsed = time.monotonic() - loop_start
                sleep_for = max(0.0, self._interval - elapsed)
                if sleep_for > 0:
                    # 用 Event.wait 而不是 sleep，便于响应 stop
                    self._stop_event.wait(sleep_for)
        finally:
            logger.debug("SystemMonitor thread exited")

    def _sample(self) -> SystemMetricSampled:
        """采集一次；psutil 缺失时所有值为 0。"""
        if not _HAS_PSUTIL or psutil is None:
            # 退化：保留事件结构但数值为 0
            return SystemMetricSampled()

        # cpu_percent 第一次返回 0；用 ``interval=None`` 配合预热
        cpu_percent = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        try:
            disk = psutil.disk_usage("/")
        except Exception:  # noqa: BLE001
            disk = None

        proc = psutil.Process()
        try:
            proc_mem_mb = proc.memory_info().rss / (1024 * 1024)
            proc_cpu = proc.cpu_percent(interval=None)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            proc_mem_mb = 0.0
            proc_cpu = 0.0

        return SystemMetricSampled(
            cpu_percent=float(cpu_percent),
            memory_percent=float(mem.percent),
            memory_used_mb=float(mem.used / (1024 * 1024)),
            memory_total_mb=float(mem.total / (1024 * 1024)),
            disk_percent=float(disk.percent) if disk else 0.0,
            disk_used_gb=float(disk.used / (1024 ** 3)) if disk else 0.0,
            disk_total_gb=float(disk.total / (1024 ** 3)) if disk else 0.0,
            process_memory_mb=float(proc_mem_mb),
            process_cpu_percent=float(proc_cpu),
        )

    def _dispatch(self, payload: SystemMetricSampled) -> None:
        self._bus.publish_event(payload)
        self._published_count += 1
        if self._sink is not None:
            try:
                self._sink(payload)
            except Exception as exc:  # noqa: BLE001
                logger.warning("SystemMonitor sink raised: %s", exc)


def build_default_monitor(
    event_bus: UnifiedEventBus,
    *,
    hz: float = 1.0,
) -> SystemMonitor:
    """构造默认 monitor 的工厂方法，便于 DI 容器注册。"""
    return SystemMonitor(event_bus, hz=hz)


# 便于模块级 ``__main__`` 快速冒烟测试
if __name__ == "__main__":  # pragma: no cover
    import sys

    from app.core.unified_event_bus import UnifiedEventBus

    bus = UnifiedEventBus()

    def _print(payload: SystemMetricSampled) -> None:
        print(
            f"[metric] cpu={payload.cpu_percent:5.1f}%  "
            f"mem={payload.memory_percent:5.1f}%  "
            f"disk={payload.disk_percent:5.1f}%",
            flush=True,
        )

    monitor = SystemMonitor(bus, hz=2.0, sink=_print)
    monitor.start()
    try:
        # 默认跑 3 秒（参数可被命令行覆盖）
        duration = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
        time.sleep(duration)
    finally:
        monitor.stop()
