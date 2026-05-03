"""
framework.logging_setup — Infrastructure Logging
================================================
Version : 1.0.0
SDD     : Design/SDD/SDD_logging.md

Centralized logging and global exception handler — P1/P2 improvement.

Call ``setup_logging()`` and ``setup_exception_handler()`` once at startup
(in AppFactory.run or BaseApp.run) before any other component is created.

Usage::

    from framework.logging_setup import setup_logging, setup_exception_handler
    setup_logging(level=logging.DEBUG, log_file="app.log")
    setup_exception_handler()
"""

import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

_framework_logger = logging.getLogger("framework")


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    fmt: str = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
) -> None:
    """Configure the root logger.

    Args:
        level:    Minimum log level (e.g. logging.DEBUG).
        log_file: Optional path to a rotating log file (max 5 MB × 3 backups).
        fmt:      Log record format string.
    """
    handlers: list = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(
            RotatingFileHandler(
                log_file,
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
        )

    logging.basicConfig(level=level, format=fmt, handlers=handlers, force=True)
    _framework_logger.debug("Logging initialised (level=%s)", logging.getLevelName(level))


def setup_exception_handler() -> None:
    """Install a global ``sys.excepthook`` that logs unhandled exceptions.

    Without this, unhandled exceptions in the main thread silently print a
    traceback but are never recorded in log files.
    """

    def _handle_uncaught(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            # Let Ctrl-C exit gracefully without a logged traceback.
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        _framework_logger.critical(
            "Unhandled exception — application may be in an inconsistent state.",
            exc_info=(exc_type, exc_value, exc_tb),
        )

    sys.excepthook = _handle_uncaught
    _framework_logger.debug("Global exception handler installed.")
