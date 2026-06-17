"""General utils smoke tests."""
import importlib
import pytest


def test_constants_importable():
    mod = importlib.import_module("utils.constants")
    assert mod is not None


def test_calculations_importable():
    mod = importlib.import_module("utils.calculations")
    assert mod is not None


def test_logger_importable():
    mod = importlib.import_module("utils.logger")
    assert mod is not None


def test_notifications_importable():
    mod = importlib.import_module("utils.notifications")
    assert mod is not None


def test_alerts_importable():
    mod = importlib.import_module("utils.alerts")
    assert mod is not None
