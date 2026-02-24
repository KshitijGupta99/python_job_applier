import asyncio
from typing import Any, Awaitable, Callable, TypeVar

import httpx

from utils.logger import get_logger


T = TypeVar("T")

logger = get_logger(__name__)


async def retry_async(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    retries: int = 3,
    base_delay: float = 0.5,
    **kwargs: Any,
) -> T:
    """
    Simple retry helper with exponential backoff.

    Retries on httpx.RequestError (network issues, timeouts, etc.).
    """
    attempt = 0
    while True:
        try:
            return await func(*args, **kwargs)
        except httpx.RequestError as exc:
            attempt += 1
            if attempt > retries:
                logger.error(
                    {
                        "event": "retry_exhausted",
                        "detail": str(exc),
                        "retries": retries,
                    }
                )
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                {
                    "event": "retry_backoff",
                    "attempt": attempt,
                    "delay": delay,
                    "error": str(exc),
                }
            )
            await asyncio.sleep(delay)

