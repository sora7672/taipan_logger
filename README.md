# taipan-logger

> A lightweight, DSGVO-safe, threadsafe, async-ready Python logger.  
> No external dependencies. Drop it in, configure once, log forever.

---

## Features

- **Singleton-based** - one instance across your entire service
- **DSGVO-safe** - no user data, no content, only structural metadata
- **Threadsafe** - uses `threading.Lock` where it matters
- **Async-ready** - `@trace` works on both sync and async functions
- **Zero dependencies** - pure Python standard library
- **Debug mode at runtime** - toggle via environment variable, no restart needed
- **Automatic project root detection** - no path configuration needed in most cases
- **Log rotation** - automatic daily rotation with configurable backup count
- **Custom log format** - configure field order, datetime format, and prefix

---

## Why this exists

Building a microservice architecture means building multiple services.
Each service runs in its own container, each container needs its own logger.

The alternative - copy-pasting and rewriting a logger six times - was never an option.

So instead of doing that, one day was spent building it properly once.
The result is taipan-logger: a logger that you drop in, import, and forget about.
No per-project configuration hell, no over-engineered setup, no copy-paste maintenance.

A centralized logging service might seem like a cleaner solution at first glance.
It is not. A shared logger across containers is a single point of failure.
If it goes down, every service goes blind at exactly the moment you need visibility the most.
Finding bugs without logs in a microservice environment is not debugging - it is guesswork.

Each service logs for itself. Isolated, reliable, always available.

And because every service handles real user requests, DSGVO-compliance was non-negotiable from day one.
No user data, no content, no addresses. Only structural metadata - timing, threads, function traces, errors.

If you need more, `taipan.debug()`, `taipan.info()`, `taipan.warning()` and `taipan.error()` are there.
The format is yours to configure. The heavy lifting is already done.

One import. If you want one configure call. Done.

---

## Installation

```bash
pip install git+https://github.com/sora7672/taipan_logger.git
```

---

## Quickstart

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
```

See [example_files/example.py](example_files/example.py) for a full working example covering sync, async, threads, errors and stacked decorators.

---

## configure()

You don't need to configure anything!
But you can call this once before the first log entry. Raises an exception if called after logging has started.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `field_order` | `list[str]` | `['DATETIME', 'LOG_STATUS', 'TRACEID', 'THREAD', 'FUNC_NAME', 'MESSAGE']` | Order of log fields |
| `datetime_format` | `str` | `'YYYY-MM-DD - hh:mm:ss:mimimi'` | Custom datetime format |
| `log_path` | `Path\|str` | auto-detected | Override log directory |
| `log_path_relative` | `bool` | `True` | Resolve log_path relative to caller |
| `log_name` | `str` | `'taipan.log'` | Base log file name |
| `max_old_logs` | `int` | `10` | Max number of old log files to keep |
| `special_prefix` | `str` | `None` | Prefix added to every log line |
| `debug` | `bool` | `False` | Enable debug mode |
| `keep_log_open` | `bool` | `False` | Keep log open until restart instead of daily rotation |
| `env_check_interval` | `int` | `120` | Seconds between environment variable checks |

### Datetime format placeholders

```
yyyy / YYYY  -> 2026              yy / YY  -> 26
MM           -> 04 (with zero)    M  -> 4
dd / DD      -> 05 (with zero)    d  -> 5
hh / HH      -> 13 (with zero)    h  -> 13
mm           -> 45 (with zero)    m  -> 45
ss           -> 07 (with zero)    s  -> 7
mimimi       -> 234 (ms 3 digits)
mimi         -> 23  (ms 2 digits)
mi           -> 2   (ms 1 digit)
```

---

## @trace Decorator

Wraps any function or method - sync or async - and automatically logs entry, exit, duration and errors.

```python
from taipan_logger import trace

@trace
def my_function(x: int, y: int) -> int:
    return x + y

@trace
async def my_async_function(url: str) -> dict:
    ...
```

Works with other decorators too - always place `@trace` closest to the function:

```python
@repeat(times=3)
@trace
def say_hello(name: str) -> str:
    return f"Hello {name}"
```

---

## Runtime Debug Toggle

Set the environment variable `DEBUG_ENABLED` to switch debug mode at runtime without restarting:

```bash
DEBUG_ENABLED=true
DEBUG_ENABLED=false
```

Taipan checks this every `env_check_interval` seconds (default 120s).

---

## Log Output Example

```
TEST[2026-04-05 - 12:36:13:427][DEBUG][654b403a][MainThread][add]|BeforeFunction| Argument infos: keys - () - Number of args: 2
TEST[2026-04-05 - 12:36:13:427][DEBUG][654b403a][MainThread][add]|AfterFunction| Time needed 0.001s returns int
TEST[2026-04-05 - 12:36:13:431][INFO][NO TRACEID][MainThread][greet]Greeting someone
TEST[2026-04-05 - 12:36:13:439][ERROR][70f74f1d][MainThread][will_fail]ValueError: I was always going to fail
TEST[2026-04-05 - 12:36:13:623][DEBUG][700732fd][Thread-1 (thread_worker)][thread_worker]|BeforeFunction| Argument infos: keys - () - Number of args: 1
TEST[2026-04-05 - 12:36:13:627][ERROR][87cd1ab0][Thread-3 (thread_worker)][thread_worker]ValueError: Worker 2 cannot handle this load
```
See the whole log example [HERE](example_files/2026-04-05_12-36-13_taipan.log)


---

## Project Root Detection

On first import, Taipan searches upward from the entry point for known project anchors:

```
.venv, requirements.txt, .gitignore, README.md,
pyproject.toml, setup.py, setup.cfg, .git
```

The directory with the most matches is used as project root. Logs are written to `<project_root>/logs/`.

Override with `configure(log_path=...)` if needed.

---

## Exceptions

| Exception | When |
|---|---|
| `TaipanRootNotFoundError` | Project root could not be detected |
| `TaipanLogPathError` | Log directory could not be created or accessed |
| `TaipanAlreadyConfiguredException` | `configure()` called more than once |
| `TaipanToLateConfiguredException` | `configure()` called after first log entry |
| `TaipanWrongConfiguredError` | Invalid configuration |

---

## Support

This software is provided without official support.  
Contact and questions via GitHub Issues are welcome at any time.

For official **business support**, contact the author via GitHub before offering support services.  
Approved providers will be listed here. The author reserves the right to revoke any listing.

> **Author:** [sora7672](https://github.com/sora7672)  
> **Organization:** [soss-community](https://github.com/soss-community)   
> **Website:** [soss.page](https://soss.page) 

---

## License

This project is licensed under the **Sora Open Source Software License (SOSS) v1.0**.  
See [LICENSE](./LICENSE) for details.  
Always refer to the latest version at: [github.com/soss-community](https://github.com/soss-community)

---

## Naming Convention

The Taipan is one of the most venomous snakes in the world,
known for striking with extreme precision, never missing its target.

That philosophy carries over here.
Taipan-logger is built to hit exactly what matters: structural metadata, timing, thread context and error traces.
Nothing more, nothing less. No user data, no guesswork, no bloat.

Precise by design. DSGVO-safe by default.

---

## Roadmap

- [ ] PyPI publish
- [ ] Transfer to soss-community organization
- [ ] CLI interface for external logger access

