"""Tests for XDG path resolution."""

from pathlib import Path

from om_search.paths import (
    active_theme_dir,
    config_dir,
    config_path,
    data_dir,
    manual_dir,
    repo_dir,
)


class TestDataDir:
    def test_honours_xdg_data_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        d = data_dir()
        assert d == tmp_path / "om-search"

    def test_creates_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        assert data_dir().is_dir()

    def test_falls_back_to_home_local_share(self, tmp_path, monkeypatch):
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        monkeypatch.setenv("HOME", str(tmp_path))
        d = data_dir()
        assert d == tmp_path / ".local" / "share" / "om-search"


class TestRepoAndManualDir:
    def test_repo_dir_nested_under_data(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        assert repo_dir() == tmp_path / "om-search" / "omarchy-repo"

    def test_manual_dir_nested_under_repo(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        assert manual_dir() == tmp_path / "om-search" / "omarchy-repo" / "manual"


class TestConfigDir:
    def test_honours_xdg_config_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        assert config_dir() == tmp_path / "om-search"

    def test_config_path_is_toml_under_config_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        assert config_path() == tmp_path / "om-search" / "config.toml"

    def test_config_dir_not_created(self, tmp_path, monkeypatch):
        # Unlike data_dir, config_dir must not create the directory.
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "nope"))
        d = config_dir()
        assert not d.exists()


class TestActiveThemeDir:
    def test_honours_xdg_state_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        assert active_theme_dir() == tmp_path / "omarchy" / "current" / "theme"
