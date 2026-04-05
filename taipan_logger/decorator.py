"""
Provides the @trace decorator for automatic call logging on sync and async functions.
Logs entry parameters, return type, elapsed time, and any exceptions via the taipan logger.
Works on regular functions, methods, and dunder methods.

:author: sora7672
"""

__author__: str = "sora7672"

import asyncio
import functools
from uuid import uuid4
from datetime import datetime
from .logger import taipan


def trace(func):
    """
    Decorator that wraps a sync or async function with automatic trace logging.
    Generates a unique trace_id per call and logs entry, exit, and exceptions.
    Exceptions are always re-raised after logging.

    :param func: the function to wrap
    :return: async_wrapper if the function is a coroutine, sync_wrapper otherwise
    """

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        """
        Async variant of the trace wrapper.
        Logs before and after the awaited call, or logs and re-raises on exception.

        :param args: positional arguments passed to the wrapped function
        :param kwargs: keyword arguments passed to the wrapped function
        :return: the return value of the wrapped function
        """
        trace_id: str = uuid4().hex[:8]
        start_time: datetime = datetime.now()
        taipan.debug(
            message=f"|async||BeforeFunction| Argument infos: keys - "
                    f"{kwargs.keys() if kwargs else '()'} - Number of args: {len(args) if args else 0}",
            trace_id=trace_id, func_name=func.__name__
        )
        try:
            out = await func(*args, **kwargs)
        except Exception as e:
            taipan.error(message=f"{type(e).__name__}: {e}", trace_id=trace_id, func_name=func.__name__)
            raise
        elapsed: float = (datetime.now() - start_time).total_seconds()
        taipan.debug(message=f"|async||AfterFunction| Time needed {elapsed:.3f}s returns {type(out).__name__}",
                     trace_id=trace_id, func_name=func.__name__)
        return out

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        """
        Sync variant of the trace wrapper.
        Logs before and after the call, or logs and re-raises on exception.

        :param args: positional arguments passed to the wrapped function
        :param kwargs: keyword arguments passed to the wrapped function
        :return: the return value of the wrapped function
        """
        trace_id: str = uuid4().hex[:8]
        start_time: datetime = datetime.now()
        taipan.debug(
            message=f"|BeforeFunction| Argument infos: keys - "
                    f"{kwargs.keys() if kwargs else '()'} - Number of args: {len(args) if args else 0}",
            trace_id=trace_id, func_name=func.__name__
        )
        try:
            out = func(*args, **kwargs)
        except Exception as e:
            taipan.error(message=f"{type(e).__name__}: {e}", trace_id=trace_id, func_name=func.__name__)
            raise
        elapsed: float = (datetime.now() - start_time).total_seconds()
        taipan.debug(message=f"|AfterFunction| Time needed {elapsed:.3f}s returns {type(out).__name__}",
                     trace_id=trace_id, func_name=func.__name__)
        return out

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


if __name__ == "__main__":
    print("Dont start the package files alone! The imports wont work like this!")