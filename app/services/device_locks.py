"""Process-local per-device serialization for safety-critical state changes."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass


@dataclass(slots=True)
class _DeviceLockEntry:
    lock: asyncio.Lock
    references: int = 0


_device_locks: dict[str, _DeviceLockEntry] = {}
_device_locks_guard = threading.Lock()


@asynccontextmanager
async def serialize_device(device_id: str) -> AsyncIterator[None]:
    """Serialize state transition + delivery for one device in one worker."""

    with _device_locks_guard:
        entry = _device_locks.setdefault(
            device_id, _DeviceLockEntry(lock=asyncio.Lock())
        )
        entry.references += 1
    try:
        async with entry.lock:
            yield
    finally:
        with _device_locks_guard:
            entry.references -= 1
            if entry.references == 0 and _device_locks.get(device_id) is entry:
                _device_locks.pop(device_id, None)


async def device_lock_dependency(device_id: str) -> AsyncIterator[None]:
    async with serialize_device(device_id):
        yield
