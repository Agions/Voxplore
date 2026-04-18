#!/usr/bin/env python3
"""Test AI Service Manager"""

import pytest
from datetime import datetime
from dataclasses import asdict

from app.services.ai_service_manager import (
    ServiceStatus,
    ServiceHealth,
    AIServiceManager,
)


class TestServiceStatus:
    """Test service status enum"""

    def test_all_statuses(self):
        """Test all statuses"""
        statuses = [
            ServiceStatus.ACTIVE,
            ServiceStatus.INACTIVE,
            ServiceStatus.ERROR,
            ServiceStatus.MAINTENANCE,
        ]
        
        assert len(statuses) == 4
        assert ServiceStatus.ACTIVE.value == "active"


class TestServiceHealth:
    """Test service health"""

    def test_creation(self):
        """Test creation"""
        health = ServiceHealth(
            service_name="test_service",
            status=ServiceStatus.ACTIVE,
            last_check=1234567890.0,
        )
        
        assert health.service_name == "test_service"
        assert health.status == ServiceStatus.ACTIVE

    def test_with_error(self):
        """Test creation with error"""
        health = ServiceHealth(
            service_name="test_service",
            status=ServiceStatus.ERROR,
            last_check=1234567890.0,
            error_message="Connection failed",
        )
        
        assert health.status == ServiceStatus.ERROR
        assert health.error_message == "Connection failed"


class TestAIServiceManager:
    """Test AI service manager"""

    def test_init(self):
        """Test initialization"""
        manager = AIServiceManager()
        
        assert manager is not None

    def test_register_service(self):
        """Test register service"""
        manager = AIServiceManager()
        manager.register_service("test_service", object())
        
        assert "test_service" in manager.get_all_services()

    def test_get_service(self):
        """Test get service"""
        manager = AIServiceManager()
        service = object()
        manager.register_service("test_service", service)
        
        assert manager.get_service("test_service") is service

    def test_get_nonexistent_service(self):
        """Test get nonexistent service"""
        manager = AIServiceManager()
        
        assert manager.get_service("nonexistent") is None

    def test_get_all_services(self):
        """Test get all services"""
        manager = AIServiceManager()
        manager.register_service("s1", object())
        manager.register_service("s2", object())
        
        services = manager.get_all_services()
        
        assert len(services) == 2

    def test_get_service_health(self):
        """Test get service health"""
        manager = AIServiceManager()
        
        health = manager.get_service_health("test_service")
        
        assert health is None

    def test_get_usage_stats(self):
        """Test get usage stats"""
        manager = AIServiceManager()
        
        stats = manager.get_usage_stats("test_service")
        
        assert "requests" in stats
        assert "errors" in stats
        assert "avg_response_time" in stats

    def test_get_summary(self):
        """Test get summary"""
        manager = AIServiceManager()
        
        summary = manager.get_summary()
        
        assert "total_services" in summary
        assert "active_services" in summary
