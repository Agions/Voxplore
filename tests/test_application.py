#!/usr/bin/env python3
"""Test Application

Note: Application tests need macOS/PySide6 environment.
"""

import pytest

pytest.skip("Application tests need macOS/PySide6 environment", allow_module_level=True)


class TestApplication:
    """Test Application"""

    def test_creation(self):
        """Test creation"""
        pass
