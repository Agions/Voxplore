"""Tests for app.core.service_container - enhanced lifecycle management"""


from scenefab.service_container import ServiceContainer, ServiceLifetime


class TestServiceLifetime:
    def test_lifetime_values(self):
        assert ServiceLifetime.SINGLETON == "singleton"
        assert ServiceLifetime.TRANSIENT == "transient"
        assert ServiceLifetime.FACTORY == "factory"


class TestServiceContainerLifecycle:
    def test_singleton_returns_same_instance(self):
        container = ServiceContainer()
        obj = object()

        container.register_singleton(object, obj)
        assert container.get(object) is obj
        assert container.get(object) is obj  # same instance again

    def test_transient_returns_different_instances(self):
        container = ServiceContainer()

        # register_transient takes (service_type, factory_or_type)
        # pass a class that will be instantiated each time
        class Dummy:
            pass
        container.register_transient(Dummy, Dummy)
        instance1 = container.get(Dummy)
        instance2 = container.get(Dummy)
        assert instance1 is not instance2

    def test_factory_called_each_get(self):
        container = ServiceContainer()
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return object()

        container.register_factory(object, factory)
        container.get(object)
        container.get(object)
        assert call_count == 2

    def test_get_or_create_calls_factory_once(self):
        container = ServiceContainer()
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return object()

        result1 = container.get_or_create(object, factory)
        result2 = container.get_or_create(object, factory)
        assert call_count == 1  # factory only called once
        assert result1 is result2  # same singleton instance

    def test_get_or_create_stores_and_returns_instance(self):
        container = ServiceContainer()
        obj = object()

        result = container.get_or_create(object, lambda: obj)
        assert result is obj
        assert container.has(object)  # now registered as singleton
