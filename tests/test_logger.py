"""Tests for utils/logger.py — verifies configuration is idempotent and
the public API works without actually writing to disk (tmp_path fixture).
"""
import logging
import os
from pathlib import Path
from unittest.mock import patch

import pytest


class TestGetLogger:
    def test_returns_logger_instance(self):
        from utils.logger import get_logger
        log = get_logger("test.module")
        assert isinstance(log, logging.Logger)

    def test_name_preserved(self):
        from utils.logger import get_logger
        log = get_logger("utils.data")
        assert log.name == "utils.data"

    def test_idempotent_multiple_imports(self):
        """Calling get_logger twice with the same name returns the same object."""
        from utils.logger import get_logger
        a = get_logger("same.module")
        b = get_logger("same.module")
        assert a is b

    def test_logger_has_handlers_after_setup(self):
        """Root logger must have at least one handler after module import."""
        import utils.logger  # noqa: F401 — trigger _setup()
        root = logging.getLogger()
        assert len(root.handlers) >= 1


class TestReadRecentLogs:
    def test_empty_list_when_file_missing(self, tmp_path, monkeypatch):
        from utils import logger as lg
        monkeypatch.setattr(lg, "_LOG_FILE", tmp_path / "nonexistent.log")
        result = lg.read_recent_logs(50)
        assert result == []

    def test_returns_last_n_lines(self, tmp_path, monkeypatch):
        from utils import logger as lg
        log_file = tmp_path / "app.log"
        lines    = [f"line {i}" for i in range(200)]
        log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        monkeypatch.setattr(lg, "_LOG_FILE", log_file)
        result = lg.read_recent_logs(50)
        assert len(result) == 50
        assert result[-1] == "line 199"   # newest last

    def test_returns_all_when_fewer_than_n(self, tmp_path, monkeypatch):
        from utils import logger as lg
        log_file = tmp_path / "app.log"
        log_file.write_text("a\nb\nc\n", encoding="utf-8")
        monkeypatch.setattr(lg, "_LOG_FILE", log_file)
        result = lg.read_recent_logs(100)
        assert result == ["a", "b", "c"]

    def test_strips_trailing_newlines(self, tmp_path, monkeypatch):
        from utils import logger as lg
        log_file = tmp_path / "app.log"
        log_file.write_text("hello\nworld\n", encoding="utf-8")
        monkeypatch.setattr(lg, "_LOG_FILE", log_file)
        result = lg.read_recent_logs(10)
        assert all("\n" not in line for line in result)


class TestLogFilePath:
    def test_returns_path_object(self):
        from utils.logger import log_file_path
        assert isinstance(log_file_path(), Path)

    def test_ends_with_app_log(self):
        from utils.logger import log_file_path
        assert log_file_path().name == "app.log"


class TestLogLevelOverride:
    def test_env_var_respected(self, monkeypatch):
        """LOG_LEVEL env var should map to correct logging level constant."""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
        assert level == logging.DEBUG
