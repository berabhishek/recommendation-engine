import os
import importlib
from pathlib import Path
from unittest import mock
import pytest

def test_default_settings():
    with mock.patch.dict(os.environ, {}, clear=True):
        import app.settings
        importlib.reload(app.settings)

        assert app.settings.DATABASE_URL.startswith("sqlite:///")
        assert app.settings.DEFAULT_PAGE_SIZE == 25
        assert app.settings.MAX_PAGE_SIZE == 100
        assert str(app.settings.DATA_DIR).endswith("raw data")

def test_custom_settings():
    env = {
        "DATABASE_URL": "postgresql://user:pass@localhost/db",
        "DATA_DIR": "/tmp/data",
        "DEFAULT_PAGE_SIZE": "10",
        "MAX_PAGE_SIZE": "50",
    }
    with mock.patch.dict(os.environ, env, clear=True):
        import app.settings
        importlib.reload(app.settings)

        assert app.settings.DATABASE_URL == "postgresql://user:pass@localhost/db"
        assert str(app.settings.DATA_DIR) == "/tmp/data"
        assert app.settings.DEFAULT_PAGE_SIZE == 10
        assert app.settings.MAX_PAGE_SIZE == 50
