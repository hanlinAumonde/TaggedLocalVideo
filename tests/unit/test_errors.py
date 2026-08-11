"""Unit tests for custom error classes."""

import pytest

from src.errors import InvalidPathError, _MigrationCancelled

pytestmark = pytest.mark.unit


def test_invalid_path_error_stores_path():
    err = InvalidPathError("/bad/path")
    assert err.path == "/bad/path"
    assert "Invalid path: /bad/path" in str(err)


def test_migration_cancelled_is_exception():
    err = _MigrationCancelled()
    assert isinstance(err, Exception)
