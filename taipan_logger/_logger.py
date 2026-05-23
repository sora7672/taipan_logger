"""
Provides the TaipanLogger class with all logging state held at class level.
Handles log folder creation, log file rotation, debug mode, thread-safe writing,
and periodic environment variable checks at runtime.
No instantiation required - all methods are classmethods.

:author: sora7672
"""

__author__: str = "sora7672"

from ._exceptions import (TaipanLogPathError, TaipanRootNotFoundError,
                          TaipanWrongConfiguredError, TaipanToLateConfiguredExceptionTaipan)
from ._time_formatter import get_datetime_string_by_format

import inspect
import logging

from pathlib import Path
from sys import argv
from os import getenv, getpid
from threading import Lock, current_thread
from time import monotonic


class TaipanLogger:
    """
    Class-level logger for the taipan logger package.
    All state is stored as class variables - no instance is needed or created.
    Manages log folder creation, log file rotation, debug mode toggling,
    thread-safe log writing, and periodic environment variable checks.

    Configurable via TaipanLogger.configure() before the first log entry is written,
    or at runtime via the DEBUG_ENABLED environment variable.
    """

    __lock: Lock = Lock()

    # Flags
    __is_configured: bool = False
    __logger_instance_initialized: bool = False
    __found_project_root: bool = False
    __log_folder_created: bool = False
    __log_file_created: bool = False

    # Configurable options
    _debug: bool = False
    _exception_hook_in_is_set: bool = False
    _log_name: str = "taipan"
    _pid : str = getpid()  # Needs to be set once at start, to prevent multiple processes using the same log
    _log_path: Path | None = None
    _datetime_format: str = 'YYYY-MM-DD - hh:mm:ss:mimimi'
    _field_order: list[str] = ['DATETIME', 'LOG_STATUS', 'TRACEID', 'THREAD', 'FUNC_NAME', 'MESSAGE']
    _allowed_fields: tuple = ('DATETIME', 'LOG_STATUS', 'TRACEID', 'THREAD', 'FUNC_NAME', 'MESSAGE')
    # Minimum required fields: DATETIME, LOG_STATUS, MESSAGE
    _max_old_logs: int = 10
    _delete_older_logs: bool = True
    _special_prefix: str | None = None
    _keep_log_open: bool = False
    _env_check_interval: int = 120        # seconds
    _log_rotation_interval: int = 60 * 60 * 24  # 24 hours in seconds

    # Internal attributes only
    __project_root_path: Path | None = None
    __logger_instance: logging.Logger | None = None
    __logger_file_handler_instance: logging.FileHandler | None = None
    __full_log_file_path: Path | None = None
    __next_env_check_time: float | None = None
    __next_log_rotation_time: float | None = None
    __tracked_exception_ids: list = []

    @classmethod
    def _class_init(cls) -> None:
        """
        Runs once at module load time to set up initial state.
        Reads the debug environment variable, sets timed check baselines, and locates the project root.

        :return: None
        """
        debug: bool | None = cls.__get_system_debug_var()
        cls._debug = debug if debug is not None else False
        cls.__next_env_check_time = monotonic() + cls._env_check_interval
        cls.__get_project_root()

    @classmethod
    def configure(cls, field_order: list[str] | None = None, datetime_format: str | None = None,
                  log_path: Path | str | None = None, log_path_relative: bool = True, log_name: str | None = None,
                  max_old_logs: int | None = None, delete_older_logs: bool | None = None,
                  special_prefix: str | None = None, exception_hook_in_is_set: bool = None,
                  debug: bool | None = None, keep_log_open: bool | None = None,
                  env_check_interval: int | None = None) -> None:
        """
        Configures TaipanLogger before the first log entry is written.
        Resolves the caller's directory automatically for relative log path support.

        :param field_order: list[str] | None (ordered list of fields to include in each log line)
        :param datetime_format: str | None (custom datetime format string using taipan placeholders)
        :param log_path: Path | str | None (custom path for the log folder)
        :param log_path_relative: bool (if True, log_path is relative to the caller's directory)
        :param log_name: str | None (base name for log files)
        :param max_old_logs: int | None (maximum number of log files to keep before rotating)
        :param delete_older_logs: bool | None (if True, old logs are deleted instead of archived)
        :param special_prefix: str | None (optional prefix string added to every log line)
        :param debug: bool | None (enables or disables debug level logging)
        :param keep_log_open: bool | None (if True, the log file is never rotated automatically)
        :param exception_hook_in_is_set: bool | None (if True, trace won't write exceptions)
        :param env_check_interval: int | None (interval in seconds between environment variable checks)
        :return: None
        :raises TaipanToLateConfiguredExceptionTaipan: If the logger is already active.
        :raises TypeError: For any argument of the wrong type.
        :raises ValueError: If field_order contains invalid or missing required fields.
        :raises TaipanLogPathError: If the given log_path does not exist.
        """
        if cls.__logger_instance_initialized:
            raise TaipanToLateConfiguredExceptionTaipan()
        if cls.__is_configured:
            print("Taipan already configured, dropped new configuration.")
            return

        if field_order and not isinstance(field_order, list):
            raise TypeError("field_order is not a list")
        if datetime_format and not isinstance(datetime_format, str):
            raise TypeError("datetime_format is not a string")
        if log_path and not isinstance(log_path, (str, Path)):
            raise TypeError("log_path is not a string or Path")
        if log_path_relative and not isinstance(log_path_relative, bool):
            raise TypeError("log_path_relative is not a bool")
        if log_name and not isinstance(log_name, str):
            raise TypeError("log_name is not a string")
        if max_old_logs and not isinstance(max_old_logs, int):
            raise TypeError("max_old_logs is not an int")
        if delete_older_logs and not isinstance(delete_older_logs, bool):
            raise TypeError("delete_older_logs is not a bool")
        if special_prefix and not isinstance(special_prefix, str):
            raise TypeError("special_prefix is not a string")
        if debug and not isinstance(debug, bool):
            raise TypeError("debug is not a bool")
        if keep_log_open and not isinstance(keep_log_open, bool):
            raise TypeError("keep_log_open is not a bool")
        if env_check_interval and not isinstance(env_check_interval, int):
            raise TypeError("env_check_interval is not an int")
        if exception_hook_in_is_set and not isinstance(exception_hook_in_is_set, bool):
            raise TypeError("exception_hook_in_is_set is not a bool")

        if field_order and not all(field in cls._allowed_fields for field in field_order):
            raise ValueError("The fields provided include not allowed fields: {}".format(field_order))
        # Minimum DATETIME, LOG_STATUS, MESSAGE
        if field_order and not all(f in field_order for f in ("DATETIME", "LOG_STATUS", "MESSAGE")):
            raise ValueError(
                "The fields are missing at least one of these fields: {}".format(["DATETIME", "LOG_STATUS", "MESSAGE"])
            )

        if field_order:
            cls._field_order = field_order
        if datetime_format:
            cls._datetime_format = datetime_format
        if log_name:
            n_logname = log_name.split(".")[0]
            if n_logname != log_name:
                print("Log name included a '.', we split it to: {}".format(n_logname))
            cls._log_name = n_logname
        if max_old_logs:
            cls._max_old_logs = max_old_logs
        if delete_older_logs:
            cls._delete_older_logs = delete_older_logs
        if special_prefix:
            cls._special_prefix = special_prefix
        if debug:
            cls._debug = debug
        if keep_log_open:
            cls._keep_log_open = keep_log_open
        if env_check_interval:
            cls._env_check_interval = env_check_interval
        if exception_hook_in_is_set:
            cls._exception_hook_in_is_set = exception_hook_in_is_set

        if log_path:
            # caller frame is 1 level up since configure lives directly on the class
            caller_path: Path = Path(inspect.stack()[1].filename).parent
            n_path: Path = Path(caller_path, log_path) if log_path_relative else Path(log_path)
            if not n_path.exists():
                raise TaipanLogPathError(f"The log_path does not exist.{n_path}")
            cls._log_path = n_path

        cls.__is_configured = True

    @classmethod
    def has_exception_hook_in(cls) -> bool:
        return cls._exception_hook_in_is_set

    @classmethod
    def debug(cls, message: str, trace_id: str = None, func_name: str = None) -> None:
        """
        Writes a DEBUG level log entry.

        :param message: str (the log message text)
        :param trace_id: str | None (optional trace ID for the current call)
        :param func_name: str | None (optional function name override)
        :return: None
        """
        cls.__log(message=message, log_status="DEBUG", trace_id=trace_id, func_name=func_name)

    @classmethod
    def info(cls, message: str, trace_id: str = None, func_name: str = None) -> None:
        """
        Writes an INFO level log entry.

        :param message: str (the log message text)
        :param trace_id: str | None (optional trace ID for the current call)
        :param func_name: str | None (optional function name override)
        :return: None
        """
        cls.__log(message=message, log_status="INFO", trace_id=trace_id, func_name=func_name)

    @classmethod
    def warning(cls, message: str, trace_id: str = None, func_name: str = None) -> None:
        """
        Writes a WARNING level log entry.

        :param message: str (the log message text)
        :param trace_id: str | None (optional trace ID for the current call)
        :param func_name: str | None (optional function name override)
        :return: None
        """
        cls.__log(message=message, log_status="WARNING", trace_id=trace_id, func_name=func_name)

    @classmethod
    def error(cls, message: str, trace_id: str = None, func_name: str = None) -> None:
        """
        Writes an ERROR level log entry.

        :param message: str (the log message text)
        :param trace_id: str | None (optional trace ID for the current call)
        :param func_name: str | None (optional function name override)
        :return: None
        """
        cls.__log(message=message, log_status="ERROR", trace_id=trace_id, func_name=func_name)

    @classmethod
    def _exception_id_exists(cls, exception_id: int) -> bool:
        """
        Checks whether an exception id is already being tracked.
        If not tracked, adds it to the list. If the list is at capacity (5), drops the oldest entry first.
        Always returns True - the return value signals that the id has been registered.

        :param exception_id: int (the id() of the exception instance to track)
        :return: bool (always True after registration)
        """
        if exception_id not in cls.__tracked_exception_ids:
            if len(cls.__tracked_exception_ids) >= 5:
                cls.__tracked_exception_ids.pop(0)
            cls.__tracked_exception_ids.append(exception_id)
            return False
        return True

    @classmethod
    def __get_project_root(cls) -> None:
        """
        Attempts to locate the project root by walking up from the caller and execution paths,
        counting how many known marker files exist at each directory level.
        Sets __project_root_path to the directory with the most matches, up to 5 levels deep.
        Sets __found_project_root to False if no marker files are found at all.

        :return: None
        """
        python_execution_path: Path = Path(argv[0]).resolve()
        frame = inspect.stack()[-1]
        caller_path: Path = Path(frame.filename)

        checkable_files_list: list[str] = [
            ".venv", "requirements.txt", "requirements-dev.txt", ".gitignore", "README.md",
            "pyproject.toml", "setup.py", "setup.cfg", ".git"
        ]
        found_file_paths: dict[Path, int] = {}

        for py_path in [caller_path, python_execution_path]:
            if isinstance(py_path, Path):
                current_check: Path = py_path
                for _ in range(5):
                    if current_check == current_check.parent:
                        break
                    current_check = current_check.parent
                    for file in current_check.iterdir():
                        if file.name in checkable_files_list:
                            found_file_paths.setdefault(file.parent, 0)
                            found_file_paths[file.parent] += 1

        if not found_file_paths:
            cls.__found_project_root = False
            return

        cls.__found_project_root = True
        cls.__project_root_path = Path(max(found_file_paths, key=found_file_paths.get))

    @classmethod
    def __create_log_folder(cls) -> None:
        """
        Creates the log folder on disk. Uses the project root if no custom path is set.
        Sets _log_path and marks __log_folder_created on success.

        :return: None
        :raises TaipanRootNotFoundError: If neither a log path nor a project root is available.
        :raises TaipanLogPathError: If the folder cannot be created due to a permission or IO error.
        """
        if cls.__log_folder_created:
            return

        if not cls._log_path and not cls.__found_project_root:
            raise TaipanRootNotFoundError()
        elif not cls._log_path and cls.__found_project_root:
            cls._log_path = Path(cls.__project_root_path, "logs")

        try:
            cls._log_path.mkdir(parents=True, exist_ok=True)
        except (PermissionError, FileNotFoundError, BlockingIOError):
            raise TaipanLogPathError("Could not create logs folder due to permission error or some other error.")

        cls.__log_folder_created = True

    @classmethod
    def __handle_old_logs(cls) -> None:
        """
        Enforces the max_old_logs limit by removing or archiving the oldest log files.
        Moves old logs to an 'old_logs' subfolder if delete_older_logs is False, otherwise deletes them.

        :return: None
        :raises TaipanLogPathError: If the log folder has not been created yet.
        """
        if not cls.__log_folder_created:
            raise TaipanLogPathError("The log folder was not created before trying to handle old logs.")

        log_list: list[str] = sorted(
            item.name for item in cls._log_path.iterdir() if item.suffix == ".log"
        )

        if len(log_list) < cls._max_old_logs:
            return

        if not cls._delete_older_logs:
            Path(cls._log_path, "old_logs").mkdir(parents=True, exist_ok=True)

        while len(log_list) >= cls._max_old_logs:
            removable: str = log_list.pop(0)
            if cls._delete_older_logs:
                Path(cls._log_path, removable).unlink()
            else:
                Path(cls._log_path, removable).rename(Path(cls._log_path, "old_logs", removable))

    @classmethod
    def __create_new_log_file(cls) -> None:
        """
        Creates a new timestamped log file in the log folder.
        Calls __handle_old_logs first to enforce the backup limit.
        Resets __next_log_rotation_time to the current monotonic time plus the rotation interval.

        :return: None
        :raises TaipanLogPathError: If the log folder has not been created yet.
        """
        if not cls.__log_folder_created:
            raise TaipanLogPathError("The log folder was not created before trying to create the file.")

        cls.__handle_old_logs()
        prefix: str = get_datetime_string_by_format("YYYY-MM-DD_hh-mm-ss_")
        cls.__full_log_file_path = Path(cls._log_path, f"{prefix}{cls._pid}_{cls._log_name}.log")
        cls.__full_log_file_path.touch()
        # Set rotation deadline as a monotonic float so __timed_checks can compare cleanly
        cls.__next_log_rotation_time = monotonic() + cls._log_rotation_interval

    @classmethod
    def __initialize_log_file(cls) -> None:
        """
        Creates the initial log file if it has not been created yet.
        Guards against repeated calls via __log_file_created.

        :return: None
        """
        if cls.__log_file_created:
            return
        cls.__create_new_log_file()
        cls.__log_file_created = True

    @classmethod
    def __switch_log(cls) -> None:
        """
        Creates a new log file and reinitializes the logger to write to it.
        Bypasses the __log_file_created guard intentionally - a new file is always needed here.
        Called automatically when __next_log_rotation_time is exceeded and keep_log_open is False.

        :return: None
        """
        cls.__create_new_log_file()
        cls.__setup_logger()

    @classmethod
    def __initialize_logger(cls) -> None:
        """
        Sets up the logger instance on first call.
        Guards against repeated calls via __logger_instance_initialized.

        :return: None
        """
        if cls.__logger_instance_initialized:
            return
        cls.__setup_logger()
        cls.__logger_instance_initialized = True

    @classmethod
    def __setup_logger(cls) -> None:
        """
        Creates or replaces the internal logging.Logger instance and its file handler.
        Closes and removes all existing handlers before attaching the new one.
        Thread-safe via the class-level lock.

        :return: None
        """
        with cls.__lock:
            if cls.__logger_instance is not None:
                for handler in cls.__logger_instance.handlers[:]:
                    handler.close()
                    cls.__logger_instance.removeHandler(handler)
                cls.__logger_instance = None

            cls.__logger_instance = logging.getLogger("TaipanLogger")
            cls.__logger_instance.setLevel(logging.DEBUG if cls._debug else logging.INFO)

            cls.__logger_file_handler_instance = logging.FileHandler(
                cls.__full_log_file_path, mode="a", encoding="utf-8"
            )
            cls.__logger_file_handler_instance.setFormatter(logging.Formatter('%(message)s'))
            cls.__logger_file_handler_instance.setLevel(logging.DEBUG if cls._debug else logging.INFO)

            cls.__logger_instance.addHandler(cls.__logger_file_handler_instance)

    @classmethod
    def __timed_checks(cls) -> None:
        """
        Runs periodic maintenance on each log call using monotonic() for all time comparisons.
        Checks environment variables at the configured interval.
        Rotates the log file when __next_log_rotation_time is exceeded, if keep_log_open is False.

        :return: None
        """
        if cls.__next_env_check_time is None:
            return

        current_time: float = monotonic()

        if cls.__next_env_check_time <= current_time:
            cls.__next_env_check_time = current_time + cls._env_check_interval
            cls.__check_for_system_vars()

        # __next_log_rotation_time is set by __create_new_log_file, so it is always a float here
        if not cls._keep_log_open and cls.__next_log_rotation_time is not None:
            if cls.__next_log_rotation_time <= current_time:
                cls.__switch_log()

    @classmethod
    def __get_system_debug_var(cls) -> bool | None:
        """
        Reads the DEBUG_ENABLED environment variable and returns it as a bool.
        Returns None if the variable is not set or has an unrecognized value.

        :return: bool | None
        """
        sys_var_debug: str | None = getenv("DEBUG_ENABLED", None)
        if sys_var_debug is None:
            return None
        if sys_var_debug.lower() == "true":
            return True
        if sys_var_debug.lower() == "false":
            return False
        return None

    @classmethod
    def __check_for_system_vars(cls) -> None:
        """
        Compares the current DEBUG_ENABLED environment variable against the active debug state.
        If they differ, updates _debug and reinitializes the logger with the new setting.

        :return: None
        """
        sys_var_debug: bool | None = cls.__get_system_debug_var()
        if sys_var_debug is None or cls._debug == sys_var_debug:
            return
        cls._debug = sys_var_debug
        cls.__setup_logger()

    @classmethod
    def __get_nearest_function_frame_above_logger(cls) -> str | None:
        """
        Walks the call stack to find the first frame that is not part of the logger internals.
        Returns the module filename stem for module-level calls, or the function name otherwise.

        :return: str | None
        """
        ignore_names: set[str] = {
            "debug", "info", "warning", "error", "__log",
            "__build_message_string", "__get_nearest_function_frame_above_logger"
        }
        for frame in inspect.stack():
            if frame.function not in ignore_names:
                if frame.function == "<module>":
                    return Path(frame.filename).stem + ".py"
                return frame.function
        return None

    @classmethod
    def __build_message_string(cls, message: str, log_status: str, trace_id: str = None,
                                func_name: str = None) -> str:
        """
        Assembles the final log line string from the configured fields and current context.

        :param message: str (the log message text)
        :param log_status: str (one of "DEBUG", "INFO", "WARNING", "ERROR")
        :param trace_id: str | None (optional trace ID for the current call)
        :param func_name: str | None (optional function name override, auto-detected if None)
        :return: str
        :raises TaipanWrongConfiguredError: If the field configuration is invalid.
        """
        if not all(x in cls._allowed_fields for x in cls._field_order):
            raise TaipanWrongConfiguredError()
        if not all(x in cls._field_order for x in ("DATETIME", "LOG_STATUS", "MESSAGE")):
            raise TaipanWrongConfiguredError(
                "The TaipanLogger is not configured correctly. "
                "Minimum fields needed in _field_order.:\n"
                "'DATETIME', 'LOG_STATUS', 'MESSAGE'"
            )

        if not func_name:
            func_name = cls.__get_nearest_function_frame_above_logger()

        parts_dict: dict[str, str] = {
            'DATETIME':   f"[{get_datetime_string_by_format(cls._datetime_format)}]",
            'LOG_STATUS': f"[{log_status}]",
            'TRACEID':    f"[{trace_id if trace_id else 'NO TRACEID'}]",
            'THREAD':     f"[{current_thread().name}]",
            'FUNC_NAME':  f"[{func_name}]",
            'MESSAGE':    f"{message}",
        }
        out_string: str = f"{cls._special_prefix}" if cls._special_prefix else ""
        for field in cls._field_order:
            out_string += parts_dict[field]

        return out_string

    @classmethod
    def __log(cls, message: str, log_status: str, trace_id: str = None, func_name: str = None) -> None:
        """
        Internal classmethod that handles all log writes.
        Lazily initializes the log folder, file, and logger instance on first call.
        Runs timed checks on every call for log rotation and env variable polling.

        :param message: str (the log message text)
        :param log_status: str ("DEBUG" | "INFO" | "WARNING" | "ERROR")
        :param trace_id: str | None (optional trace ID for the current call)
        :param func_name: str | None (optional function name override)
        :return: None
        :raises TypeError: If log_status or message are of the wrong type.
        """
        if not isinstance(log_status, str) or log_status not in ("DEBUG", "INFO", "WARNING", "ERROR"):
            raise TypeError("status_id must be 'DEBUG', 'INFO', 'WARNING' or 'ERROR'.")
        if not isinstance(message, str):
            raise TypeError("message must be a string")

        if not cls.__log_folder_created:
            cls.__create_log_folder()
        if not cls.__log_file_created:
            cls.__initialize_log_file()
        if not cls.__logger_instance_initialized:
            cls.__initialize_logger()

        cls.__timed_checks()

        log_string: str = cls.__build_message_string(
            message=message, log_status=log_status, trace_id=trace_id, func_name=func_name
        )
        getattr(cls.__logger_instance, log_status.lower())(log_string)


TaipanLogger._class_init()


if __name__ == "__main__":
    print("Dont start the package files alone! The imports wont work like this!")