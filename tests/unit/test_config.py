"""Unit tests for Configuration with precedence testing (T099).

Tests User Story 7: Production Polish - Configuration Management.
"""

import os
import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from scripts.cdp.config import Configuration


class TestConfigurationPrecedence:
    """T099: Test configuration precedence (CLI > env > file > defaults)."""

    def test_default_values(self):
        """Verify default configuration values are set correctly."""
        config = Configuration()

        # Default values per spec
        assert config.chrome_port == 9222
        assert config.timeout == 30.0
        assert config.max_size == 2_097_152  # 2MB
        assert config.log_level == "INFO"
        assert config.log_format == "text"

    def test_load_from_file(self):
        """Verify configuration loads from ~/.cdprc file."""
        with TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".cdprc"
            config_data = {"chrome_port": 9333, "timeout": 60.0, "log_level": "DEBUG"}
            config_file.write_text(json.dumps(config_data))

            config = Configuration()
            config.load_from_file(str(config_file))

            assert config.chrome_port == 9333
            assert config.timeout == 60.0
            assert config.log_level == "DEBUG"
            # Defaults still apply for unset values
            assert config.max_size == 2_097_152

    def test_load_from_env(self):
        """Verify configuration loads from CDP_* environment variables."""
        # Set environment variables
        os.environ["CDP_CHROME_PORT"] = "9444"
        os.environ["CDP_TIMEOUT"] = "45.0"
        os.environ["CDP_LOG_LEVEL"] = "WARNING"

        try:
            config = Configuration()
            config.load_from_env()

            assert config.chrome_port == 9444
            assert config.timeout == 45.0
            assert config.log_level == "WARNING"
            # Defaults still apply
            assert config.max_size == 2_097_152
        finally:
            # Cleanup
            os.environ.pop("CDP_CHROME_PORT", None)
            os.environ.pop("CDP_TIMEOUT", None)
            os.environ.pop("CDP_LOG_LEVEL", None)

    def test_cli_overrides_all(self):
        """Verify CLI arguments override env vars and config file."""
        with TemporaryDirectory() as tmpdir:
            # Set up config file
            config_file = Path(tmpdir) / ".cdprc"
            config_data = {"chrome_port": 9333, "timeout": 60.0}
            config_file.write_text(json.dumps(config_data))

            # Set up environment variables
            os.environ["CDP_CHROME_PORT"] = "9444"
            os.environ["CDP_TIMEOUT"] = "45.0"

            try:
                config = Configuration()
                config.load_from_file(str(config_file))
                config.load_from_env()

                # CLI overrides (highest precedence)
                config.merge(chrome_port=9555, timeout=20.0)

                assert config.chrome_port == 9555  # CLI wins
                assert config.timeout == 20.0  # CLI wins
            finally:
                os.environ.pop("CDP_CHROME_PORT", None)
                os.environ.pop("CDP_TIMEOUT", None)

    def test_precedence_chain_file_env_cli(self):
        """Test complete precedence chain: defaults < file < env < CLI."""
        with TemporaryDirectory() as tmpdir:
            # Defaults: port=9222, timeout=30.0, max_size=2097152, log_level=INFO

            # File: port=9333, timeout=60.0
            config_file = Path(tmpdir) / ".cdprc"
            config_data = {"chrome_port": 9333, "timeout": 60.0}
            config_file.write_text(json.dumps(config_data))

            # Env: port=9444, log_level=DEBUG
            os.environ["CDP_CHROME_PORT"] = "9444"
            os.environ["CDP_LOG_LEVEL"] = "DEBUG"

            try:
                config = Configuration()
                config.load_from_file(str(config_file))
                config.load_from_env()
                # CLI: timeout=15.0
                config.merge(timeout=15.0)

                # Verify precedence
                assert config.chrome_port == 9444  # Env wins over file
                assert config.timeout == 15.0  # CLI wins over file
                assert config.log_level == "DEBUG"  # Env wins (no CLI override)
                assert config.max_size == 2_097_152  # Default (no override)
            finally:
                os.environ.pop("CDP_CHROME_PORT", None)
                os.environ.pop("CDP_LOG_LEVEL", None)

    def test_invalid_config_file_graceful_fallback(self):
        """Verify invalid config file doesn't crash, uses defaults."""
        with TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".cdprc"
            config_file.write_text("INVALID JSON{{{")

            config = Configuration()
            config.load_from_file(str(config_file))

            # Should fall back to defaults
            assert config.chrome_port == 9222
            assert config.timeout == 30.0

    def test_nonexistent_config_file_ignored(self):
        """Verify nonexistent config file is silently ignored."""
        config = Configuration()
        config.load_from_file("/nonexistent/path/.cdprc")

        # Should use defaults
        assert config.chrome_port == 9222
        assert config.timeout == 30.0

    def test_partial_config_file(self):
        """Verify partial config file merges with defaults."""
        with TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".cdprc"
            # Only set one value
            config_data = {"chrome_port": 9999}
            config_file.write_text(json.dumps(config_data))

            config = Configuration()
            config.load_from_file(str(config_file))

            assert config.chrome_port == 9999  # From file
            assert config.timeout == 30.0  # Default
            assert config.max_size == 2_097_152  # Default


class TestConfigurationTypes:
    """Test type conversion and validation."""

    def test_port_type_conversion_from_env(self):
        """Verify environment variables are converted to correct types."""
        os.environ["CDP_CHROME_PORT"] = "9333"  # String
        os.environ["CDP_TIMEOUT"] = "45.5"  # String

        try:
            config = Configuration()
            config.load_from_env()

            assert isinstance(config.chrome_port, int)
            assert config.chrome_port == 9333
            assert isinstance(config.timeout, float)
            assert config.timeout == 45.5
        finally:
            os.environ.pop("CDP_CHROME_PORT", None)
            os.environ.pop("CDP_TIMEOUT", None)

    def test_invalid_env_var_ignored(self):
        """Verify invalid environment variable values are ignored."""
        os.environ["CDP_CHROME_PORT"] = "not_a_number"

        try:
            config = Configuration()
            config.load_from_env()

            # Should fall back to default
            assert config.chrome_port == 9222
        finally:
            os.environ.pop("CDP_CHROME_PORT", None)
