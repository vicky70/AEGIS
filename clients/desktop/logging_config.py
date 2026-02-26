"""AEGIS Desktop Monitor — centralised logging setup.

Configures the ``aegis`` logger hierarchy to write to both a rotating
file (C:\\ProgramData\\AEGIS\\aegis.log) and the console.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

_LOG_DIR = r"C:\ProgramData\AEGIS"
_LOG_FILE = os.path.join(_LOG_DIR, "aegis.log")
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 3
_FORMAT = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"


def setup_logging() -> None:
    """Configure the root ``aegis`` logger with file + console handlers."""
    os.makedirs(_LOG_DIR, exist_ok=True)

    root_logger = logging.getLogger("aegis")
    root_logger.setLevel(logging.DEBUG)

    # Avoid adding duplicate handlers if called more than once
    if root_logger.handlers:
        return

    formatter = logging.Formatter(_FORMAT)

    # Rotating file handler
    file_handler = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Console handler (useful when running interactively)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
