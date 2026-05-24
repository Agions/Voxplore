"""Tests for app.core._signals - PySide6 compatibility bridge"""

import pytest


class TestSignalsBridge:
    """Test the _signals bridge layer"""

    def test_qobject_available(self):
        """QObject should be available"""
        from scenefab._signals import QObject
        assert QObject is not None

    def test_signal_available(self):
        """Signal should be available"""
        from scenefab._signals import Signal
        assert Signal is not None

    def test_signal_instantiation(self):
        """Signal can be instantiated with a type"""
        from scenefab._signals import Signal
        sig = Signal(str)
        assert sig is not None
