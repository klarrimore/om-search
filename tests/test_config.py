"""Tests for om-search TOML configuration (theme + keybindings)."""

from om_search.config import DEFAULT_KEYS, load_config, write_default_config


class TestLoadConfig:
    def test_defaults_when_missing(self, tmp_path):
        cfg = load_config(tmp_path / "nope.toml")
        assert cfg.theme_source == "omarchy"
        assert cfg.keys == DEFAULT_KEYS
        assert cfg.theme_custom == {}

    def test_user_overrides_theme_and_keys(self, tmp_path):
        p = tmp_path / "config.toml"
        p.write_text(
            '[theme]\n'
            'source = "catppuccin"\n'
            '[theme.custom]\n'
            'accent = "#f5c2e7"\n'
            '[keys]\n'
            'down = "ctrl-n"\n'
            'up = "ctrl-p"\n'
        )
        cfg = load_config(p)
        assert cfg.theme_source == "catppuccin"
        assert cfg.theme_custom == {"accent": "#f5c2e7"}
        assert cfg.keys["down"] == "ctrl-n"
        assert cfg.keys["up"] == "ctrl-p"
        # untouched keys keep defaults
        assert cfg.keys["copy"] == DEFAULT_KEYS["copy"]

    def test_invalid_theme_source_ignored(self, tmp_path):
        p = tmp_path / "config.toml"
        p.write_text('[theme]\nsource = "bogus"\n')
        assert load_config(p).theme_source == "omarchy"

    def test_empty_key_unbinds(self, tmp_path):
        p = tmp_path / "config.toml"
        p.write_text('[keys]\ncopy = ""\n')
        cfg = load_config(p)
        assert cfg.keys["copy"] == ""
        assert "ctrl-y:execute-silent" not in "".join(cfg.movement_binds())

    def test_malformed_toml_falls_back(self, tmp_path):
        p = tmp_path / "config.toml"
        p.write_text("this is = = not valid toml [[[")
        cfg = load_config(p)
        assert cfg.theme_source == "omarchy"


class TestMovementBinds:
    def test_builds_key_action_pairs(self, tmp_path):
        cfg = load_config(tmp_path / "nope.toml")
        binds = cfg.movement_binds()
        assert "ctrl-j:down" in binds
        assert "ctrl-k:up" in binds
        assert "ctrl-d:half-page-down" in binds
        assert "ctrl-f:preview-half-page-down" in binds


class TestWriteDefaultConfig:
    def test_writes_when_missing(self, tmp_path):
        p = tmp_path / "config.toml"
        write_default_config(p)
        assert p.exists()
        assert "[theme]" in p.read_text()
        assert "[keys]" in p.read_text()

    def test_does_not_overwrite_existing(self, tmp_path):
        p = tmp_path / "config.toml"
        p.write_text("# mine\n")
        write_default_config(p)
        assert p.read_text() == "# mine\n"
