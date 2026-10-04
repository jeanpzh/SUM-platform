from __future__ import annotations

import asyncio
import multiprocessing

from sum_contracts.models import ServiceError

from .extractors import process_source


class CpuPool:
    """One bounded reusable spawn pool per service process, shared across documents."""

    def __init__(self, processes: int, timeout: int):
        self.processes, self.timeout = processes, timeout
        self.pool = None
        self.slots = asyncio.Semaphore(processes)
        self.reset_lock = asyncio.Lock()
        self.pending: set[asyncio.Future] = set()

    async def start(self):
        async with self.reset_lock:
            if self.pool is None:
                self.pool = await asyncio.to_thread(
                    multiprocessing.get_context("spawn").Pool, self.processes
                )

    async def reset(self):
        async with self.reset_lock:
            pool, self.pool = self.pool, None
            if pool is not None:
                await asyncio.to_thread(pool.terminate)
                await asyncio.to_thread(pool.join)
            for future in tuple(self.pending):
                if not future.done():
                    future.set_exception(
                        ServiceError("LIMITE_TIEMPO", "Se reinició el pool de extracción.", 504)
                    )

    async def call(
        self,
        action: str,
        mime: str,
        path: str,
        first: int = 0,
        last: int = 0,
        options: dict | None = None,
    ):
        async with self.slots:
            await self.start()
            loop = asyncio.get_running_loop()
            future = loop.create_future()
            self.pending.add(future)

            def deliver(result, error=False):
                if not future.done():
                    if error:
                        future.set_exception(result)
                    else:
                        future.set_result(result)

            try:
                self.pool.apply_async(
                    process_source,
                    (action, mime, path, first, last, options or {}),
                    callback=lambda value: loop.call_soon_threadsafe(deliver, value),
                    error_callback=lambda error: loop.call_soon_threadsafe(deliver, error, True),
                )
                return await asyncio.wait_for(future, self.timeout)
            except (TimeoutError, asyncio.CancelledError):
                await self.reset()
                if future.cancelled():
                    raise ServiceError(
                        "LIMITE_TIEMPO", "La extracción superó el tiempo permitido.", 504
                    ) from None
                raise
            finally:
                self.pending.discard(future)

    async def close(self):
        await self.reset()
