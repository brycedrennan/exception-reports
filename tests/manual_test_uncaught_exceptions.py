import sys
from logging.config import dictConfig

from exception_reports.logs import DEFAULT_LOGGING_CONFIG, uncaught_exception_handler


def main():
    # Configure logging to use our filter and formatter
    dictConfig(DEFAULT_LOGGING_CONFIG)

    # configure uncaught exceptions to be logged
    sys.excepthook = uncaught_exception_handler

    class SpecialArgsException(Exception):
        def __init__(self, message, important_var):
            super().__init__(message)

    try:
        raise SpecialArgsException("<strong>YOLO!!!!</strong>", 24)
    except Exception:
        raise SpecialArgsException("<strong>HELLO</strong>", 34)  # noqa
