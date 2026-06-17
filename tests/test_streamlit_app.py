"""Smoke tests for the top-level app.py structure (no Streamlit runtime needed)."""
import ast
import os
import pytest


APP_PATH = os.path.join(os.path.dirname(__file__), "..", "app.py")


def test_app_py_exists():
    assert os.path.isfile(APP_PATH), "app.py not found at repo root"


def test_app_py_is_valid_python():
    """Parse app.py as AST -- catches syntax errors without executing."""
    with open(APP_PATH, "r", encoding="utf-8") as fh:
        source = fh.read()
    tree = ast.parse(source)  # raises SyntaxError if broken
    assert tree is not None


def test_pages_directory_exists():
    pages = os.path.join(os.path.dirname(__file__), "..", "pages")
    assert os.path.isdir(pages)


def test_all_page_files_are_valid_python():
    pages_dir = os.path.join(os.path.dirname(__file__), "..", "pages")
    page_files = [f for f in os.listdir(pages_dir) if f.endswith(".py")]
    assert len(page_files) > 0, "No page files found"
    for fname in page_files:
        path = os.path.join(pages_dir, fname)
        with open(path, "r", encoding="utf-8") as fh:
            source = fh.read()
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in pages/{fname}: {e}")


def test_utils_modules_are_valid_python():
    utils_dir = os.path.join(os.path.dirname(__file__), "..", "utils")
    py_files = [f for f in os.listdir(utils_dir) if f.endswith(".py")]
    for fname in py_files:
        path = os.path.join(utils_dir, fname)
        with open(path, "r", encoding="utf-8") as fh:
            source = fh.read()
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in utils/{fname}: {e}")
