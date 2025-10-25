"""Configuration management for CDP tools.

Supports multiple configuration sources with precedence:
CLI flags > Environment variables > Config file > Defaults

Usage:
    >>> config = Configuration()
    >>> config.load_from_file("~/.cdprc")
    >>> config.load_from_env()
    >>> config.merge(chrome_port=9333)  # CLI overrides
    >>> print(config.chrome_port)
    9333
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)


class Configuration:
    """Configuration manager with layered precedence.

    Precedence order (highest to lowest):
    1. CLI arguments (via merge method)
    2. Environment variables (CDP_* prefix)
    3. Config file (~/.cdprc JSON)
    4. Default values

    Attributes:
        chrome_port: Chrome remote debugging port (default: 9222)
        timeout: CDP command timeout in seconds (default: 30.0)
        max_size: Maximum WebSocket message size in bytes (default: 2MB)
        log_level: Logging level (default: "INFO")
        log_format: Log output format "text" or "json" (default: "text")
    """

    # Default configuration values
    DEFAULTS = {
        "chrome_port": 9222,
        "timeout": 30.0,
        "max_size": 2_097_152,  # 2MB
        "log_level": "INFO",
        "log_format": "text",
    }

    def __init__(self):
        """Initialize configuration with default values."""
        self.chrome_port: int = self.DEFAULTS["chrome_port"]
        self.timeout: float = self.DEFAULTS["timeout"]
        self.max_size: int = self.DEFAULTS["max_size"]
        self.log_level: str = self.DEFAULTS["log_level"]
        self.log_format: str = self.DEFAULTS["log_format"]

    def load_from_file(self, file_path: str) -> None:
        """Load configuration from JSON file.

        Args:
            file_path: Path to config file (typically ~/.cdprc)

        Note:
            Invalid JSON or missing file is silently ignored with warning log.
            Partial configs are merged with existing values.
        """
        path = Path(file_path).expanduser()

        if not path.exists():
            logger.debug(f"Config file not found: {path}")
            return

        try:
            with open(path, "r") as f:
                data = json.load(f)

            self._merge_dict(data)
            logger.info(f"Loaded configuration from {path}")

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in config file {path}: {e}")
        except Exception as e:
            logger.warning(f"Error loading config file {path}: {e}")

    def load_from_env(self) -> None:
        """Load configuration from environment variables.

        Environment variables use CDP_ prefix:
        - CDP_CHROME_PORT
        - CDP_TIMEOUT
        - CDP_MAX_SIZE
        - CDP_LOG_LEVEL
        - CDP_LOG_FORMAT

        Invalid values are silently ignored with warning log.
        """
        env_mappings = {
            "CDP_CHROME_PORT": ("chrome_port", int),
            "CDP_TIMEOUT": ("timeout", float),
            "CDP_MAX_SIZE": ("max_size", int),
            "CDP_LOG_LEVEL": ("log_level", str),
            "CDP_LOG_FORMAT": ("log_format", str),
        }

        for env_var, (attr_name, type_converter) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    converted_value = type_converter(value)
                    setattr(self, attr_name, converted_value)
                    logger.debug(f"Loaded {attr_name}={converted_value} from {env_var}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid value for {env_var}: {value} ({e})")

    def merge(self, **kwargs) -> None:
        """Merge CLI arguments into configuration (highest precedence).

        Args:
            **kwargs: Configuration key-value pairs to override

        Example:
            >>> config.merge(chrome_port=9333, timeout=15.0)
        """
        self._merge_dict(kwargs)

    def _merge_dict(self, data: dict) -> None:
        """Internal helper to merge dictionary into configuration.

        Args:
            data: Dictionary with configuration keys matching attribute names
        """
        for key, value in data.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
                logger.debug(f"Set {key}={value}")

    def to_dict(self) -> dict:
        """Export configuration as dictionary.

        Returns:
            Dictionary with all configuration values
        """
        return {
            "chrome_port": self.chrome_port,
            "timeout": self.timeout,
            "max_size": self.max_size,
            "log_level": self.log_level,
            "log_format": self.log_format,
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"Configuration({self.to_dict()})"
