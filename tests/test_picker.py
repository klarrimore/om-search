"""Tests for fzf integration — preview, section reading, and actions."""

import json
import types

import pytest

import om_search.picker as picker
from om_search.config import Config
from om_search.index import DocCandidate, CmdCandidate, build_index, INDEX_FILENAME
from om_search.picker import action_for, section_text, picker_header, run_fzf
from om_search.paths import data_dir


# Fixture: a minimal manual dir in a temp XDG_DATA_HOME
FIXTURE_FILE = "04-navigation.md"
FIXTURE_CONTENT = """# Navigation

Omarchy intro.

## Navigating

Super + Space opens the Omarchy menu.

## Workspaces

You can switch between workspaces with Super + 1-4.
"""


@pytest.fixture(autouse=True)
def fake_xdg_data(tmp_path, monkeypatch):
    xdg = tmp_path / "xdg-data"
    xdg.mkdir()
    mdir = xdg / "om-search" / "omarchy-repo" / "manual"
    mdir.mkdir(parents=True)
    (mdir / FIXTURE_FILE).write_text(FIXTURE_CONTENT)
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg))
    yield


class TestPickerHeader:
    def test_all_mode(self):
        h = picker_header(mode="all")
        assert "all sources" in h
        assert "Enter: read" in h
        assert "Ctrl+O: full" in h
        assert "Ctrl+L: links" in h

    def test_doc_mode(self):
        h = picker_header(mode="doc")
        assert "docs only" in h

    def test_cmd_mode(self):
        h = picker_header(mode="cmd")
        assert "commands only" in h

    def test_with_page_filter(self):
        h = picker_header(mode="all", page_filter="04-navigation.md")
        assert "page: 04-navigation.md" in h
        assert "all sources" in h

    def test_with_group_filter(self):
        h = picker_header(mode="cmd", group_filter="capture")
        assert "group: capture" in h
        assert "commands only" in h


class TestSectionText:
    def test_returns_matching_section(self):
        cand = DocCandidate(
            page_file=FIXTURE_FILE, anchor="navigating",
            page_title="Navigation", heading="Navigating",
        )
        text = section_text(cand)
        assert "Super + Space" in text
        assert "intro" not in text  # intro section, not this one

    def test_returns_intro_when_no_heading(self):
        cand = DocCandidate(
            page_file=FIXTURE_FILE, anchor="",
            page_title="Navigation", heading="",
        )
        text = section_text(cand)
        assert "Omarchy intro" in text

    def test_empty_when_file_missing(self):
        cand = DocCandidate(
            page_file="nonexistent.md", anchor="",
            page_title="", heading="",
        )
        assert section_text(cand) == ""

    def test_reads_from_index_when_present(self):
        """When index.json exists it wins over on-disk parsing."""
        mdir = data_dir() / "omarchy-repo" / "manual"
        # Write a slightly different body into the index to prove it is read
        (mdir / FIXTURE_FILE).write_text(FIXTURE_CONTENT.replace(
            "Super + Space opens the Omarchy menu.",
            "Super + Space opens the INDEXED menu."
        ))
        build_index(mdir, data_dir() / INDEX_FILENAME)

        cand = DocCandidate(
            page_file=FIXTURE_FILE, anchor="navigating",
            page_title="Navigation", heading="Navigating",
        )
        text = section_text(cand)
        assert "INDEXED menu" in text
        assert "intro" not in text


class TestRunFzf:
    @staticmethod
    def _capture(monkeypatch, **kwargs):
        captured = {}

        def fake_run(cmd, **_):
            captured["cmd"] = cmd
            return types.SimpleNamespace(stdout="")

        monkeypatch.setattr("om_search.picker.subprocess.run", fake_run)
        # theme_source="none" keeps the test off the real filesystem palette
        cfg = Config(theme_source="none")
        run_fzf(["doc\ta.md\tanchor\t[doc] Title\tbody words here"], cfg=cfg, **kwargs)
        return captured["cmd"]

    def test_search_scope_includes_body_excerpt_field(self, monkeypatch):
        """Regression: fzf must search field 5 (body excerpt), not just the
        display field, or doc bodies become undiscoverable."""
        cmd = self._capture(monkeypatch)
        assert "--with-nth" in cmd
        assert cmd[cmd.index("--with-nth") + 1] == "4,5"

    def test_is_bordered_and_reverse_layout(self, monkeypatch):
        cmd = self._capture(monkeypatch)
        assert "--border=rounded" in cmd
        assert "--layout=reverse" in cmd

    def test_movement_and_help_binds_from_config(self, monkeypatch):
        cmd = self._capture(monkeypatch)
        binds = [cmd[i + 1] for i, a in enumerate(cmd) if a == "--bind"]
        assert "ctrl-j:down" in binds
        assert "ctrl-k:up" in binds
        assert any(b.startswith("?:change-preview") for b in binds)
        assert any(b.startswith("ctrl-y:") for b in binds)

    def test_no_expect_left_when_back_disabled(self, monkeypatch):
        cmd = self._capture(monkeypatch)
        assert "--expect" not in cmd

    def test_enter_opens_reading_mode_for_docs(self, monkeypatch):
        cmd = self._capture(monkeypatch)
        binds = [cmd[i + 1] for i, a in enumerate(cmd) if a == "--bind"]
        enter = [b for b in binds if b.startswith("enter:")]
        assert enter, "enter must be bound"
        assert "doc" in enter[0]                    # doc -> reading mode
        assert "change-preview-window" in enter[0]  # enlarge the pane
        assert "accept" in enter[0]                 # command -> accept

    def test_ctrl_o_opens_full_pager_for_docs(self, monkeypatch):
        cmd = self._capture(monkeypatch)
        binds = [cmd[i + 1] for i, a in enumerate(cmd) if a == "--bind"]
        assert any(b.startswith("ctrl-o:") and "om-search open" in b for b in binds)

    def test_ctrl_l_follows_links_for_docs(self, monkeypatch):
        cmd = self._capture(monkeypatch)
        binds = [cmd[i + 1] for i, a in enumerate(cmd) if a == "--bind"]
        assert any(b.startswith("ctrl-l:") and "om-search links" in b for b in binds)

    def test_movement_is_modal_while_reading(self, monkeypatch):
        cmd = self._capture(monkeypatch)
        binds = [cmd[i + 1] for i, a in enumerate(cmd) if a == "--bind"]
        cj = [b for b in binds if b.startswith("ctrl-j:transform")]
        assert cj, "ctrl-j must be modal"
        assert "preview-down" in cj[0] and "reading" in cj[0]


class TestRunFzfBack:
    """Scoped pickers let Left/Esc pop back to the parent list."""

    @staticmethod
    def _run(monkeypatch, stdout, returncode=0):
        captured = {}

        def fake_run(cmd, **_):
            captured["cmd"] = cmd
            return types.SimpleNamespace(stdout=stdout, returncode=returncode)

        monkeypatch.setattr("om_search.picker.subprocess.run", fake_run)
        cfg = Config(theme_source="none")
        result = run_fzf(["d\ta.md\tanc\t[doc] T\tbody"], cfg=cfg, back=True)
        return captured["cmd"], result

    def test_binds_left_via_expect(self, monkeypatch):
        cmd, _ = self._run(monkeypatch, "\nsel")
        assert cmd[cmd.index("--expect") + 1] == "left"

    def test_left_key_returns_back_sentinel(self, monkeypatch):
        _, result = self._run(monkeypatch, "left\n[doc] T")
        assert result is picker.BACK

    def test_esc_returns_back_sentinel(self, monkeypatch):
        _, result = self._run(monkeypatch, "", returncode=130)
        assert result is picker.BACK

    def test_enter_still_returns_selection(self, monkeypatch):
        _, result = self._run(monkeypatch, "\n[doc]\tT\tanchor")
        assert result == "[doc]\tT\tanchor"


class TestAction:
    def test_action_returns_view_and_text_for_doc(self):
        cand = DocCandidate(
            page_file=FIXTURE_FILE, anchor="navigating",
            page_title="Navigation", heading="Navigating",
        )
        kind, text = action_for(cand)
        assert kind == "view"
        assert "Super + Space" in text

    def test_action_echoes_command_for_cmd(self):
        cand = CmdCandidate(
            path="omarchy capture screenshot",
            description="Take a screenshot",
        )
        kind, text = action_for(cand)
        assert kind == "echo"
        assert text == "omarchy capture screenshot"


class TestRenderMarkdown:
    @pytest.fixture(autouse=True)
    def _force_color(self, monkeypatch):
        # Exercise the colour renderer chain regardless of the runner's env.
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "xterm-256color")

    def test_returns_raw_text_when_no_renderer(self, monkeypatch):
        """With no renderer on PATH, the text passes through unchanged."""
        monkeypatch.setattr(picker.shutil, "which", lambda _: None)
        assert picker.render_markdown("# Hi\n\nbody") == "# Hi\n\nbody"

    def test_prefers_glow_and_returns_its_output(self, monkeypatch):
        monkeypatch.setattr(picker.shutil, "which",
                            lambda name: "/usr/bin/glow" if name == "glow" else None)
        calls = {}

        def fake_run(cmd, **kwargs):
            calls["cmd"] = cmd
            return types.SimpleNamespace(returncode=0, stdout="RENDERED")

        monkeypatch.setattr(picker.subprocess, "run", fake_run)
        out = picker.render_markdown("# Hi")
        assert out == "RENDERED"
        assert calls["cmd"][0] == "glow"

    def test_view_markdown_writes_when_not_a_tty(self, monkeypatch, capsys):
        """No TTY -> render straight to stdout instead of paging."""
        monkeypatch.setattr(picker.shutil, "which", lambda _: None)
        monkeypatch.setattr(picker.sys.stdout, "isatty", lambda: False)
        picker.view_markdown("plain body")
        assert "plain body" in capsys.readouterr().out


class TestRunSimpleFzf:
    @staticmethod
    def _capture(monkeypatch, stdout="", **kwargs):
        captured = {}

        def fake_run(cmd, **_):
            captured["cmd"] = cmd
            return types.SimpleNamespace(stdout=stdout)

        monkeypatch.setattr("om_search.picker.subprocess.run", fake_run)
        cfg = Config(theme_source="none")
        result = picker.run_simple_fzf(
            ["omarchy theme", "omarchy capture"], cfg=cfg, **kwargs
        )
        return captured["cmd"], result

    def test_returns_none_on_cancel(self, monkeypatch):
        _, result = self._capture(monkeypatch, stdout="")
        assert result is None

    def test_returns_selected_line(self, monkeypatch):
        _, result = self._capture(monkeypatch, stdout="omarchy capture\n")
        assert result == "omarchy capture"

    def test_is_themed_and_bordered(self, monkeypatch):
        cmd, _ = self._capture(monkeypatch)
        assert cmd[0] == "fzf"
        assert "--border=rounded" in cmd

    def test_forwards_header_and_query(self, monkeypatch):
        cmd, _ = self._capture(monkeypatch, header="Pick one", query="cap")
        assert cmd[cmd.index("--header") + 1] == "Pick one"
        assert cmd[cmd.index("--query") + 1] == "cap"


class TestKeysCheatsheet:
    def test_lists_configured_chords(self):
        sheet = picker.keys_cheatsheet(Config())
        assert "Ctrl + J" in sheet
        assert "Ctrl + K" in sheet


class TestViewMarkdownPager:
    def test_pages_through_less_when_tty(self, monkeypatch):
        monkeypatch.setattr(picker.shutil, "which",
                            lambda n: "/usr/bin/less" if n == "less" else None)
        monkeypatch.setattr(picker.sys.stdout, "isatty", lambda: True)
        calls = {}
        monkeypatch.setattr(
            picker.subprocess, "run",
            lambda cmd, **k: calls.update(cmd=cmd, input=k.get("input")),
        )
        picker.view_markdown("# body")
        assert calls["cmd"][0] == "less"


class TestPageText:
    def test_returns_whole_page_not_just_section(self):
        cand = DocCandidate(
            page_file=FIXTURE_FILE, anchor="workspaces",
            page_title="Navigation", heading="Workspaces",
        )
        text = picker.page_text(cand)
        # Whole page: both the intro and every section are present.
        assert "Omarchy intro" in text
        assert "Super + Space" in text
        assert "switch between workspaces" in text

    def test_empty_when_file_missing(self):
        cand = DocCandidate(
            page_file="nope.md", anchor="", page_title="", heading="",
        )
        assert picker.page_text(cand) == ""


class TestHeadingLine:
    def test_finds_heading_line_ignoring_ansi(self):
        rendered = "intro line\n\x1b[1m## \x1b[0m\x1b[1mWorkspaces\x1b[0m\nbody\n"
        assert picker.heading_line(rendered, "Workspaces") == 2

    def test_prefers_hashed_heading_over_body_mention(self):
        rendered = "we discuss Workspaces here\n### Workspaces\nbody\n"
        assert picker.heading_line(rendered, "Workspaces") == 2

    def test_returns_zero_when_absent(self):
        assert picker.heading_line("nothing here\n", "Missing") == 0

    def test_returns_zero_for_empty_heading(self):
        assert picker.heading_line("## X\n", "") == 0


class TestViewMarkdownJump:
    def test_opens_pager_at_heading_line(self, monkeypatch):
        monkeypatch.setattr(picker.shutil, "which",
                            lambda n: "/usr/bin/less" if n == "less" else None)
        monkeypatch.setattr(picker.sys.stdout, "isatty", lambda: True)
        # no markdown renderer -> rendered text is the raw input, lines intact
        monkeypatch.setattr(picker, "render_markdown", lambda t: t)
        calls = {}
        monkeypatch.setattr(
            picker.subprocess, "run",
            lambda cmd, **k: calls.update(cmd=cmd),
        )
        picker.view_markdown("# Title\n\n## First\n\na\n\n## Second\n\nb\n",
                             jump_to="Second")
        assert calls["cmd"][0] == "less"
        assert "+7" in calls["cmd"]  # positioned at the "## Second" line

    def test_no_jump_arg_when_heading_absent(self, monkeypatch):
        monkeypatch.setattr(picker.shutil, "which",
                            lambda n: "/usr/bin/less" if n == "less" else None)
        monkeypatch.setattr(picker.sys.stdout, "isatty", lambda: True)
        monkeypatch.setattr(picker, "render_markdown", lambda t: t)
        calls = {}
        monkeypatch.setattr(
            picker.subprocess, "run", lambda cmd, **k: calls.update(cmd=cmd),
        )
        picker.view_markdown("just text\n", jump_to="Nope")
        assert not any(a.startswith("+") for a in calls["cmd"])  # no jump arg
        assert calls["cmd"][:2] == ["less", "-R"]

    def test_esc_binds_to_back_via_lesskey(self, monkeypatch):
        """Esc must act as 'back': less is launched with a LESSKEYIN file that
        binds Esc to quit, so the picker loop resumes."""
        monkeypatch.setattr(picker.shutil, "which",
                            lambda n: "/usr/bin/less" if n == "less" else None)
        monkeypatch.setattr(picker.sys.stdout, "isatty", lambda: True)
        monkeypatch.setattr(picker, "render_markdown", lambda t: t)
        calls = {}
        monkeypatch.setattr(
            picker.subprocess, "run",
            lambda cmd, **k: calls.update(cmd=cmd, env=k.get("env")),
        )
        picker.view_markdown("body\n")
        env = calls["env"]
        assert env is not None and "LESSKEYIN" in env
        from pathlib import Path
        assert "quit" in Path(env["LESSKEYIN"]).read_text(encoding="utf-8")
        # prompt advertises the back key
        assert any("back" in a for a in calls["cmd"])


class TestColorDegradation:
    def test_fzf_uses_bw_under_no_color(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        args = picker._base_fzf_args(Config(theme_source="omarchy"))
        assert args[args.index("--color") + 1] == "bw"
        # No palette hex color spec is emitted.
        assert not any("#" in a for a in args)

    def test_fzf_uses_palette_when_color_enabled(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "xterm-256color")
        args = picker._base_fzf_args(Config(theme_source="catppuccin"))
        spec = args[args.index("--color") + 1]
        assert "#" in spec and spec != "bw"

    def test_render_markdown_plain_under_no_color(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        # No glow available -> raw text, and never ANSI.
        monkeypatch.setattr(picker.shutil, "which", lambda _: None)
        out = picker.render_markdown("# Hi\n\nbody")
        assert out == "# Hi\n\nbody"
        assert "\x1b[" not in out

    def test_render_markdown_uses_glow_notty_under_no_color(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.setattr(picker.shutil, "which",
                            lambda n: "/usr/bin/glow" if n == "glow" else None)
        calls = {}
        monkeypatch.setattr(
            picker.subprocess, "run",
            lambda cmd, **k: calls.update(cmd=cmd) or types.SimpleNamespace(
                returncode=0, stdout="PLAIN LAYOUT"),
        )
        out = picker.render_markdown("# Hi")
        assert out == "PLAIN LAYOUT"
        # notty style = no ANSI colour, layout preserved
        assert calls["cmd"] == ["glow", "-s", "notty", "-"]