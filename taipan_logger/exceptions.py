"""
Defines all custom exception and warning classes used across the taipan logger package.
Provides structured base classes and specific error types for configuration and path problems.

:author: sora7672
"""

__author__: str = "sora7672"


class OOPException(Exception):
    """
    Base exception class that extends the built-in Exception with structured fields.
    Allows callers to access the message, error code, and any extra data directly as attributes.
    """

    def __init__(self, message: str = None, error_code: int = None, **kwargs):
        """
        Stores the message, error code, and any additional keyword arguments as structured data.
        Raises TypeError if message is not a string or error_code is not an int.

        :param message: str | None - human-readable description of the error
        :param error_code: int | None - optional numeric code identifying the error type
        :param kwargs: any additional context data to attach to the exception
        """
        if message and not isinstance(message, str):
            raise TypeError("message must be a string")
        if error_code and not isinstance(error_code, int):
            raise TypeError("error_code must be a numeric code")
        self.message: str = message
        self.error_code: int = error_code
        self.data: dict = kwargs or {}

        super().__init__(self.message)


class OOPWarning(Warning):
    """
    Base warning class that mirrors OOPException but extends Warning instead of Exception.
    Allows callers to access the message, error code, and any extra data directly as attributes.
    """

    def __init__(self, message: str = None, error_code: int = None, **kwargs):
        """
        Stores the message, error code, and any additional keyword arguments as structured data.
        Raises TypeError if message is not a string or error_code is not an int.

        :param message: str | None - human-readable description of the warning
        :param error_code: int | None - optional numeric code identifying the warning type
        :param kwargs: any additional context data to attach to the warning
        """
        if message and not isinstance(message, str):
            raise TypeError("message must be a string")
        if error_code and not isinstance(error_code, int):
            raise TypeError("error_code must be a numeric code")
        self.message: str = message
        self.error_code: int = error_code
        self.data: dict = kwargs or {}

        super().__init__(self.message)


class TaipanRootNotFoundError(OOPException):
    """
    Raised when the project root directory cannot be located during logger initialization.
    Lists the marker files that are checked and suggests how to resolve the issue.
    """

    def __init__(self, message: str = None, error_code: int = None, **kwargs):
        """
        Sets a default message if none is provided and delegates to OOPException.

        :param message: str | None - description of the root detection failure
        :param error_code: int | None - optional numeric code identifying the error type
        :param kwargs: any additional context data to attach to the exception
        """
        if message and not isinstance(message, str):
            raise TypeError("message must be a string")
        if error_code and not isinstance(error_code, int):
            raise TypeError("error_code must be a numeric code")
        self.message: str = message if message else (
            "Could not find the root directory to initialize taipan_logger.\n"
            "We check on '.gitignore', 'README.md', '/.venv' or "
            "'requirements.txt'.\nSet the project properly up, use environment "
            "variables or use configure()."
        )

        super().__init__(message=self.message, error_code=error_code, **kwargs)


class TaipanLogPathError(OOPException):
    """
    Raised when the log path is invalid, missing, or cannot be created.
    """

    def __init__(self, message: str = None, error_code: int = None, **kwargs):
        """
        Sets a default message if none is provided and delegates to OOPException.

        :param message: str | None - description of the log path problem
        :param error_code: int | None - optional numeric code identifying the error type
        :param kwargs: any additional context data to attach to the exception
        """
        if message and not isinstance(message, str):
            raise TypeError("message must be a string")
        if error_code and not isinstance(error_code, int):
            raise TypeError("error_code must be a numeric code")
        self.message: str = message if message else "There was an error with the log path"

        super().__init__(message=self.message, error_code=error_code, **kwargs)


class TaipanToLateConfiguredException(OOPException):
    """
    Raised when configure() is called after the logger has already written its first log entry.
    Suggests using the DEBUG_ENABLED environment variable as an alternative.
    """

    def __init__(self, message: str = None, error_code: int = None, **kwargs):
        """
        Sets a default message if none is provided and delegates to OOPException.

        :param message: str | None - description of the timing violation
        :param error_code: int | None - optional numeric code identifying the error type
        :param kwargs: any additional context data to attach to the exception
        """
        if message and not isinstance(message, str):
            raise TypeError("message must be a string")
        if error_code and not isinstance(error_code, int):
            raise TypeError("error_code must be a numeric code")
        self.message: str = message if message else (
            "You can not configure the logger at this time. Only before first log is written.\n"
            "To enable debug, use the boolean environment variable 'DEBUG_ENABLED'"
        )

        super().__init__(message=self.message, error_code=error_code, **kwargs)


class TaipanWrongConfiguredError(OOPException):
    """
    Raised when one or more internal logger attributes are set to invalid values.
    """

    def __init__(self, message: str = None, error_code: int = None, **kwargs):
        """
        Sets a default message if none is provided and delegates to OOPException.

        :param message: str | None - description of the misconfiguration
        :param error_code: int | None - optional numeric code identifying the error type
        :param kwargs: any additional context data to attach to the exception
        """
        if message and not isinstance(message, str):
            raise TypeError("message must be a string")
        if error_code and not isinstance(error_code, int):
            raise TypeError("error_code must be a numeric code")
        self.message: str = message if message else "Anyhow some attributes of the TaipanLogger are set wrong!"

        super().__init__(message=self.message, error_code=error_code, **kwargs)


class TaipanAlreadyConfiguredException(OOPWarning):
    """
    Raised as a warning when configure() is called more than once.
    Suggests using environment variables for runtime configuration changes instead.
    """

    def __init__(self, message: str = None, error_code: int = None, **kwargs):
        """
        Always uses the fixed default message regardless of what is passed in,
        then delegates to OOPWarning.

        :param message: str | None - ignored, a fixed message is always used
        :param error_code: int | None - ignored, always passed as None
        :param kwargs: any additional context data to attach to the warning
        """
        if message and not isinstance(message, str):
            raise TypeError("message must be a string")
        if error_code and not isinstance(error_code, int):
            raise TypeError("error_code must be a numeric code")
        self.message: str = (
            "taipan_logger is already configured. You tryed to configure it multiple times.\n"
            "To change the configuration while runtime, please use environment variables and "
            "set the check timer for it as needed."
        )
        super().__init__(message=self.message, error_code=None, **kwargs)


if __name__ == "__main__":
    print("Dont start the package files alone! The imports wont work like this!")