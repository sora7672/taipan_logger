# taipan-logger

> A lightweight, GDPR-safe, threadsafe, async-ready Python logger.
> No external dependencies. Drop it in, configure once, log forever.

[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](#)
[![License](https://img.shields.io/badge/license-SOSS%20v1.0-green)](https://github.com/soss-community/.github/blob/main/license/SOSS-MODULE-LICENSE.md)
[![Version](https://img.shields.io/badge/version-2.0.0-orange)](#)
[![Community](https://img.shields.io/badge/community-soss.page-purple)](https://soss.page)
[img width=75px height=20 src="https://komarev.com/ghpvc/?username=soss-community-taipan&color=763eab&style=flat-round&label=Views:" /](#)


---

The Taipan is one of the most venomous snakes in the world, known for striking with extreme precision - never missing its target.

That philosophy carries over here. Taipan-logger hits exactly what matters: structural metadata, timing, thread context and error traces.
Nothing more, nothing less. No user data, no guesswork, no bloat. Precise by design. GDPR-safe by default.

---

## The Problem

Building a microservice architecture means building multiple services.
Each service runs in its own container, each container needs its own logger.

The alternative - copy-pasting and rewriting a logger six times - was never an option.
So instead, one day was spent building it properly once.
The result is taipan-logger: a logger you drop in, import, and forget about.
No per-project configuration hell, no over-engineered setup, no copy-paste maintenance.

A centralized logging service might seem like a cleaner solution at first glance - it is not.
A shared logger across containers is a single point of failure.
If it goes down, every service goes blind at exactly the moment you need visibility the most.
Finding bugs without logs in a microservice environment is not debugging, it is guesswork.

Each service logs for itself. Isolated, reliable, always available.

And because every service handles real user requests, GDPR-compliance was non-negotiable from day one.
No user data, no content, no addresses. Only structural metadata - timing, threads, function traces, errors.

One import. One optional configure call. Done.

---

## Features

- **Class-based singleton** - all state lives at class level, no instance needed, one logger across your entire service
- **GDPR-safe** - no user data, no content, only structural metadata logged by default
- **Threadsafe** - uses `threading.Lock` for all write operations
- **Async-ready** - `@trace` detects and wraps both sync and async functions automatically
- **Zero dependencies** - pure Python standard library only
- **Debug toggle at runtime** - switch debug mode via environment variable without restart
- **Automatic project root detection** - finds your project root by scanning for known anchor files, no path config needed
- **Log rotation** - daily rotation with configurable backup count and optional keep-open mode
- **Custom log format** - configure field order, datetime format, and a per-service prefix
- **Smart exception deduplication** - the `@trace` decorator logs each exception object only once, even when it is re-raised and caught multiple times across nested call frames

---

## Installation

```bash
pip install taipan-logger
```

[taipan-logger on PyPI](https://pypi.org/project/taipan-logger/)

---

## Usage

### Quickstart

```python
from taipan_logger import taipan, configure, trace

# Optional: configure before first log call
configure(special_prefix="MY-SERVICE", debug=True)

# Manual logging
taipan.info("Service started")
taipan.warning("Something looks off")
taipan.error("Something broke")
taipan.debug("Verbose trace info")

# Automatic function tracing
@trace
def add(x: int, y: int) -> int:
    return x + y

@trace
async def fetch_data(url: str) -> dict:
    ...
```

For full working examples see:
- [examples/example_logging.py](examples/example_logging.py) - all four log levels, manual trace_id, with and without configure
- [examples/example_decorator.py](examples/example_decorator.py) - sync and async `@trace`, stacked decorators
- [examples/example_exceptions.py](examples/example_exceptions.py) - exception deduplication, nested frames, hook_in mode
- [examples/example_configure_and_threads.py](examples/example_configure_and_threads.py) - configure() options, threading, runtime debug toggle

---

## Naming Conventions

This are the public interfaces you can use:

| Name | Type | Description |
|---|---|---|
| `taipan` | `SimpleNamespace` | Logging interface: `.debug()`, `.info()`, `.warning()`, `.error()`, `.configure()` |
| `configure` | function | Direct alias for `TaipanLogger.configure` |
| `trace` | decorator | Wraps sync and async functions with automatic trace logging |

---

## configure()

Call this once before the first log entry. If the logger has already written anything, it raises an exception.
Nothing needs to be configured - all defaults work out of the box.

```python
from taipan_logger import configure

configure(special_prefix="MY-SERVICE", debug=True)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `field_order` | `list[str]` | `['DATETIME', 'LOG_STATUS', 'TRACEID', 'THREAD', 'FUNC_NAME', 'MESSAGE']` | Order of fields in each log line |
| `datetime_format` | `str` | `'YYYY-MM-DD - hh:mm:ss:mimimi'` | Custom datetime format using taipan placeholders |
| `log_path` | `Path\|str` | auto-detected | Override log directory |
| `log_path_relative` | `bool` | `True` | Resolve log_path relative to the caller's file |
| `log_name` | `str` | `'taipan.log'` | Base log file name (date prefix is added automatically) |
| `max_old_logs` | `int` | `10` | Max number of rotated log files to keep |
| `delete_older_logs` | `bool` | `True` | Delete old logs beyond max_old_logs |
| `special_prefix` | `str` | `None` | String prepended to every log line, useful to identify the service |
| `debug` | `bool` | `False` | Enable debug level logging |
| `keep_log_open` | `bool` | `False` | Disable daily rotation - keep one log file until restart |
| `env_check_interval` | `int` | `120` | Seconds between environment variable polls |
| `exception_hook_in_is_set` | `bool` | `False` | If True, `@trace` skips logging exception details and only logs that a hook is active - the hook itself is responsible for the output |

Minimum required fields if you override `field_order`: `DATETIME`, `LOG_STATUS`, `MESSAGE`.

### Datetime format placeholders

```
yyyy / YYYY  -> 2026              yy / YY  -> 26
MM           -> 04 (with zero)    M  -> 4
dd / DD      -> 05 (with zero)    d  -> 5
hh / HH      -> 13 (with zero)    h  -> 13
mm           -> 45 (with zero)    m  -> 45
ss           -> 07 (with zero)    s  -> 7
mimimi       -> 234 (ms, 3 digits)
mimi         -> 23  (ms, 2 digits)
mi           -> 2   (ms, 1 digit)
```

You could use it like this (You decide how you want to read it):  

```python
configure(datetime_format="dd~MM~yy §hh:mm'ss§ [mimimi]")
```

Output:
```
[08~05~26 §19:51'51§ [381]]
```

---

## @trace Decorator

Wraps any function or method - sync or async - and automatically logs entry, exit, duration, and exceptions.
Each call gets its own unique `trace_id`, which groups the before/after/error lines together in the log.

```python
from taipan_logger import trace

@trace
def my_function(x: int, y: int) -> int:
    return x + y

@trace
async def my_async_function(url: str) -> dict:
    ...
```

Works with other decorators. Always place `@trace` closest to the function definition:

```python
@repeat(times=3)
@trace
def say_hello(name: str) -> str:
    return f"Hello {name}"
```

**Exception deduplication:** when an exception is re-raised and passes through multiple `@trace`-wrapped frames,
it is logged only once - at the frame where it originally occurred. A new exception object (e.g. wrapping the
original via `raise RuntimeError(...) from e`) is treated as a distinct exception and logged separately.

---

## Runtime Debug Toggle

Set the environment variable `DEBUG_ENABLED` to switch debug mode at runtime without restarting:

```bash
DEBUG_ENABLED=true
DEBUG_ENABLED=false
```

Taipan polls this every `env_check_interval` seconds (default 120s).

---

## Log Output

Each line follows the configured field order. Default format:

```
[DATETIME][LOG_STATUS][TRACEID][THREAD][FUNC_NAME]MESSAGE
```

With an optional `special_prefix` prepended before the first bracket.

```
[2026-05-08 - 19:51:51:381][DEBUG][acaea09e][MainThread][path2_level1]|BeforeFunction| Argument infos: 0 xargs and 0 kwargs
[2026-05-08 - 19:51:51:382][DEBUG][f29e443d][MainThread][path2_level2]|BeforeFunction| Argument infos: 0 xargs and 0 kwargs
[2026-05-08 - 19:51:51:382][ERROR][f29e443d][MainThread][path2_level2]RuntimeError: Wrapped error in path 2
```

Notice `[f29e443d]` appears on the DEBUG before-entry and the ERROR line - the shared trace_id lets you
follow a single call through any depth of nesting or threading.

See a full log example at [example_files/2026-05-08_23-16-47_taipan.log](example_files/2026-05-08_23-16-47_taipan.log).

---

## Project Root Detection

On first import, Taipan walks upward from the entry point file and scores each parent directory by how many
known anchor files it contains:

```
.venv, requirements.txt, .gitignore, README.md, pyproject.toml, setup.py, setup.cfg, .git
```

The directory with the highest score is used as project root. Logs are written to `<project_root>/logs/`.

Override with `configure(log_path=...)` if the detection does not match your layout.

---

## Exceptions

| Exception | When it is raised |
|---|---|
| `TaipanRootNotFoundError` | Project root could not be detected during init |
| `TaipanLogPathError` | Log directory could not be created or the given path does not exist |
| `TaipanToLateConfiguredExceptionTaipan` | `configure()` called after the first log entry was written |
| `TaipanWrongConfiguredError` | Internal field configuration is invalid |

All exceptions extend `TaipanOOPException`, which adds `.message`, `.error_code`, and `.data` attributes
directly on the exception object for structured error handling.

---

## What this is not for and what we excluded

| Feature / Class | Reason excluded |
|---|---|
| Network / remote logging | Out of scope - use a dedicated log aggregator per service |
| Log parsing or querying | Taipan writes logs, it does not read them |
| Structured JSON output | Plain text format is intentional - line-based, human-readable |
| User data in log lines | GDPR requirement - never log content, only structure |
| `BaseException` subclassing | Not caught by `@trace` intentionally - `KeyboardInterrupt` etc. must not be swallowed |
| Centralized shared logger | Architectural decision - every service owns its own logger |

---

## Compatibility

Python 3.12 or higher. No external dependencies. Works on Linux, macOS, and Windows.

---

## License

This project is licensed under the **Sora Open Source Software License (SOSS) v1.0**.  
See [LICENSE](./LICENSE) for full terms.  
Always refer to the latest version at: [github.com/soss-community](https://github.com/soss-community)

---

## Community and contributing

Part of the Sora Open Source Software community.  
Visit [github.com/soss-community](https://github.com/soss-community)  
for contribution guidelines, issue tracking, and discussion.

This software is provided without official support.  
For **business support**, contact the author via GitHub before offering support services.  
Approved providers will be listed here. The author reserves the right to revoke any listing.

> **Author:** [sora7672](https://github.com/sora7672)  
> **Organization:** [soss-community](https://github.com/soss-community)  
> **Website:** [soss.page](https://soss.page)