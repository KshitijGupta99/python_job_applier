import asyncio
import time
from typing import Optional


class RateLimiter:
    def __init__(self, delay_seconds: float = 1.0) -> None:
        self.delay_seconds = max(delay_seconds, 0.0)
        self._lock = asyncio.Lock()
        self._last_call: Optional[float] = None

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            if self._last_call is not None and self.delay_seconds > 0:
                elapsed = now - self._last_call
                remaining = self.delay_seconds - elapsed
                if remaining > 0:
                    await asyncio.sleep(remaining)
            self._last_call = time.monotonic()

