import asyncio
import threading
from taipan_logger import taipan, configure, trace
import functools

configure(special_prefix="TEST", debug=True)


# --- Sync functions ---

@trace
def add(x: int, y: int) -> int:
    return x + y

@trace
def greet(name: str) -> str:
    taipan.info(f"Greeting someone")
    return f"Hello {name}"

@trace
def no_args_no_return():
    taipan.debug("doing something quietly")

@trace
def will_fail():
    raise ValueError("I was always going to fail")


# --- Async functions ---

@trace
async def async_fetch(url: str) -> dict:
    await asyncio.sleep(0.1)
    return {"url": url, "status": 200}

@trace
async def async_no_return():
    await asyncio.sleep(0.05)
    taipan.warning("async warning from inside")

@trace
async def async_fail():
    await asyncio.sleep(0.01)
    raise RuntimeError("async explosion")


# --- Thread functions ---

@trace
def thread_worker(worker_id: int):
    taipan.info(f"Worker {worker_id} started")

    if worker_id == 2:
        raise ValueError(f"Worker {worker_id} cannot handle this load")

    result = add(worker_id, worker_id * 2)
    taipan.debug(f"Worker {worker_id} finished")
    return result

@trace
def run_threads():
    threads = []
    errors = []

    def safe_worker(worker_id):
        try:
            thread_worker(worker_id)
        except ValueError as e:
            errors.append(e)

    for i in range(5):
        t = threading.Thread(target=safe_worker, args=(i,), name=f"Worker-{i}")
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if errors:
        taipan.error(f"Thread errors caught: {len(errors)}")

# --- Double Decorator ---
def repeat(times: int):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator


@repeat(times=3)
@trace
def say_hello(name: str) -> str:
    return f"Hello {name}"


@repeat(times=2)
@trace
def multiply(x: int, y: int) -> int:
    return x * y


# --- Main ---

async def main():
    # Sync calls
    add(3, 7)
    greet("Sora")
    no_args_no_return()

    try:
        will_fail()
    except ValueError:
        pass

    # Async calls
    await async_fetch("https://example.com")
    await async_no_return()

    try:
        await async_fail()
    except RuntimeError:
        pass

    # Threads
    threads = [threading.Thread(target=thread_worker, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Double Decorated Functions
    multiply(3, 7)
    say_hello("Sam")

    taipan.error("manual error log")
    taipan.warning("manual warning log")
    taipan.debug("manual debug log")
    taipan.info("manual info log")


if __name__ == "__main__":
    asyncio.run(main())