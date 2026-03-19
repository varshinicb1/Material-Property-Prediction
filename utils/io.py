"""I/O utilities for saving and loading models and data."""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np

from utils.logging import get_logger

logger = get_logger(__name__)


def save_pickle(obj: Any, path: Path) -> None:
    """Save any Python object as pickle.

    Args:
        obj: Object to serialize.
        path: Destination file path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
    logger.debug(f"Saved pickle: {path}")


def load_pickle(path: Path) -> Any:
    """Load a pickle file.

    Args:
        path: Source file path.

    Returns:
        Deserialized object.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Pickle file not found: {path}")
    with open(path, "rb") as f:
        obj = pickle.load(f)
    logger.debug(f"Loaded pickle: {path}")
    return obj


def save_json(data: dict[str, Any], path: Path) -> None:
    """Save dictionary as JSON.

    Args:
        data: Dictionary to serialize.
        path: Destination file path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=_json_default)
    logger.debug(f"Saved JSON: {path}")


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON file.

    Args:
        path: Source file path.

    Returns:
        Loaded dictionary.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.debug(f"Loaded JSON: {path}")
    return data


def _json_default(obj: Any) -> Any:
    """Handle non-serializable types for JSON."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
