#!/usr/bin/env python3
"""Test AI Service Status and Health"""

from scenefab.services.ai.base import ServiceHealth, ServiceStatus


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
