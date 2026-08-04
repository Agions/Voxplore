#!/usr/bin/env python3
"""DashboardViewModel · Phase 2 Dashboard 后端。

职责
----

1. **复用 HomeViewModel 的 4 个 KPI**（media / scene / script / export）——
   但仅 *委托* 调用而非继承，因为 Dashboard 的 KPI 顺序与原
   HomePage 不同，需要独立的 emit 信号集合。
2. **订阅 ``system.metric`` 事件**，把 1Hz 的 CPU / 内存 / 磁盘
   实时数值以 Qt Property 形式暴露给 View。
3. **维护 60 个样本的环形 buffer** 用于折线图：把 1Hz 的 CPU /
   memory 历史聚合成两个 ``tuple[float, ...]`` 暴露给 View 即可
   （视图层 ``LineChart.extend_samples`` 接受可迭代对象）。
4. **暴露简单业务指标**（最近项目数 / 当前任务统计）便于 4 象限布局。

设计要点
--------

* VM 接收可选 :py:class:`app.application.Application`；当未传入时
  所有指标退化为零，单元测试不依赖任何 DI 容器也能跑通。
* 不在 VM 里持有 Qt 句柄；它只暴露 *属性* 与 *Signal*，由
  :py:class:`app.ui.main.pages.home_page.DashboardPage` 负责绑定
  到 GlassCard / RingChart / LineChart。
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from PySide6.QtCore import Signal

from app.core.event_types import SystemMetricSampled
from app.ui.viewmodels import ViewModelBase

if TYPE_CHECKING:
    from app.application import Application
    from app.core.unified_event_bus import UnifiedEventBus


__all__ = ["DashboardViewModel"]


class DashboardViewModel(ViewModelBase):
    """Dashboard 综合 VM。

    Properties
    ----------
    KPI（项目维度）
        media_count : int
        scene_count : int
        script_status : str
        export_config : str

    系统指标
        cpu_percent : float
        memory_percent : float
        memory_used_mb : float
        memory_total_mb : float
        disk_percent : float
        process_memory_mb : float

    历史曲线（最近 HISTORY_CAPACITY 个样本）
        cpu_history : tuple[float, ...]
        memory_history : tuple[float, ...]
    """

    HISTORY_CAPACITY: int = 60  # 1Hz × 60s

    # ── 项目 KPI 信号 ──
    media_count_changed = Signal()
    scene_count_changed = Signal()
    script_status_changed = Signal()
    export_config_changed = Signal()
    recent_projects_changed = Signal()

    # ── 系统指标信号 ──
    cpu_percent_changed = Signal()
    memory_percent_changed = Signal()
    memory_used_mb_changed = Signal()
    memory_total_mb_changed = Signal()
    disk_percent_changed = Signal()
    process_memory_mb_changed = Signal()
    history_changed = Signal()

    def __init__(self, application: Application | None = None, parent=None) -> None:
        super().__init__(application, parent)

        # KPI 字段
        self._media_count = 0
        self._scene_count = 0
        self._script_status = "待生成"
        self._export_config = "1080x1920"
        self._recent_projects: list[str] = []

        # 系统指标
        self._cpu_percent = 0.0
        self._memory_percent = 0.0
        self._memory_used_mb = 0.0
        self._memory_total_mb = 0.0
        self._disk_percent = 0.0
        self._process_memory_mb = 0.0

        # 环形缓冲
        self._cpu_history: deque[float] = deque(maxlen=self.HISTORY_CAPACITY)
        self._mem_history: deque[float] = deque(maxlen=self.HISTORY_CAPACITY)

        # 内部状态
        self._pm_bound = False
        self._bus_unsubscribe: Callable[[], None] | None = None

    # ───────────────────────────────────────────────
    #  属性
    # ───────────────────────────────────────────────

    @property
    def media_count(self) -> int: return self._media_count

    @property
    def scene_count(self) -> int: return self._scene_count

    @property
    def script_status(self) -> str: return self._script_status

    @property
    def export_config(self) -> str: return self._export_config

    @property
    def recent_projects(self) -> list[str]: return list(self._recent_projects)

    @property
    def cpu_percent(self) -> float: return self._cpu_percent

    @property
    def memory_percent(self) -> float: return self._memory_percent

    @property
    def memory_used_mb(self) -> float: return self._memory_used_mb

    @property
    def memory_total_mb(self) -> float: return self._memory_total_mb

    @property
    def disk_percent(self) -> float: return self._disk_percent

    @property
    def process_memory_mb(self) -> float: return self._process_memory_mb

    @property
    def cpu_history(self) -> Sequence[float]:
        return tuple(self._cpu_history)

    @property
    def memory_history(self) -> Sequence[float]:
        return tuple(self._mem_history)

    @property
    def is_metric_connected(self) -> bool:
        return self._bus_unsubscribe is not None

    # ───────────────────────────────────────────────
    #  生命周期
    # ───────────────────────────────────────────────

    def bind(self) -> None:
        """订阅项目信号 + ``system.metric`` 事件。"""
        if self._pm_bound:
            return

        self._connect_and_seed(
            {
                "project_opened": lambda pid: self._refresh_from_project(),
                "project_closed": lambda pid: self._reset_kpi(),
                "project_saved": lambda pid: self._refresh_from_project(),
                "project_deleted": lambda pid: self._reset_kpi(),
                "recent_projects_updated": self._on_recent_updated,
            }
        )

        # system.metric 事件 — 由 SystemMonitor 1Hz 推送
        bus = self._event_bus()
        if bus is not None:
            self._bus_unsubscribe = bus.subscribe(
                SystemMetricSampled.event_name,
                self._on_system_metric,
                name="dashboard_viewmodel",
            )

        self._refresh_from_project()
        self._pm_bound = True

    def unbind(self) -> None:
        if not self._pm_bound:
            return
        self._unbind_pm_signals(
            {
                "project_opened": lambda pid: self._refresh_from_project(),
                "project_closed": lambda pid: self._reset_kpi(),
                "project_saved": lambda pid: self._refresh_from_project(),
                "project_deleted": lambda pid: self._reset_kpi(),
                "recent_projects_updated": self._on_recent_updated,
            }
        )
        if self._bus_unsubscribe is not None:
            self._bus_unsubscribe()
            self._bus_unsubscribe = None
        self._pm_bound = False

    # ───────────────────────────────────────────────
    #  KPI 事件
    # ───────────────────────────────────────────────

    def _refresh_from_project(self) -> None:
        project = self._current_project()
        if project is None:
            self._reset_kpi()
            return
        self._set_media(len(project.media_files))
        timeline = project.timeline
        scene_count = len(timeline.tracks) if timeline is not None else 0
        self._set_scenes(scene_count)
        self._set_script_status("已生成" if scene_count > 0 else "待生成")
        settings = project.settings
        resolution = getattr(settings, "resolution", None) or "1080x1920"
        fps = getattr(settings, "fps", None) or 30
        bitrate = getattr(settings, "bitrate", None) or "8000k"
        self._set_export_config(f"{resolution} · {fps}fps · {bitrate}")

    def _on_recent_updated(self, recents: list) -> None:
        self._recent_projects = list(recents) if recents else []
        self.recent_projects_changed.emit()

    def _reset_kpi(self) -> None:
        self._set_media(0)
        self._set_scenes(0)
        self._set_script_status("待生成")
        self._set_export_config("1080x1920")

    # ───────────────────────────────────────────────
    #  系统指标事件
    # ───────────────────────────────────────────────

    def _on_system_metric(self, payload) -> None:
        """``system.metric`` 事件回调。"""
        # 容忍 dict / dataclass 两种入参形式
        if isinstance(payload, SystemMetricSampled):
            cpu = float(payload.cpu_percent)
            mem = float(payload.memory_percent)
            mem_used = float(payload.memory_used_mb)
            mem_total = float(payload.memory_total_mb)
            disk = float(payload.disk_percent)
            proc_mem = float(payload.process_memory_mb)
        elif isinstance(payload, dict):
            cpu = float(payload.get("cpu_percent", 0.0))
            mem = float(payload.get("memory_percent", 0.0))
            mem_used = float(payload.get("memory_used_mb", 0.0))
            mem_total = float(payload.get("memory_total_mb", 0.0))
            disk = float(payload.get("disk_percent", 0.0))
            proc_mem = float(payload.get("process_memory_mb", 0.0))
        else:
            return

        changed = False

        # 先 append 再 emit，保证 ``emit`` 触发的回调能读到最新历史。
        self._cpu_history.append(cpu)
        self._mem_history.append(mem)

        if cpu != self._cpu_percent:
            self._cpu_percent = cpu
            self.cpu_percent_changed.emit()
            changed = True

        if mem != self._memory_percent:
            self._memory_percent = mem
            self.memory_percent_changed.emit()
            changed = True

        if abs(mem_used - self._memory_used_mb) > 1e-3:
            self._memory_used_mb = mem_used
            self.memory_used_mb_changed.emit()
        if abs(mem_total - self._memory_total_mb) > 1e-3:
            self._memory_total_mb = mem_total
            self.memory_total_mb_changed.emit()
        if abs(disk - self._disk_percent) > 1e-3:
            self._disk_percent = disk
            self.disk_percent_changed.emit()
        if abs(proc_mem - self._process_memory_mb) > 1e-3:
            self._process_memory_mb = proc_mem
            self.process_memory_mb_changed.emit()

        if changed:
            self.history_changed.emit()

    # 注入测试样本（单元测试时使用）
    def inject_metric(
        self,
        *,
        cpu_percent: float,
        memory_percent: float,
        memory_used_mb: float | None = None,
        memory_total_mb: float | None = None,
        disk_percent: float | None = None,
        process_memory_mb: float | None = None,
    ) -> None:
        """直接灌一组样本，跳过事件总线（仅供测试）。"""
        self._on_system_metric(
            SystemMetricSampled(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb or 0.0,
                memory_total_mb=memory_total_mb or 0.0,
                disk_percent=disk_percent or 0.0,
                process_memory_mb=process_memory_mb or 0.0,
            )
        )

    # ───────────────────────────────────────────────
    #  内部 setter（带 dedup）
    # ───────────────────────────────────────────────

    def _set_media(self, n: int) -> None:
        if n != self._media_count:
            self._media_count = n
            self.media_count_changed.emit()

    def _set_scenes(self, n: int) -> None:
        if n != self._scene_count:
            self._scene_count = n
            self.scene_count_changed.emit()

    def _set_script_status(self, s: str) -> None:
        if s != self._script_status:
            self._script_status = s
            self.script_status_changed.emit()

    def _set_export_config(self, s: str) -> None:
        if s != self._export_config:
            self._export_config = s
            self.export_config_changed.emit()

    # ───────────────────────────────────────────────
    #  application helpers
    # ───────────────────────────────────────────────

    def _event_bus(self) -> UnifiedEventBus | None:
        app = self._application
        if app is None:
            return None
        bus = app.get_service_by_name("event_bus")
        if bus is not None:
            return bus
        # 兜底：DI 全局
        try:
            from app.core.unified_event_bus import get_event_bus

            return get_event_bus()
        except Exception:  # noqa: BLE001
            return None
