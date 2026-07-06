"""Bridge between sync and async code paths.

Provides :func:`run_async_safely`, a helper for safely executing a coroutine
factory from synchronous code that may or may not already be running inside an
asyncio event loop.

When the caller is **not** inside an event loop we simply call
:func:`asyncio.run`. When the caller is **already** inside a running loop
(e.g. inside another ``async`` function that wants to await a sub-task) we
isolate the new event loop in a worker thread via :class:`ThreadPoolExecutor`,
so the nested ``asyncio.run`` does not conflict with the existing loop.

Typical client: a sync wrapper around an async provider call::

    def generate_sync(self, ...):
        async def _run():
            return await self.generate(...)

        result, provider = run_async_safely(_run)
        return result
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


def run_async_safely(
    coro_factory: Callable[[], Coroutine[Any, Any, T]],
) -> T:
    """Run ``coro_factory()`` from sync code, surviving nested event loops.

    Returns the value the coroutine resolves with.

    The ``coro_factory`` pattern (instead of passing an already-created
    coroutine) lets us build the coroutine exactly when we are ready to run
    it, which is required by :func:`asyncio.run` (it raises if given a
    coroutine that was created on a different loop).
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No loop in flight → safe to use asyncio.run directly.
        return asyncio.run(coro_factory())

    # Caller is inside a running loop → isolate in a worker thread so we
    # do not deadlock on the existing loop.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro_factory()).result()


__all__ = ["run_async_safely"]
