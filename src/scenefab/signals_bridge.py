"""
PySide6 兼容桥接层

提供 QObject 和 Signal 的兼容实现：
- 有 PySide6 时：直接使用 PySide6.QtCore
- 无 PySide6 时：提供无头环境兼容的桩

用法：
    from scenefab.signals_bridge import QObject, Signal

这样 core 层就可以在 CI / 无头环境下导入而不报 ImportError。
"""

try:
    from PySide6.QtCore import QObject, QSettings, QTimer, Signal

    _HAS_PYSIDE6 = True
except ImportError:
    _HAS_PYSIDE6 = False

    class Signal:
        """无头环境的 Signal 桩"""

        def __init__(self, *args):
            pass

        def connect(self, *args, **kwargs):
            pass

        def disconnect(self, *args, **kwargs):
            pass

        def emit(self, *args, **kwargs):
            pass

    class QObject:
        """无头环境的 QObject 桩"""

        class Signal(Signal):  # 内部引用
            pass

    QTimer = None
    QSettings = None


__all__ = ["QObject", "Signal", "QTimer", "QSettings", "_HAS_PYSIDE6"]
