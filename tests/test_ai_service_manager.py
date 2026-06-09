#!/usr/bin/env python3
"""Test AI Service Manager (V2 权威实现)"""

from scenefab.services.ai.base import ServiceHealth, ServiceStatus
from scenefab.services.ai.manager import AIServiceManager


class TestServiceStatus:
    """Test service status enum"""

    def test_all_statuses(self):
        """Test all statuses"""
        statuses = [
            ServiceStatus.ACTIVE,
            ServiceStatus.INACTIVE,
            ServiceStatus.ERROR,
            ServiceStatus.MAINTENANCE,
            ServiceStatus.RATE_LIMITED,
        ]

        assert len(statuses) == 5
        assert ServiceStatus.ACTIVE.value == "active"
        assert ServiceStatus.MAINTENANCE.value == "maintenance"
        assert ServiceStatus.RATE_LIMITED.value == "rate_limited"


class TestServiceHealth:
    """Test service health"""

    def test_creation(self):
        """Test creation"""
        health = ServiceHealth(
            name="test_service",
            status=ServiceStatus.ACTIVE,
            last_check=1234567890.0,
        )

        assert health.name == "test_service"
        assert health.status == ServiceStatus.ACTIVE

    def test_with_error(self):
        """Test creation with error"""
        health = ServiceHealth(
            name="test_service",
            status=ServiceStatus.ERROR,
            last_check=1234567890.0,
            error_message="Connection failed",
        )

        assert health.status == ServiceStatus.ERROR
        assert health.error_message == "Connection failed"

    def test_response_time_default(self):
        """Test default response_time is 0.0"""
        health = ServiceHealth(
            name="svc",
            status=ServiceStatus.INACTIVE,
            last_check=0.0,
        )

        assert health.response_time == 0.0
        assert health.error_message == ""


class TestAIServiceManager:
    """Test AI service manager (V2 权威实现)"""

    def test_singleton(self):
        """Test AIServiceManager is a singleton"""
        m1 = AIServiceManager()
        m2 = AIServiceManager()
        assert m1 is m2

    def test_register_llm(self):
        """Test register LLM service"""
        manager = AIServiceManager()
        manager.register_llm("test_llm", {"api_key": "fake", "model": "gpt-4"})

        llm = manager.get_llm("test_llm")
        assert llm is not None

    def test_get_summary(self):
        """Test get summary"""
        manager = AIServiceManager()

        summary = manager.get_summary()

        assert "total_services" in summary or isinstance(summary, dict)

    def test_vision_accessor(self):
        """Test vision service accessor"""
        manager = AIServiceManager()
        # vision may be None if not registered; just verify accessor exists
        assert hasattr(manager, "vision")

    def test_tts_accessor(self):
        """Test TTS service accessor"""
        manager = AIServiceManager()
        assert hasattr(manager, "tts")

    def test_asr_accessor(self):
        """Test ASR service accessor"""
        manager = AIServiceManager()
        assert hasattr(manager, "asr")
