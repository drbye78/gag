"""Tests for core/di.py AppContainer."""

import threading
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def _reset_container():
    """Reset the AppContainer singleton between tests."""
    from core.di import AppContainer
    AppContainer._instance = None
    yield
    AppContainer._instance = None


class TestAppContainerSingleton:
    def test_register_singleton(self):
        from core.di import AppContainer
        container = AppContainer()
        container.register_singleton(int, 42)
        assert container.singleton(int) == 42

    def test_singleton_returns_none_for_unregistered(self):
        from core.di import AppContainer
        container = AppContainer()
        assert container.singleton(str) is None

    def test_singleton_overwrite(self):
        from core.di import AppContainer
        container = AppContainer()
        container.register_singleton(str, "first")
        container.register_singleton(str, "second")
        assert container.singleton(str) == "second"


class TestAppContainerFactory:
    def test_register_factory(self):
        from core.di import AppContainer
        container = AppContainer()
        container.register_factory(list, list)
        result = container.get_or_create(list)
        assert isinstance(result, list)

    def test_factory_creates_once(self):
        from core.di import AppContainer
        container = AppContainer()
        call_count = 0

        def make():
            nonlocal call_count
            call_count += 1
            return {"value": call_count}

        container.register_factory(dict, make)
        first = container.get_or_create(dict)
        second = container.get_or_create(dict)
        assert first is second
        assert call_count == 1


class TestGetOrCreate:
    def test_raises_keyerror_for_unregistered(self):
        from core.di import AppContainer
        container = AppContainer()
        with pytest.raises(KeyError, match="No singleton or factory"):
            container.get_or_create(float)

    def test_prefers_existing_singleton_over_factory(self):
        from core.di import AppContainer
        container = AppContainer()
        container.register_singleton(str, "cached")
        container.register_factory(str, lambda: "from_factory")
        assert container.get_or_create(str) == "cached"

    def test_thread_safety_basic(self):
        """Basic test that concurrent get_or_create doesn't raise."""
        from core.di import AppContainer
        container = AppContainer()
        container.register_factory(list, list)

        results = []
        errors = []

        def worker():
            try:
                r = container.get_or_create(list)
                results.append(r)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        # All threads should get the same instance
        assert all(r is results[0] for r in results)


class TestClearOverrides:
    def test_clear_overrides(self):
        from core.di import AppContainer
        container = AppContainer()
        container.register_singleton(int, 1)
        container.register_factory(str, str)
        container.clear_overrides()
        assert container.singleton(int) is None
        with pytest.raises(KeyError):
            container.get_or_create(str)


class TestAppContainerSingletonPattern:
    def test_app_container_is_singleton(self):
        from core.di import AppContainer
        a = AppContainer()
        b = AppContainer()
        assert a is b
