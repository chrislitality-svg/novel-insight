"""异步重试装饰器:指数退避(1s, 2s, 4s),默认最多 3 次。"""
import asyncio
import functools
from typing import Awaitable, Callable, TypeVar

from app.utils.logger import get_logger

logger = get_logger("retry")

T = TypeVar("T")


def async_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """失败后指数退避重试。重试耗尽后向上抛出最后一次异常。"""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exc: Exception | None = None
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt >= max_retries:
                        logger.warning("调用失败,已达最大重试 %d 次: %s", max_retries, exc)
                        break
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "第 %d 次调用失败(%s),%.0fs 后重试", attempt, exc, delay
                    )
                    await asyncio.sleep(delay)
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator
