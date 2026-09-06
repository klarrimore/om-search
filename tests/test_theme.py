"""Tests for Omarchy theme -> fzf colour translation."""

from om_search import theme
from om_search.theme import (
    CATPPUCCIN_MOCHA,
    fzf_color_spec,
    load_palette,
    resolve_palette,
)

PALETTE_TOML = """\
mode = "dark"
accent = "#7aa2f7"
selection = "#292e42"
muted = "#414868"
background = "#1a1b26"
dark_background = "#13141c"
foreground = "#a9b1d6"
bright_foreground = "#c0caf5"
red = "#f7768e"
green = "#9ece6a"

[theme.custom]
ignored = "table entry not a scalar"
"""


def _write_theme(tmp_path):
    (tmp_path / "colors.toml").write_text(PALETTE_TOML)
    return tmp_path


class TestLoadPalette:
    def test_reads_scalar_tokens(self, tmp_path):
        pal = load_palette(_write_theme(tmp_path))
        assert pal is not None
        assert pal["background"] == "#1a1b26"
        assert pal["accent"] == "#7aa2f7"
        # Nested tables are not scalars and must be dropped
        assert "theme" not in pal

    def test_missing_returns_none(self, tmp_path):
        assert load_palette(tmp_path / "nope") is None


class TestResolvePalette:
    def test_none_source(self):
        assert resolve_palette("none") is None

    def test_catppuccin_source(self):
        pal = resolve_palette("catppuccin")
        assert pal is not None
        assert pal["background"] == CATPPUCCIN_MOCHA["background"]

    def test_omarchy_source_uses_active_theme(self, tmp_path, monkeypatch):
        monkeypatch.setattr(theme, "load_palette", lambda: {"background": "#000000"})
        pal = resolve_palette("omarchy")
        assert pal == {"background": "#000000"}

    def test_omarchy_falls_back_when_no_theme(self, monkeypatch):
        monkeypatch.setattr(theme, "load_palette", lambda: None)
        pal = resolve_palette("omarchy")
        assert pal is not None
        assert pal["background"] == CATPPUCCIN_MOCHA["background"]

    def test_custom_overrides_win(self, monkeypatch):
        monkeypatch.setattr(theme, "load_palette", lambda: {"background": "#000000"})
        pal = resolve_palette("omarchy", {"background": "#ffffff"})
        assert pal["background"] == "#ffffff"


class TestFzfColorSpec:
    def test_maps_tokens_to_fzf_roles(self, tmp_path):
        pal = load_palette(_write_theme(tmp_path))
        spec = fzf_color_spec(pal)
        assert "bg:#1a1b26" in spec
        assert "fg:#a9b1d6" in spec
        assert "prompt:#7aa2f7" in spec       # from accent
        assert "pointer:#f7768e" in spec      # from red
        assert "preview-bg:#13141c" in spec   # from dark_background

    def test_partial_palette_skips_missing(self):
        spec = fzf_color_spec({"background": "#123456"})
        assert "bg:#123456" in spec
        # No foreground token -> no fg role emitted
        assert "fg:#" not in spec
