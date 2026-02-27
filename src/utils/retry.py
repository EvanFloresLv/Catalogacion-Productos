# ---------------------------------------------------------------------
# Standard libraries
# ---------------------------------------------------------------------
import time
import random
from typing import Callable, TypeVar, Tuple, Type, Awaitable
import asyncio

T = TypeVar("T")


async def async_exponential_backoff_retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int = 5,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    retry_on: Tuple[Type[BaseException], ...] = (Exception,),
) -> T:

    last_exc: BaseException | None = None

    for attempt in range(1, attempts + 1):
        try:
            return await fn()

        except retry_on as exc:
            last_exc = exc

            if attempt == attempts:
                raise

            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            sleep_for = random.uniform(0, delay)

            await asyncio.sleep(sleep_for)

    raise RuntimeError("Retry failed unexpectedly") from last_exc


def sync_exponential_backoff_retry_sync(
    fn: Callable[[], T],
    *,
    attempts: int = 5,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    retry_on: Tuple[Type[BaseException], ...] = (Exception,),
) -> T:

    last_exc: BaseException | None = None

    for attempt in range(1, attempts + 1):
        try:
            return fn()

        except retry_on as exc:
            last_exc = exc

            if attempt == attempts:
                raise

            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            sleep_for = random.uniform(0, delay)

            time.sleep(sleep_for)

    # Should never reach here
    raise RuntimeError("Retry failed unexpectedly") from last_exc
