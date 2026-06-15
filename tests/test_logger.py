"""Unit tests for utils/logger.py."""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import pytest


# ===========================================================================
# get_logger
# ===========================================================================
class TestGetLogger:
    def test_returns_logger_instance(self):
        from utils.logger import get_logger
        log = get_logger("test.module")
        assert isinstance(log, logging.Logger)

    def test_name_prefixed_with_nse_tracker(self):
        from utils.logger import get_logger
        log = get_logger("some.module")
        assert log.name.startswith("nse_tracker")

    def test_already_prefixed_name_unchanged(self):
        from utils.logger import get_logger
        log = get_logger("nse_tracker.already")
        assert log.name == "nse_tracker.already"

    def test_same_name_returns_same_logger(self):
        from utils.logger import get_logger
        a = get_logger("utils.data")
        b = get_logger("utils.data")
        assert a is b

    def test_logger_has_parent_handlers(self):
        from utils.logger import get_logger
        log = get_logger("test.handlers")
        root = logging.getLogger("nse_tracker")
        # After _configure(), root should have at least one handler
        assert len(root.handlers) >= 1


# ===========================================================================
# log_file_path
# ===========================================================================
class TestLogFilePath:
    def test_returns_string(self):
        from utils.logger import log_file_path
        assert isinstance(log_file_path(), str)

    def test_ends_with_app_log(self):
        from utils.logger import log_file_path
        assert log_file_path().endswith("app.log")

    def test_path_contains_logs_directory(self):
        from utils.logger import log_file_path
        assert "logs" in log_file_path()


# ===========================================================================
# read_recent_logs
# ===========================================================================
class TestReadRecentLogs:
    def test_returns_list(self):
        from utils.logger import read_recent_logs
        result = read_recent_logs(10)
        assert isinstance(result, list)

    def test_returns_at_most_n_lines(self):
        from utils.logger import read_recent_logs
        result = read_recent_logs(5)
        assert len(result) <= 5

    def test_nonexistent_file_returns_empty_list(self, tmp_path, monkeypatch):
        import utils.logger as _l
        monkeypatch.setattr(_l, "_LOG_FILE", tmp_path / "nonexistent.log")
        from utils.logger import read_recent_logs
        result = read_recent_logs(100)
        assert result == []

    def test_reads_lines_from_real_file(self, tmp_path, monkeypatch):
        import utils.logger as _l
        fake_log = tmp_path / "test.log"
        fake_log.write_text("line1\nline2\nline3\n", encoding="utf-8")
        monkeypatch.setattr(_l, "_LOG_FILE", fake_log)
        result = read_recent_logs(10)
        assert "line1" in result
        assert "line3" in result

    def test_respects_n_limit(self, tmp_path, monkeypatch):
        import utils.logger as _l
        fake_log = tmp_path / "big.log"
        fake_log.write_text("\n".join(f"line{i}" for i in range(200)), encoding="utf-8")
        monkeypatch.setattr(_l, "_LOG_FILE", fake_log)
        result = read_recent_logs(50)
        assert len(result) == 50

    def test_returns_tail_not_head(self, tmp_path, monkeypatch):
        import utils.logger as _l
        fake_log = tmp_path / "tail.log"
        lines = [f"line{i}" for i in range(100)]
        fake_log.write_text("\n".join(lines), encoding="utf-8")
        monkeypatch.setattr(_l, "_LOG_FILE", fake_log)
        result = read_recent_logs(10)
        assert "line99" in result
        assert "line0"  not in result
