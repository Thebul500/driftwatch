"""Tests for application configuration."""

import os
from unittest.mock import patch

from driftwatch.config import Settings, settings


def test_settings_defaults():
    """Settings has expected defaults."""
    s = Settings()
    assert s.debug is False
    assert s.access_token_expire_minutes == 30
    assert s.secret_key == "change-me-in-production"
    assert "driftwatch" in s.database_url


def test_settings_env_prefix():
    """Settings uses DRIFTWATCH_ env prefix."""
    assert Settings.model_config["env_prefix"] == "DRIFTWATCH_"


def test_settings_from_env():
    """Settings can be overridden via environment variables."""
    with patch.dict(os.environ, {"DRIFTWATCH_DEBUG": "true", "DRIFTWATCH_SECRET_KEY": "test-key"}):
        s = Settings()
        assert s.debug is True
        assert s.secret_key == "test-key"


def test_module_level_settings():
    """Module-level settings instance exists."""
    assert settings is not None
    assert isinstance(settings, Settings)
