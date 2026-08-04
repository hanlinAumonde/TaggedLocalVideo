"""Unit tests for config.py utility methods."""

import pytest

from src import config
from src.config import Settings, get_settings


class TestSettingsUtilities:
    def test_get_all_host_paths(self, test_settings: Settings):
        paths = test_settings.get_all_host_paths()
        assert isinstance(paths, set)
        assert "/test/videos" in paths

    def test_get_host_path(self, test_settings: Settings):
        result = test_settings.get_host_path("Test-category", "Test-resource")
        assert result == "/test/videos"

    def test_find_category_by_host_path_exact(self, test_settings: Settings):
        assert test_settings.find_category_by_host_path("/test/videos") == "Test-category"

    def test_find_category_by_host_path_subpath(self, test_settings: Settings):
        assert test_settings.find_category_by_host_path("/test/videos/sub/file.mp4") == "Test-category"

    def test_find_category_by_host_path_no_match(self, test_settings: Settings):
        assert test_settings.find_category_by_host_path("/unrelated/path") is None

    def test_get_settings_not_initialized(self, monkeypatch):
        monkeypatch.setattr(config, "_settings", None)
        with pytest.raises(RuntimeError, match="Settings have not been initialized"):
            get_settings()
