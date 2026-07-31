"""Tests for Phase 2 services (SystemMonitor) and dashboard VM."""

from __future__ import annotations

import os
import time

import pytest

PySide6 = pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


# ────────────────────────────────────────────────────────────────
#  SystemMonitor
# ────────────────────────────────────────────────────────────────


def test_system_monitor_publishes_system_metric(qt_app: QApplication) -> None:
    from app.core.event_types import SystemMetricSampled
    from app.core.unified_event_bus import UnifiedEventBus
    from app.services.monitor import SystemMonitor

    bus = UnifiedEventBus()
    received: list[SystemMetricSampled] = []
    bus.subscribe(SystemMetricSampled.event_name, lambda p: received.append(p))

    monitor = SystemMonitor(bus, hz=20.0)
    monitor.start()
    try:
        # 20Hz × 0.3s ≈ 6 samples (allow ≥3 for slow CI runners)
        time.sleep(0.3)
    finally:
        monitor.stop()
    assert monitor.published_count >= 3
    assert len(received) == monitor.published_count
    assert all(isinstance(p, SystemMetricSampled) for p in received)
    assert all(p.memory_total_mb > 0 or p.memory_percent >= 0 for p in received)


def test_system_monitor_stop_is_idempotent(qt_app: QApplication) -> None:
    from app.core.unified_event_bus import UnifiedEventBus
    from app.services.monitor import SystemMonitor

    bus = UnifiedEventBus()
    monitor = SystemMonitor(bus, hz=10.0)
    monitor.start()
    time.sleep(0.1)
    monitor.stop()
    # 双 stop 不应抛错
    monitor.stop()
    assert not monitor.is_running


def test_system_monitor_rejects_invalid_hz(qt_app: QApplication) -> None:
    from app.core.unified_event_bus import UnifiedEventBus
    from app.services.monitor import SystemMonitor

    bus = UnifiedEventBus()
    with pytest.raises(ValueError):
        SystemMonitor(bus, hz=0)
    with pytest.raises(ValueError):
        SystemMonitor(bus, hz=-1)


def test_system_monitor_requires_event_bus(qt_app: QApplication) -> None:
    from app.services.monitor import SystemMonitor

    with pytest.raises(ValueError):
        SystemMonitor(None)  # type: ignore[arg-type]


def test_system_monitor_sink_invoked_per_sample(qt_app: QApplication) -> None:
    from app.core.event_types import SystemMetricSampled
    from app.core.unified_event_bus import UnifiedEventBus
    from app.services.monitor import SystemMonitor

    bus = UnifiedEventBus()
    sink_calls: list[SystemMetricSampled] = []
    monitor = SystemMonitor(bus, hz=20.0, sink=lambda p: sink_calls.append(p))
    monitor.start()
    try:
        time.sleep(0.2)
    finally:
        monitor.stop()
    assert len(sink_calls) >= 2


def test_system_metric_sampled_event_name_constant() -> None:
    from app.core.event_types import SystemMetricSampled

    assert SystemMetricSampled.event_name == "system.metric"


# ────────────────────────────────────────────────────────────────
#  DashboardViewModel
# ────────────────────────────────────────────────────────────────


class _NullApp:
    """应用层 stub —— 没有任何服务."""

    def get_service(self, *_args, **_kwargs):
        return None

    def get_service_by_name(self, *_args, **_kwargs):
        return None


def test_dashboard_viewmodel_starts_with_zeros(qt_app: QApplication) -> None:
    from app.ui.viewmodels import DashboardViewModel

    vm = DashboardViewModel(application=None)
    assert vm.cpu_percent == 0.0
    assert vm.memory_percent == 0.0
    assert vm.memory_total_mb == 0.0
    assert vm.disk_percent == 0.0
    assert vm.cpu_history == ()
    assert vm.memory_history == ()


def test_dashboard_viewmodel_inject_metric_updates_state(
    qt_app: QApplication,
) -> None:
    from app.ui.viewmodels import DashboardViewModel

    vm = DashboardViewModel(application=None)
    vm.inject_metric(
        cpu_percent=42.0,
        memory_percent=58.0,
        memory_used_mb=8192.0,
        memory_total_mb=16384.0,
        disk_percent=22.0,
        process_memory_mb=120.0,
    )
    assert vm.cpu_percent == 42.0
    assert vm.memory_percent == 58.0
    assert vm.memory_used_mb == 8192.0
    assert vm.disk_percent == 22.0
    assert vm.process_memory_mb == 120.0
    assert vm.cpu_history[-1] == 42.0
    assert vm.memory_history[-1] == 58.0


def test_dashboard_viewmodel_history_capacity_is_bounded(
    qt_app: QApplication,
) -> None:
    from app.ui.viewmodels import DashboardViewModel

    vm = DashboardViewModel(application=None)
    cap = vm.HISTORY_CAPACITY
    # 灌入 2× capacity 个不同样本
    for i in range(cap * 2):
        vm.inject_metric(cpu_percent=float(i), memory_percent=float(i))
    assert len(vm.cpu_history) == cap
    assert len(vm.memory_history) == cap
    # 窗口里是最新的 cap 个
    assert vm.cpu_history[0] == cap
    assert vm.cpu_history[-1] == cap * 2 - 1


def test_dashboard_viewmodel_emits_signals_on_change(
    qt_app: QApplication,
) -> None:
    from app.ui.viewmodels import DashboardViewModel

    vm = DashboardViewModel(application=None)
    seen: list[str] = []
    vm.cpu_percent_changed.connect(lambda: seen.append("cpu"))
    vm.memory_percent_changed.connect(lambda: seen.append("mem"))
    vm.history_changed.connect(lambda: seen.append("hist"))

    vm.inject_metric(cpu_percent=10.0, memory_percent=20.0)
    vm.inject_metric(cpu_percent=10.0, memory_percent=20.0)  # 不变 → 不发
    vm.inject_metric(cpu_percent=30.0, memory_percent=40.0)  # 都变 → 发多个

    assert "cpu" in seen
    assert "mem" in seen
    # history_changed 触发条件：cpu 或 mem 至少一个改变了
    assert "hist" in seen


def test_dashboard_viewmodel_accepts_dict_payload(
    qt_app: QApplication,
) -> None:
    """``bus.publish('system.metric', dict_payload)`` 也能被消费。"""
    from app.ui.viewmodels import DashboardViewModel

    vm = DashboardViewModel(application=None)
    vm._on_system_metric({
        "cpu_percent": 88.0,
        "memory_percent": 33.0,
        "memory_used_mb": 4096.0,
        "memory_total_mb": 16384.0,
        "disk_percent": 12.0,
    })
    assert vm.cpu_percent == 88.0
    assert vm.memory_percent == 33.0
    assert vm.disk_percent == 12.0


def test_dashboard_viewmodel_unbind_is_idempotent(
    qt_app: QApplication,
) -> None:
    from app.ui.viewmodels import DashboardViewModel

    vm = DashboardViewModel(application=None)
    vm.bind()
    vm.unbind()
    vm.unbind()  # second call should be a no-op, not raise


# ────────────────────────────────────────────────────────────────
#  CommandRegistry / CommandPalette
# ────────────────────────────────────────────────────────────────


def test_command_registry_register_and_get() -> None:
    from app.ui.commands import Command, CommandRegistry

    reg = CommandRegistry()
    fired: list[str] = []
    cmd = Command(id="t.a", title="A", callback=lambda: fired.append("a"))
    reg.register(cmd)
    assert reg.get("t.a") is cmd
    cmd.callback()
    assert fired == ["a"]


def test_command_registry_search_priority() -> None:
    """search 先按 id 精确，再按 prefix → contains → keyword."""
    from app.ui.commands import Command, CommandRegistry

    reg = CommandRegistry()
    reg.register(Command(id="a", title="Apple", callback=lambda: None))
    reg.register(Command(
        id="b", title="Banana", callback=lambda: None, keywords=("fruit",)))
    reg.register(Command(
        id="c", title="Cherry", callback=lambda: None, keywords=("a",)))

    # id 精确
    assert reg.search("a")[0].id == "a"
    # prefix
    assert reg.search("Ba")[0].id == "b"
    # contains
    assert reg.search("nan")[0].id == "b"
    # keyword hit
    assert reg.search("fruit")[0].id == "b"


def test_command_registry_unregister() -> None:
    from app.ui.commands import Command, CommandRegistry

    reg = CommandRegistry()
    reg.register(Command(id="t.x", title="X", callback=lambda: None))
    assert len(reg) == 1
    reg.unregister("t.x")
    assert len(reg) == 0
    reg.unregister("t.missing")  # no-op


def test_command_palette_shortcut_default(qt_app: QApplication) -> None:
    from app.ui.commands import Command, CommandPalette, CommandRegistry

    reg = CommandRegistry()
    reg.register(Command(id="t.a", title="A", callback=lambda: None))
    palette = CommandPalette(reg, parent=None)
    assert palette._shortcut.key().toString() == "Ctrl+K"


def test_command_palette_theme_switch(qt_app: QApplication) -> None:
    from app.ui.commands import Command, CommandPalette, CommandRegistry
    from app.ui.theme.ds_tokens import set_theme_mode

    reg = CommandRegistry()
    reg.register(Command(id="t.a", title="A", callback=lambda: None))

    set_theme_mode("light")
    palette = CommandPalette(reg, parent=None)
    qt_app.processEvents()
    assert "rgba(255,255,255,0.7)" in palette.styleSheet()

    set_theme_mode("dark")
    palette.apply_palette()
    qt_app.processEvents()
    assert "rgba(17,24,39,0.6)" in palette.styleSheet()
