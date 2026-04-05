"""
Provides the TaipanLogger singleton and the module-level configure() function.
Handles log folder creation, log file rotation, debug mode, thread-safe writing,
and periodic environment variable checks at runtime.

:author: sora7672
"""

__author__: str = "sora7672"

from .exceptions import (TaipanLogPathError, TaipanAlreadyConfiguredException, TaipanRootNotFoundError,
                          TaipanWrongConfiguredError, TaipanToLateConfiguredException)
from .time_formatter import get_datetime_string_by_format

import inspect
import logging

from pathlib import Path
from sys import argv
from os import getenv
from threading import Lock, current_thread
from datetime import datetime, timedelta


class TaipanLogger:
    """
    Singleton logger class for the taipan logger package.
    Manages log folder creation, log file rotation, debug mode toggling,
    thread-safe log writing, and periodic environment variable checks.

    Configurable via configure() before the first log entry is written,
    or at runtime via the DEBUG_ENABLED environment variable.
    """

    _instance: "TaipanLogger | None" = None

    def __new__(cls, *args, **kwargs) -> "TaipanLogger":
        """
        Implements the singleton pattern by ensuring only one instance of the class exists.

        :return: TaipanLogger
        """
        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """
        Initializes the TaipanLogger singleton on first call.
        Skipped on subsequent calls via the _initialized guard.
        Sets all default values for configurable and internal attributes,
        and attempts to locate the project root directory.

        :return: None
        """
        if not hasattr(self, '_initialized'):
            self._initialized: bool = True
            self.__lock: Lock = Lock()

            # Flags
            self.__is_configured: bool = False
            self.__logger_instance_initialized: bool = False
            self.__found_project_root: bool = False
            self.__log_folder_created: bool = False
            self.__log_file_created: bool = False

            # Configurable options
            debug: bool | None = self.__get_system_debug_var()
            self._debug: bool = debug if debug is not None else False
            self._log_name: str = "taipan.log"
            self._log_path: Path | None = None
            self._datetime_format: str = 'YYYY-MM-DD - hh:mm:ss:mimimi'
            self._field_order: list[str] = ['DATETIME', 'LOG_STATUS', 'TRACEID', 'THREAD', 'FUNC_NAME', 'MESSAGE']
            self._allowed_fields: tuple = ('DATETIME', 'LOG_STATUS', 'TRACEID', 'THREAD', 'FUNC_NAME', 'MESSAGE')
            # Minimum required fields: DATETIME, LOG_STATUS, MESSAGE
            self._max_old_logs: int = 10
            self._delete_older_logs: bool = True
            self._special_prefix: str | None = None
            self._keep_log_open: bool = False

            # Internal attributes only
            self.__project_root_path: Path | None = None
            self.__get_project_root()
            self.__logger_instance: logging.Logger | None = None
            self._env_check_interval: int = 120  # seconds
            self.__next_env_check_time: datetime = datetime.now() + timedelta(seconds=self._env_check_interval)
            self.__real_log_file_path: Path | None = None
            self.__log_creation_datetime: datetime | None = None

    @property
    def allowed_fields(self) -> tuple:
        """
        Returns the tuple of field names that are valid for use in field_order.

        :return: tuple
        """
        return self._allowed_fields

    def __get_project_root(self) -> None:
        """
        Attempts to locate the project root by walking up from the caller and execution paths,
        counting how many known marker files exist at each directory level.
        Sets __project_root_path to the directory with the most matches, up to 5 levels deep.
        Sets __found_project_root to False if no marker files are found at all.

        :return: None
        """
        python_execution_path: Path = Path(argv[0]).resolve()
        frame = inspect.stack()[-1]  # get last caller frame
        caller_path: Path = Path(frame.filename)

        checkable_files_list: list[str] = [".venv", "requirements.txt", "requirements-dev.txt", ".gitignore", "README.md",
            "pyproject.toml", "setup.py", "setup.cfg", ".git"]
        found_file_paths: dict[Path, int] = {}

        for py_path in [caller_path, python_execution_path]:
            if isinstance(py_path, Path):
                current_check: Path = py_path
                for _ in range(5):
                    if current_check == current_check.parent:
                        break
                    current_check = current_check.parent
                    files = current_check.iterdir()
                    for file in files:
                        if file.name in checkable_files_list:
                            found_file_paths.setdefault(file.parent, 0)
                            found_file_paths[file.parent] += 1

        if not found_file_paths:
            self.__found_project_root = False
            return

        self.__found_project_root = True
        project_root: Path = Path(max(found_file_paths, key=found_file_paths.get))
        self.__project_root_path = Path(project_root)

    def __create_log_folder(self) -> None:
        """
        Creates the log folder on disk. Uses the project root if no custom path is set.
        Raises TaipanRootNotFoundError if neither a log path nor a project root is available.
        Raises TaipanLogPathError if the folder cannot be created due to a permission or IO error.

        :return: None
        """
        if self.__log_folder_created:
            return

        if not self._log_path and not self.__found_project_root:
            raise TaipanRootNotFoundError()
        elif not self._log_path and self.__found_project_root:
            self._log_path = Path(self.__project_root_path, "logs")
            try:
                self._log_path.mkdir(parents=True, exist_ok=True)
            except (PermissionError, FileNotFoundError, BlockingIOError):
                raise TaipanLogPathError("Could not create logs folder due to permission error or some other error.")
        else:
            if not isinstance(self._log_path, Path):
                raise TaipanLogPathError(f"The _log_path is not a proper Path.{self._log_path}")
            try:
                self._log_path.mkdir(parents=True, exist_ok=True)
            except (PermissionError, FileNotFoundError, BlockingIOError):
                raise TaipanLogPathError("Could not create logs folder due to permission error or some other error.")

        self.__log_folder_created = True

    def __handle_old_logs(self) -> None:
        """
        Enforces the max_old_logs limit by removing or archiving the oldest log files.
        Moves old logs to an 'old_logs' subfolder if delete_older_logs is False, otherwise deletes them.
        Raises TaipanLogPathError if the log folder is not set.

        :return: None
        """
        if not self._log_path:
            raise TaipanLogPathError("The log folder was not created before trying to create the file.")

        log_list: list[str] = []
        for item in self._log_path.iterdir():
            if item.suffix == ".log":
                log_list.append(item.name)
        log_list.sort()

        if len(log_list) < self._max_old_logs:
            return

        if not self._delete_older_logs:
            Path(self._log_path, "old_logs").mkdir(parents=True, exist_ok=True)

        while len(log_list) >= self._max_old_logs:
            removable: str = log_list.pop(0)

            if self._delete_older_logs:
                Path(self._log_path, removable).unlink()
            else:
                Path(self._log_path, removable).rename(Path(self._log_path, "old_logs", removable))

    def __initialize_log_file(self) -> None:
        """
        Creates the initial log file if it has not been created yet.
        Guards against repeated calls via __log_file_created.

        :return: None
        """
        if self.__log_file_created:
            return

        self.__create_new_log_file()
        self.__log_file_created = True

    def __create_new_log_file(self) -> None:
        """
        Creates a new timestamped log file in the log folder.
        Calls __handle_old_logs first to enforce the backup limit.
        Raises TaipanLogPathError if the log folder is not set.

        :return: None
        """
        if not self._log_path:
            raise TaipanLogPathError("The log folder was not created before trying to create the file.")

        self.__handle_old_logs()
        prefix: str = get_datetime_string_by_format("YYYY-MM-DD_hh-mm-ss_")
        Path(self._log_path, f"{prefix}{self._log_name}").touch()
        self.__full_log_file_path: Path = Path(self._log_path, f"{prefix}{self._log_name}")
        self.__log_creation_datetime = datetime.now()

    def __switch_log(self) -> None:
        """
        Creates a new log file and reinitializes the logger to write to it.
        Called automatically after 24 hours if keep_log_open is False.

        :return: None
        """
        self.__create_new_log_file()
        self.__setup_logger()

    def __initialize_logger(self) -> None:
        """
        Sets up the logger instance on first call.
        Guards against repeated calls via __logger_instance_initialized.

        :return: None
        """
        if self.__logger_instance_initialized:
            return

        self.__setup_logger()
        self.__logger_instance_initialized = True

    def __setup_logger(self) -> None:
        """
        Creates or replaces the internal logging.Logger instance and its file handler.
        Closes and removes all existing handlers before attaching the new one.
        Thread-safe via the internal lock.
        Raises TaipanLogPathError if _log_path is not a valid Path.

        :return: None
        """
        if not isinstance(self._log_path, Path):
            raise TaipanLogPathError(f"The log_path is not a proper Path.{self._log_path}")

        with self.__lock:
            if self.__logger_instance is not None:
                for handler in self.__logger_instance.handlers[:]:
                    handler.close()
                    self.__logger_instance.removeHandler(handler)
                del self.__logger_instance

            self.__logger_instance = logging.getLogger("TaipanLogger")
            self.__logger_instance.setLevel(logging.DEBUG if self._debug else logging.INFO)

            self.__logger_file_handler_instance: logging.FileHandler = logging.FileHandler(
                self.__full_log_file_path, mode="a"
            )
            self.__logger_file_handler_instance.setFormatter(logging.Formatter('%(message)s'))
            self.__logger_file_handler_instance.setLevel(logging.DEBUG if self._debug else logging.INFO)

            self.__logger_instance.addHandler(self.__logger_file_handler_instance)

    def __timed_checks(self) -> None:
        """
        Runs periodic maintenance on each log call.
        Checks environment variables at the configured interval and rotates the log file
        after 24 hours if keep_log_open is False.

        :return: None
        """
        current_time: datetime = datetime.now()
        if self.__next_env_check_time <= current_time:
            self.__next_env_check_time = datetime.now() + timedelta(seconds=self._env_check_interval)
            self.__check_for_system_vars()

        if not self._keep_log_open:
            if self.__log_creation_datetime + timedelta(hours=24) <= current_time:
                self.__switch_log()

    def __get_system_debug_var(self) -> bool | None:
        """
        Reads the DEBUG_ENABLED environment variable and returns it as a bool.
        Returns None if the variable is not set.

        :return: bool | None
        """
        sys_var_debug: str | None = getenv("DEBUG_ENABLED", None)
        if sys_var_debug is None:
            return

        if isinstance(sys_var_debug, str):
            if sys_var_debug.lower() == "true":
                return True
            elif sys_var_debug.lower() == "false":
                return False

    def __check_for_system_vars(self) -> None:
        """
        Compares the current DEBUG_ENABLED environment variable against the active debug state.
        If they differ, updates _debug and reinitializes the logger with the new setting.

        :return: None
        """
        if (sys_var_debug := self.__get_system_debug_var()) is None:
            return
        if self._debug == sys_var_debug:
            return
        else:
            self._debug = sys_var_debug
            self.__setup_logger()

    def _update_configuration(self, field_order: list[str] | None = None, datetime_format: str | None = None,
                               log_path: Path | str | None = None, log_path_relative: bool = True,
                               log_name: str | None = None, max_old_logs: int | None = None,
                               delete_older_logs: bool | None = None, special_prefix: str | None = None,
                               debug: bool | None = None, keep_log_open: bool | None = None,
                               env_check_interval: int | None = None, caller_path: Path | None = None) -> None:
        """
        Applies configuration options before the first log entry is written.
        Raises TaipanToLateConfiguredException if the logger is already active.
        Raises TaipanAlreadyConfiguredException if configure() was already called.
        Raises TypeError for any argument of the wrong type.
        Raises ValueError if field_order contains invalid or missing required fields.
        Raises TaipanLogPathError if the given log_path does not exist.

        :param field_order: list[str] | None - ordered list of fields to include in each log line
        :param datetime_format: str | None - custom datetime format string using taipan placeholders
        :param log_path: Path | str | None - custom path for the log folder
        :param log_path_relative: bool - if True, log_path is relative to the caller's directory
        :param log_name: str | None - base name for log files
        :param max_old_logs: int | None - maximum number of log files to keep before rotating
        :param delete_older_logs: bool | None - if True, old logs are deleted instead of archived
        :param special_prefix: str | None - optional prefix string added to every log line
        :param debug: bool | None - enables or disables debug level logging
        :param keep_log_open: bool | None - if True, the log file is never rotated automatically
        :param env_check_interval: int | None - interval in seconds between environment variable checks
        :param caller_path: Path | None - directory of the calling file, used for relative log_path resolution
        :return: None
        """
        if self.__logger_instance_initialized:
            raise TaipanToLateConfiguredException()
        if self.__is_configured:
            raise TaipanAlreadyConfiguredException()

        if field_order and not isinstance(field_order, list):
            raise TypeError("field_order is not a list")
        if datetime_format and not isinstance(datetime_format, str):
            raise TypeError("datetime_format is not a string")
        if log_path and not isinstance(log_path, str):
            raise TypeError("log_path is not a string")
        if log_path_relative and not isinstance(log_path_relative, bool):
            raise TypeError("log_path_relative is not a bool")
        if log_name and not isinstance(log_name, str):
            raise TypeError("log_name is not a string")
        if max_old_logs and not isinstance(max_old_logs, int):
            raise TypeError("max_old_logs is not a int")
        if delete_older_logs and not isinstance(delete_older_logs, bool):
            raise TypeError("delete_older_logs is not a bool")
        if special_prefix and not isinstance(special_prefix, str):
            raise TypeError("special_prefix is not a string")
        if debug and not isinstance(debug, bool):
            raise TypeError("debug is not a bool")
        if keep_log_open and not isinstance(keep_log_open, bool):
            raise TypeError("keep_log_open is not a bool")
        if env_check_interval and not isinstance(env_check_interval, int):
            raise TypeError("env_check_interval is not a int")
        if caller_path and not isinstance(caller_path, Path):
            raise TypeError("caller_path is not a Path")

        if field_order and not all([field in self._allowed_fields for field in field_order]):
            raise ValueError("The fields provided include not allowed fields: {}".format(field_order))
        # Minimum DATETIME, LOG_STATUS, MESSAGE
        if field_order and not all([needed_field in field_order for needed_field in ["DATETIME", "LOG_STATUS", "MESSAGE"]]):
            raise ValueError(
                "The fields are missing at least one of these fields: {}".format(["DATETIME", "LOG_STATUS", "MESSAGE"])
            )

        self._field_order = field_order if field_order is not None else self._field_order
        self._datetime_format = datetime_format if datetime_format is not None else self._datetime_format
        self._log_name = log_name if log_name is not None else self._log_name
        self._max_old_logs = max_old_logs if max_old_logs is not None else self._max_old_logs
        self._delete_older_logs = delete_older_logs if delete_older_logs is not None else self._delete_older_logs
        self._special_prefix = special_prefix if special_prefix is not None else self._special_prefix
        self._debug = debug if debug is not None else self._debug
        self._keep_log_open = keep_log_open if keep_log_open is not None else self._keep_log_open
        self._env_check_interval = env_check_interval if env_check_interval is not None else self._env_check_interval
        if log_path:
            if log_path_relative:
                n_path: Path = Path(caller_path, log_path)
            else:
                n_path = Path(log_path)
            if not n_path.exists():
                raise TaipanLogPathError(f"The log_path does not exist.{n_path}")
            else:
                self._log_path = n_path

        self.__is_configured = True

    def __get_nearest_function_frame_above_logger(self) -> str | None:
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
                else:
                    return frame.function

        return None

    def __build_message_string(self, message: str, log_status: str, trace_id: str = None,
                                func_name: str = None) -> str:
        """
        Assembles the final log line string from the configured fields and current context.
        Raises TaipanWrongConfiguredError if the field configuration is invalid.

        :param message: str - the log message text
        :param log_status: str - one of "DEBUG", "INFO", "WARNING", "ERROR"
        :param trace_id: str | None - optional trace ID for the current call
        :param func_name: str | None - optional function name override, auto-detected if None
        :return: str
        """
        if not all([x in self.allowed_fields for x in self._field_order]):
            raise TaipanWrongConfiguredError()
        if not all([x in self._field_order for x in ["DATETIME", "LOG_STATUS", "MESSAGE"]]):
            raise TaipanWrongConfiguredError(
                "The TaipanLogger is not configured correctly. "
                "Minimum fields needed in _field_order.:\n"
                "'DATETIME', 'LOG_STATUS', 'MESSAGE'"
            )

        if not func_name:
            func_name = self.__get_nearest_function_frame_above_logger()

        parts_dict: dict[str, str] = {
            'DATETIME':       f"[{get_datetime_string_by_format(self._datetime_format)}]",
            'LOG_STATUS':     f"[{log_status}]",
            'TRACEID':        f"[{trace_id if trace_id else 'NO TRACEID'}]",
            'THREAD':         f"[{current_thread().name}]",
            'FUNC_NAME':      f"[{func_name}]",
            'MESSAGE':        f"{message}",
            'SPECIAL_PREFIX': f"{self._special_prefix}" if self._special_prefix else "",
        }
        out_string: str = parts_dict['SPECIAL_PREFIX']
        for field in self._field_order:
            out_string += f"{parts_dict[field]}"

        return out_string

    def __log(self, message: str, log_status: str, trace_id: str = None, func_name: str = None) -> None:
        """
        Internal method that handles all log writes.
        Lazily initializes the log folder, file, and logger instance on first call.
        Runs timed checks on every call for log rotation and env variable polling.
        Raises TypeError if log_status or message are of the wrong type.
        Raises ValueError if log_status is not a valid level string.

        :param message: str - the log message text
        :param log_status: str ("DEBUG" | "INFO" | "WARNING" | "ERROR")
        :param trace_id: str | None - optional trace ID for the current call
        :param func_name: str | None - optional function name override
        :return: None
        """
        if not isinstance(log_status, str) or log_status not in ("DEBUG", "INFO", "WARNING", "ERROR"):
            raise TypeError("status_id must be 'DEBUG', INFO', 'WARNING' or 'ERROR'.")
        if not isinstance(message, str):
            raise TypeError("message must be a string")

        if not self.__log_folder_created:
            self.__create_log_folder()
        if not self.__log_file_created:
            self.__initialize_log_file()
        if not self.__logger_instance_initialized:
            self.__initialize_logger()

        self.__timed_checks()

        log_string: str = self.__build_message_string(
            message=message, log_status=log_status, trace_id=trace_id, func_name=func_name
        )
        match log_status:
            case "DEBUG":
                self.__logger_instance.debug(log_string)
            case "INFO":
                self.__logger_instance.info(log_string)
            case "WARNING":
                self.__logger_instance.warning(log_string)
            case "ERROR":
                self.__logger_instance.error(log_string)
            case _:
                raise ValueError(f"log_status must be 'DEBUG', INFO', 'WARNING' or 'ERROR': " + log_status)

    def debug(self, message: str, trace_id: str = None, func_name: str = None) -> None:
        """
        Writes a DEBUG level log entry.

        :param message: str - the log message text
        :param trace_id: str | None - optional trace ID for the current call
        :param func_name: str | None - optional function name override
        :return: None
        """
        self.__log(message=message, log_status="DEBUG", trace_id=trace_id, func_name=func_name)

    def info(self, message: str, trace_id: str = None, func_name: str = None) -> None:
        """
        Writes an INFO level log entry.

        :param message: str - the log message text
        :param trace_id: str | None - optional trace ID for the current call
        :param func_name: str | None - optional function name override
        :return: None
        """
        self.__log(message=message, log_status="INFO", trace_id=trace_id, func_name=func_name)

    def warning(self, message: str, trace_id: str = None, func_name: str = None) -> None:
        """
        Writes a WARNING level log entry.

        :param message: str - the log message text
        :param trace_id: str | None - optional trace ID for the current call
        :param func_name: str | None - optional function name override
        :return: None
        """
        self.__log(message=message, log_status="WARNING", trace_id=trace_id, func_name=func_name)

    def error(self, message: str, trace_id: str = None, func_name: str = None) -> None:
        """
        Writes an ERROR level log entry.

        :param message: str - the log message text
        :param trace_id: str | None - optional trace ID for the current call
        :param func_name: str | None - optional function name override
        :return: None
        """
        self.__log(message=message, log_status="ERROR", trace_id=trace_id, func_name=func_name)

    @classmethod
    def get_instance(cls) -> "TaipanLogger":
        """
        Returns the current singleton instance of TaipanLogger.

        :return: TaipanLogger
        """
        return cls._instance


if not globals().get("__INIT_DONE", False):
    __INIT_DONE: bool = True
    taipan: TaipanLogger = TaipanLogger()
    taipan.__doc__ = TaipanLogger.__doc__


def configure(field_order: list[str] | None = None, datetime_format: str | None = None,
              log_path: Path | str | None = None, log_path_relative: bool = True, log_name: str | None = None,
              max_old_logs: int | None = None, delete_older_logs: bool | None = None,
              special_prefix: str | None = None, debug: bool | None = None, keep_log_open: bool | None = None,
              env_check_interval: int | None = None) -> None:
    """
    Module-level convenience function to configure the TaipanLogger singleton before first use.
    Must be called before any log entry is written, otherwise raises TaipanToLateConfiguredException.
    Automatically resolves the caller's directory for relative log path support.

    :param field_order: list[str] | None - ordered list of fields to include in each log line
    :param datetime_format: str | None - custom datetime format string using taipan placeholders
    :param log_path: Path | str | None - custom path for the log folder
    :param log_path_relative: bool - if True, log_path is relative to the caller's directory
    :param log_name: str | None - base name for log files
    :param max_old_logs: int | None - maximum number of log files to keep before rotating
    :param delete_older_logs: bool | None - if True, old logs are deleted instead of archived
    :param special_prefix: str | None - optional prefix string added to every log line
    :param debug: bool | None - enables or disables debug level logging
    :param keep_log_open: bool | None - if True, the log file is never rotated automatically
    :param env_check_interval: int | None - interval in seconds between environment variable checks
    :return: None
    """
    frame = inspect.stack()[1]
    caller_path: Path = Path(frame.filename).parent
    taipan_instance: TaipanLogger = TaipanLogger.get_instance()
    taipan_instance._update_configuration(
        field_order=field_order, datetime_format=datetime_format, log_path=log_path,
        log_path_relative=log_path_relative, log_name=log_name, max_old_logs=max_old_logs,
        delete_older_logs=delete_older_logs, special_prefix=special_prefix, debug=debug,
        keep_log_open=keep_log_open, env_check_interval=env_check_interval, caller_path=caller_path
    )


if __name__ == "__main__":
    print("Dont start the package files alone! The imports wont work like this!")