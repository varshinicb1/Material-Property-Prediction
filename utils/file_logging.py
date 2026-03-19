"""File-based logging configuration for production deployments.

Provides structured logging to both console and files with rotation.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

from rich.logging import RichHandler


def setup_file_logging(
    log_dir: str = "logs",
    log_level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True,
) -> logging.Logger:
    """Setup file-based logging with rotation.
    
    Args:
        log_dir: Directory for log files.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        max_bytes: Maximum size of each log file before rotation.
        backup_count: Number of backup files to keep.
        enable_console: Whether to also log to console.
        
    Returns:
        Configured logger instance.
    """
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("material_ai")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_path / "material_ai.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Error file handler (only errors and critical)
    error_handler = RotatingFileHandler(
        log_path / "material_ai_errors.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)
    
    # Console handler with Rich formatting
    if enable_console:
        console_handler = RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_time=False,
            show_path=False,
        )
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)
    
    logger.info(f"Logging initialized: {log_path.absolute()}")
    return logger


def get_file_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.
    
    Args:
        name: Module name (typically __name__).
        
    Returns:
        Logger instance.
    """
    return logging.getLogger(f"material_ai.{name}")
