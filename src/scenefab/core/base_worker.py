#!/usr/bin/env python3
"""
统一 Worker 基类 — v2.0 重构

为 SceneFab 中所有耗时操作提供统一基类，封装：
- QThread 生命周期管理
- Signal/Slot 进度回调
- 取消/暂停支持（与 TaskManager 集成）
- 错误传播
- 可选 PySide6 依赖（headless 模式可降级）

使用示例:
    from scenefab.core.base_worker import BaseWorker, WorkerResult

    class MyWorker(BaseWorker):
        def run(self):
            for i in range(100):
                if self.is_cancelled():
                    return
                # ... do work ...
                self.emit_progress(i, 100, f"Step {i+1}")

    worker = MyWorker()
    worker.finished.connect(on_done)
    worker.error.connect(on_error)
    worker.start()
"""

import logging
import threading
import traceback
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


# === 尝试导入 PySide6 ===
try:
    from PySide6.QtCore import QObject, QThread, Signal

    _QT_AVAILABLE = True
except ImportError:
    _QT_AVAILABLE = False
    QObject = object  # type: ignore[misc,assignment]
    QThread = object  # type: ignore[misc,assignment]

    class _DummySignal:  # noqa: D401
        """PySide6 不可用时的占位 Signal"""

        def __init__(self, *args, **kwargs):
            self._handlers = []

        def connect(self, handler):
            self._handlers.append(handler)

        def emit(self, *args):
            for h in self._handlers:
                try:
                    h(*args)
                except Exception as e:
                    logger.error(f"Signal handler error: {e}")

    Signal = _DummySignal  # type: ignore[misc,assignment]


@dataclass
class WorkerResult:
    """Worker 执行结果"""

    success: bool
    data: Any = None
    error: str | None = None
    error_type: str | None = None
    traceback: str | None = None
    duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseWorker(QThread if _QT_AVAILABLE else threading.Thread):  # type: ignore[misc,valid-type]
    """
    统一 Worker 基类

    继承 QThread（PySide6 可用时）或 threading.Thread（headless）

    Signals:
        progress: (current:int, total:int, message:str)
        status: (message:str)
        finished: (WorkerResult)
        error: (error_message:str)
        cancelled: ()
    """

    # Qt Signal 类型定义
    progress: Any = Signal(int, int, str)
    status: Any = Signal(str)
    finished: Any = Signal(object)  # WorkerResult
    error: Any = Signal(str)
    cancelled: Any = Signal()

    def __init__(
        self,
        name: str = "BaseWorker",
        cancellable: bool = True,
        parent: Any = None,
    ) -> None:
        """
        Args:
            name: Worker 名称（用于日志/调试）
            cancellable: 是否支持取消
            parent: Qt 父对象
        """
        if _QT_AVAILABLE:
            QThread.__init__(self, parent)
        else:
            threading.Thread.__init__(self, daemon=True)
        self._name = name
        self._cancellable = cancellable
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # 默认非暂停
        self._result: WorkerResult | None = None
        self._start_time_ms: int = 0

    # ==============================================================
    # 公共 API
    # ==============================================================

    def get_name(self) -> str:
        return self._name

    def is_cancellable(self) -> bool:
        return self._cancellable

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def is_paused(self) -> bool:
        return not self._pause_event.is_set()

    def cancel(self) -> None:
        """请求取消（cooperative cancellation）"""
        if not self._cancellable:
            logger.warning(f"{self._name} is not cancellable, ignoring cancel request")
            return
        logger.info(f"{self._name} cancel requested")
        self._cancel_event.set()
        self.cancelled.emit()

    def pause(self) -> None:
        """请求暂停"""
        if not self._cancellable:
            logger.warning(f"{self._name} does not support pause")
            return
        logger.info(f"{self._name} pause requested")
        self._pause_event.clear()

    def resume(self) -> None:
        """恢复执行"""
        if not self._cancellable:
            return
        logger.info(f"{self._name} resumed")
        self._pause_event.set()

    def wait_pause(self) -> None:
        """如果处于暂停状态则阻塞等待 resume（worker run 内部调用）"""
        self._pause_event.wait()

    def check_cancel_or_pause(self) -> bool:
        """
        配合 cancel/pause 机制的辅助方法

        Returns:
            True 表示已取消（应中止 run），False 表示可继续
        """
        self.wait_pause()  # 暂停时阻塞
        if self.is_cancelled():
            return True
        return False

    def get_result(self) -> WorkerResult | None:
        return self._result

    # ==============================================================
    # Signal 辅助
    # ==============================================================

    def emit_progress(self, current: int, total: int, message: str = "") -> None:
        """发送进度信号"""
        if _QT_AVAILABLE:
            self.progress.emit(current, total, message)
        else:
            for h in self.progress._handlers:
                h(current, total, message)

    def emit_status(self, message: str) -> None:
        """发送状态消息"""
        if _QT_AVAILABLE:
            self.status.emit(message)
        else:
            for h in self.status._handlers:
                h(message)

    # ==============================================================
    # 子类重写
    # ==============================================================

    def run(self) -> None:  # type: ignore[override]
        """
        子类应重写此方法实现具体逻辑

        通过 check_cancel_or_pause() 周期性检查取消/暂停状态
        通过 emit_progress(current, total, message) 报告进度
        """
        raise NotImplementedError("Subclasses must implement run()")

    # ==============================================================
    # 内部执行循环
    # ==============================================================

    def _execute(self) -> None:
        """
        QThread.run() / Thread.run() 的统一入口
        负责异常捕获、结果包装、Signal 发送
        """
        import time

        self._start_time_ms = int(time.time() * 1000)
        try:
            self.run()
            duration = int(time.time() * 1000) - self._start_time_ms
            if self.is_cancelled():
                self._result = WorkerResult(
                    success=False,
                    error="cancelled",
                    error_type="CancelledError",
                    duration_ms=duration,
                )
            else:
                self._result = WorkerResult(
                    success=True,
                    duration_ms=duration,
                )
                if _QT_AVAILABLE:
                    self.finished.emit(self._result)
                else:
                    for h in self.finished._handlers:
                        h(self._result)
        except Exception as e:
            duration = int(time.time() * 1000) - self._start_time_ms
            tb = traceback.format_exc()
            logger.error(f"{self._name} failed: {e}\n{tb}")
            self._result = WorkerResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
                traceback=tb,
                duration_ms=duration,
            )
            if _QT_AVAILABLE:
                self.error.emit(str(e))
            else:
                for h in self.error._handlers:
                    h(str(e))

    def start(self, *args, **kwargs) -> None:  # type: ignore[override]
        """启动 Worker"""
        if _QT_AVAILABLE:
            QThread.start(self)
        else:
            # 包装 run 调用，注入 _execute 异常处理
            original_run = self.run

            def wrapped_run():
                # 用 _execute 的异常处理逻辑
                self._execute()

            self.run = wrapped_run
            threading.Thread.start(self)


__all__ = [
    "BaseWorker",
    "WorkerResult",
]
