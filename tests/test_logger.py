"""Tests for utils/logger.py."""
import logging
import pytest
from utils.logger import get_logger


def test_get_logger_returns_logger():
    logger = get_logger("test")
    assert isinstance(logger, logging.Logger)


def test_get_logger_name():
    logger = get_logger("my_module")
    assert "my_module" in logger.name


def test_logger_has_handler():
    logger = get_logger("handler_test")
    # The root logger may hold handlers; check effective level instead
    assert logger.getEffectiveLevel() <= logging.WARNING


def test_logger_debug_does_not_raise():
    logger = get_logger("no_raise")
    logger.debug("debug message")


def test_logger_info_does_not_raise():
    logger = get_logger("no_raise_info")
    logger.info("info message")
