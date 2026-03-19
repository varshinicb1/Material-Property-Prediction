"""Rich-based logging utilities."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

_CUSTOM_THEME = Theme(
    {
        "info": "cyan",
        "warning": "yellow bold",
        "error": "red bold",
        "success": "green bold",
        "highlight": "magenta",
    }
)

console = Console(theme=_CUSTOM_THEME)


def get_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """Create a Rich-formatted logger.

    Args:
        name: Logger name (usually __name__).
        level: Log level string (DEBUG, INFO, WARNING, ERROR).
        log_file: Optional path to write logs to file.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        rich_handler = RichHandler(
            console=console,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            show_time=True,
            show_path=False,
            markup=True,
        )
        rich_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        logger.addHandler(rich_handler)

        if log_file is not None:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            file_handler.setLevel(logging.DEBUG)
            logger.addHandler(file_handler)

    return logger


def log_section(logger: logging.Logger, title: str) -> None:
    """Log a section header for visual separation."""
    logger.info(f"[bold magenta]{'=' * 60}[/bold magenta]")
    logger.info(f"[bold magenta]  {title}[/bold magenta]")
    logger.info(f"[bold magenta]{'=' * 60}[/bold magenta]")
