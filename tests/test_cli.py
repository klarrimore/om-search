"""Tests for CLI argument parsing — flags and dispatch."""

from om_search.cli import build_parser


def test_parser_defaults():
    parser = build_parser()
    args = parser.parse_args([])
    assert args.docs is False
    assert args.cmds is False
    assert args.page is None
    assert args.group is None
    assert args.update is False
    assert args.pages is False
    assert args.groups is False
    assert args.query == []


def test_parser_query_positional():
    parser = build_parser()
    args = parser.parse_args(["screenshot", "region"])
    assert args.query == ["screenshot", "region"]


def test_parser_docs_flag():
    parser = build_parser()
    args = parser.parse_args(["--docs", "volume"])
    assert args.docs is True
    assert args.cmds is False
    assert args.query == ["volume"]


def test_parser_cmds_flag():
    parser = build_parser()
    args = parser.parse_args(["--cmds"])
    assert args.cmds is True
    assert args.docs is False


def test_parser_page_option():
    parser = build_parser()
    args = parser.parse_args(["--page", "04-navigation.md"])
    assert args.page == "04-navigation.md"


def test_parser_group_option():
    parser = build_parser()
    args = parser.parse_args(["--group", "capture"])
    assert args.group == "capture"


def test_parser_update_flag():
    parser = build_parser()
    args = parser.parse_args(["--update"])
    assert args.update is True


def test_parser_pages_flag():
    parser = build_parser()
    args = parser.parse_args(["--pages"])
    assert args.pages is True


def test_parser_groups_flag():
    parser = build_parser()
    args = parser.parse_args(["--groups"])
    assert args.groups is True


def test_parser_pages_with_query():
    parser = build_parser()
    args = parser.parse_args(["--pages", "theme"])
    assert args.pages is True
    assert args.query == ["theme"]


def test_parser_query_and_flag():
    parser = build_parser()
    args = parser.parse_args(["screenshot", "--docs"])
    assert args.query == ["screenshot"]
    assert args.docs is True


def test_parser_flag_after_query():
    parser = build_parser()
    args = parser.parse_args(["screenshot", "--page", "04-navigation.md"])
    assert args.query == ["screenshot"]
    assert args.page == "04-navigation.md"


# --- Dispatch and command-function coverage ---------------------------------

import subprocess
import types
from pathlib import Path

import pytest

from om_search import cli
from om_search.commands import Command
from om_search.index import CmdCandidate, DocCandidate


@pytest.fixture(autouse=True)
def fake_xdg_data(tmp_path, monkeypatch):
    """Isolate every path lookup inside a temp XDG data/config/state home."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    yield


def _ns(**kw):
    return types.SimpleNamespace(**kw)


class TestFindCommands:
    def test_parses_envelope_from_cli(self, monkeypatch):
        raw = (
            '{"ok": true, "commands": ['
            '{"route": "omarchy theme set", "group": "theme", "name": "set",'
            ' "summary": "Apply a theme"}]}'
        )
        monkeypatch.setattr(
            cli.subprocess, "run", lambda *a, **k: _ns(stdout=raw)
        )
        cmds = cli.find_commands()
        assert [c.path for c in cmds] == ["omarchy theme set"]

    def test_degraded_when_cli_absent(self, monkeypatch):
        def boom(*a, **k):
            raise FileNotFoundError("omarchy")

        monkeypatch.setattr(cli.subprocess, "run", boom)
        assert cli.find_commands() == []

    def test_degraded_on_nonzero_exit(self, monkeypatch):
        def boom(*a, **k):
            raise subprocess.CalledProcessError(1, "omarchy")

        monkeypatch.setattr(cli.subprocess, "run", boom)
        assert cli.find_commands() == []


class TestMainDispatch:
    def test_preview_intercepted_before_argparse(self, monkeypatch):
        seen = {}
        monkeypatch.setattr(
            cli, "cmd_preview",
            lambda k1, k2="": seen.update(k1=k1, k2=k2) or 0,
        )
        assert cli.main(["preview", "04-navigation.md", "navigating"]) == 0
        assert seen == {"k1": "04-navigation.md", "k2": "navigating"}

    def test_open_intercepted_before_argparse(self, monkeypatch):
        seen = {}
        monkeypatch.setattr(
            cli, "cmd_open",
            lambda k1, k2="": seen.update(k1=k1, k2=k2) or 0,
        )
        assert cli.main(["open", "04-navigation.md", "navigating"]) == 0
        assert seen == {"k1": "04-navigation.md", "k2": "navigating"}

    def test_completion_prints_and_exits(self, capsys):
        assert cli.main(["--completion"]) == 0
        assert "register-python-argcomplete" in capsys.readouterr().out

    def test_keys_prints_cheatsheet(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "keys_cheatsheet", lambda: "KEYS\n")
        assert cli.main(["--keys"]) == 0
        assert "KEYS" in capsys.readouterr().out

    def test_init_config_writes_and_reports(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "write_default_config", lambda: Path("/tmp/c.toml"))
        assert cli.main(["--init-config"]) == 0
        assert "/tmp/c.toml" in capsys.readouterr().out

    def test_update_dispatches(self, monkeypatch):
        monkeypatch.setattr(cli, "cmd_update", lambda: 7)
        assert cli.main(["--update"]) == 7

    def test_pages_dispatches_with_query(self, monkeypatch):
        got = {}
        monkeypatch.setattr(cli, "cmd_pages", lambda q: got.update(q=q) or 0)
        cli.main(["--pages", "theme"])
        assert got["q"] == "theme"

    def test_groups_dispatches_with_query(self, monkeypatch):
        got = {}
        monkeypatch.setattr(cli, "cmd_groups", lambda q: got.update(q=q) or 0)
        cli.main(["--groups", "capture"])
        assert got["q"] == "capture"

    @pytest.mark.parametrize(
        "argv,expected_mode",
        [
            ([], "all"),
            (["--docs"], "doc"),
            (["--cmds"], "cmd"),
            (["--docs", "--cmds"], "all"),
        ],
    )
    def test_mode_resolution(self, monkeypatch, argv, expected_mode):
        got = {}
        monkeypatch.setattr(
            cli, "cmd_picker",
            lambda **kw: got.update(kw) or 0,
        )
        cli.main(argv)
        assert got["mode"] == expected_mode

    def test_query_and_filters_forwarded_to_picker(self, monkeypatch):
        got = {}
        monkeypatch.setattr(cli, "cmd_picker", lambda **kw: got.update(kw) or 0)
        cli.main(["screen", "shot", "--page", "04.md", "--group", "capture"])
        assert got["query"] == "screen shot"
        assert got["page_filter"] == "04.md"
        assert got["group_filter"] == "capture"

    def test_print_flag_forwarded_to_picker(self, monkeypatch):
        got = {}
        monkeypatch.setattr(cli, "cmd_picker", lambda **kw: got.update(kw) or 0)
        cli.main(["--print", "theme"])
        assert got["plain"] is True

    def test_no_color_flag_sets_env(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setattr(cli, "cmd_picker", lambda **kw: 0)
        cli.main(["--no-color", "x"])
        assert cli.os.environ.get("NO_COLOR") == "1"


class TestCmdUpdate:
    def test_returns_1_when_update_fails(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "update_manual", lambda repo: False)
        assert cli.cmd_update() == 1
        assert "Update failed" in capsys.readouterr().err

    def test_success_rebuilds_index_and_reports(self, monkeypatch, tmp_path, capsys):
        mdir = tmp_path / "manual"
        mdir.mkdir()
        monkeypatch.setattr(cli, "update_manual", lambda repo: True)
        monkeypatch.setattr(cli, "manual_dir", lambda: mdir)
        monkeypatch.setattr(cli, "build_index", lambda *a, **k: None)
        monkeypatch.setattr(cli, "_load_sections", lambda m: ["s1", "s2"])
        monkeypatch.setattr(cli, "find_commands", lambda: [])
        assert cli.cmd_update() == 0
        out = capsys.readouterr().out
        assert "Search index rebuilt." in out
        assert "2 doc sections indexed." in out
        assert "degraded mode" in out

    def test_success_reports_command_count(self, monkeypatch, tmp_path, capsys):
        mdir = tmp_path / "manual"
        mdir.mkdir()
        monkeypatch.setattr(cli, "update_manual", lambda repo: True)
        monkeypatch.setattr(cli, "manual_dir", lambda: mdir)
        monkeypatch.setattr(cli, "build_index", lambda *a, **k: None)
        monkeypatch.setattr(cli, "_load_sections", lambda m: [])
        monkeypatch.setattr(
            cli, "find_commands",
            lambda: [Command(group="x", name="y", path="omarchy x y",
                             description="")],
        )
        cli.cmd_update()
        assert "1 commands indexed." in capsys.readouterr().out


class TestCmdPicker:
    def _stub_env(self, monkeypatch, tmp_path, candidates):
        monkeypatch.setattr(cli, "_ensure_manual", lambda: tmp_path)
        monkeypatch.setattr(cli, "_load_sections", lambda m: [])
        monkeypatch.setattr(cli, "find_commands", lambda: [])
        monkeypatch.setattr(cli, "build_candidates", lambda *a, **k: candidates)
        monkeypatch.setattr(cli, "render_candidate", lambda c: "line")
        # Default to the interactive path; plain-mode tests override this.
        monkeypatch.setattr(cli.sys.stdout, "isatty", lambda: True)

    def test_no_candidates_returns_1(self, monkeypatch, tmp_path, capsys):
        self._stub_env(monkeypatch, tmp_path, [])
        assert cli.cmd_picker() == 1
        assert "No content indexed." in capsys.readouterr().err

    def test_cancel_returns_0(self, monkeypatch, tmp_path):
        self._stub_env(monkeypatch, tmp_path, ["c"])
        monkeypatch.setattr(cli, "run_fzf", lambda *a, **k: None)
        assert cli.cmd_picker() == 0

    def test_command_selection_is_echoed(self, monkeypatch, tmp_path, capsys):
        self._stub_env(monkeypatch, tmp_path, ["c"])
        monkeypatch.setattr(cli, "run_fzf", lambda *a, **k: "sel")
        monkeypatch.setattr(
            cli, "parse_fzf_line",
            lambda s: CmdCandidate(path="omarchy theme set", description="d"),
        )
        assert cli.cmd_picker() == 0
        assert capsys.readouterr().out.strip() == "omarchy theme set"

    def test_command_selection_returns_immediately(self, monkeypatch, tmp_path, capsys):
        # Docs read in-pane, so the picker returns only for a command.
        self._stub_env(monkeypatch, tmp_path, ["c"])
        calls = {"fzf": 0}
        def fake_fzf(*a, **k):
            calls["fzf"] += 1
            return "sel"
        monkeypatch.setattr(cli, "run_fzf", fake_fzf)
        monkeypatch.setattr(
            cli, "parse_fzf_line",
            lambda s: CmdCandidate(path="omarchy theme set", description="d"),
        )
        assert cli.cmd_picker() == 0
        assert capsys.readouterr().out.strip() == "omarchy theme set"
        assert calls["fzf"] == 1  # single call, no browse loop

    def test_doc_line_fallback_opens_pager_once(self, monkeypatch, tmp_path):
        # Docs are normally read in-pane; if a doc line is returned anyway
        # (fallback), the pager opens once and the picker exits (no loop).
        self._stub_env(monkeypatch, tmp_path, ["c"])
        monkeypatch.setattr(cli, "run_fzf", lambda *a, **k: "sel")
        monkeypatch.setattr(
            cli, "parse_fzf_line",
            lambda s: DocCandidate(
                page_file="04.md", anchor="a", page_title="T", heading="Nav"
            ),
        )
        monkeypatch.setattr(cli, "action_for", lambda c: ("view", "BODY"))
        viewed = {}
        monkeypatch.setattr(
            cli, "view_markdown",
            lambda t, jump_to=None: viewed.update(t=t, jump=jump_to),
        )
        assert cli.cmd_picker() == 0
        assert viewed == {"t": "BODY", "jump": "Nav"}

    def test_unparseable_selection_returns_0(self, monkeypatch, tmp_path):
        self._stub_env(monkeypatch, tmp_path, ["c"])
        monkeypatch.setattr(cli, "run_fzf", lambda *a, **k: "garbage")
        monkeypatch.setattr(cli, "parse_fzf_line", lambda s: None)
        assert cli.cmd_picker() == 0

    def test_print_flag_emits_plain_labels(self, monkeypatch, tmp_path, capsys):
        cands = [
            DocCandidate(page_title="Navigation", heading="Grouping windows"),
            CmdCandidate(path="omarchy theme set", description="Apply a theme"),
        ]
        self._stub_env(monkeypatch, tmp_path, cands)
        monkeypatch.setattr(cli.sys.stdout, "isatty", lambda: True)  # flag, not tty
        monkeypatch.setattr(
            cli, "run_fzf",
            lambda *a, **k: pytest.fail("fzf must not run for --print"),
        )
        assert cli.cmd_picker(plain=True) == 0
        out = capsys.readouterr().out
        assert "[doc] Navigation / Grouping windows" in out
        assert "[cmd] omarchy theme set  ::  Apply a theme" in out

    def test_non_tty_degrades_to_plain(self, monkeypatch, tmp_path, capsys):
        cands = [CmdCandidate(path="omarchy x", description="d")]
        self._stub_env(monkeypatch, tmp_path, cands)
        monkeypatch.setattr(cli.sys.stdout, "isatty", lambda: False)
        monkeypatch.setattr(
            cli, "run_fzf",
            lambda *a, **k: pytest.fail("fzf must not run when stdout is not a tty"),
        )
        assert cli.cmd_picker() == 0
        assert "[cmd] omarchy x" in capsys.readouterr().out

    def test_scoped_picker_back_returns_go_back(self, monkeypatch, tmp_path):
        self._stub_env(monkeypatch, tmp_path, ["c"])
        seen = {}
        monkeypatch.setattr(
            cli, "run_fzf",
            lambda *a, **k: seen.update(back=k.get("back")) or cli.BACK,
        )
        assert cli.cmd_picker(page_filter="04.md") == cli.GO_BACK
        assert seen["back"] is True  # back enabled because scoped

    def test_unscoped_picker_does_not_enable_back(self, monkeypatch, tmp_path):
        self._stub_env(monkeypatch, tmp_path, ["c"])
        seen = {}
        monkeypatch.setattr(
            cli, "run_fzf",
            lambda *a, **k: seen.update(back=k.get("back")) or None,
        )
        assert cli.cmd_picker() == 0
        assert seen["back"] is False


class TestCmdPages:
    def test_no_pages_returns_1(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(cli, "_ensure_manual", lambda: tmp_path)
        monkeypatch.setattr(cli, "_list_pages", lambda m: [])
        assert cli.cmd_pages() == 1
        assert "No pages found." in capsys.readouterr().err

    def test_cancel_returns_0(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cli, "_ensure_manual", lambda: tmp_path)
        monkeypatch.setattr(
            cli, "_list_pages",
            lambda m: [{"number": 4, "title": "Navigation", "file": "04-nav.md"}],
        )
        monkeypatch.setattr(cli, "run_simple_fzf", lambda *a, **k: None)
        assert cli.cmd_pages() == 0

    def test_selection_extracts_page_file_and_scopes_picker(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cli, "_ensure_manual", lambda: tmp_path)
        monkeypatch.setattr(
            cli, "_list_pages",
            lambda m: [{"number": 4, "title": "Navigation", "file": "04-nav.md"}],
        )
        monkeypatch.setattr(
            cli, "run_simple_fzf", lambda *a, **k: "04  Navigation  (04-nav.md)"
        )
        got = {}
        monkeypatch.setattr(cli, "cmd_picker", lambda **kw: got.update(kw) or 0)
        cli.cmd_pages()
        assert got["mode"] == "doc"
        assert got["page_filter"] == "04-nav.md"

    def test_back_from_scoped_picker_reshows_page_list(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cli, "_ensure_manual", lambda: tmp_path)
        monkeypatch.setattr(
            cli, "_list_pages",
            lambda m: [{"number": 4, "title": "Navigation", "file": "04-nav.md"}],
        )
        # Pick the page, back out of the scoped picker, then cancel the list.
        fzf = iter(["04  Navigation  (04-nav.md)", None])
        monkeypatch.setattr(cli, "run_simple_fzf", lambda *a, **k: next(fzf))
        calls = {"picker": 0}
        def fake_picker(**kw):
            calls["picker"] += 1
            return cli.GO_BACK
        monkeypatch.setattr(cli, "cmd_picker", fake_picker)
        assert cli.cmd_pages() == 0
        assert calls["picker"] == 1  # entered once, backed out, list reshown


class TestCmdGroups:
    def test_degraded_returns_1(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "find_commands", lambda: [])
        assert cli.cmd_groups() == 1
        assert "degraded mode" in capsys.readouterr().err

    def test_cancel_returns_0(self, monkeypatch):
        monkeypatch.setattr(
            cli, "find_commands",
            lambda: [Command(group="capture", name="screenshot",
                             path="omarchy capture screenshot", description="")],
        )
        monkeypatch.setattr(cli, "run_simple_fzf", lambda *a, **k: None)
        assert cli.cmd_groups() == 0

    def test_selection_strips_prefix_and_scopes_picker(self, monkeypatch):
        monkeypatch.setattr(
            cli, "find_commands",
            lambda: [Command(group="capture", name="screenshot",
                             path="omarchy capture screenshot", description="")],
        )
        monkeypatch.setattr(cli, "run_simple_fzf", lambda *a, **k: "omarchy capture")
        got = {}
        monkeypatch.setattr(cli, "cmd_picker", lambda **kw: got.update(kw) or 0)
        cli.cmd_groups()
        assert got["mode"] == "cmd"
        assert got["group_filter"] == "capture"


class TestRenderText:
    @pytest.fixture(autouse=True)
    def _force_color(self, monkeypatch):
        # These exercise the colour renderers; keep them on regardless of the
        # ambient NO_COLOR/TERM the test runner may carry.
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "xterm-256color")

    def test_prefers_mdcat(self, monkeypatch, capsys):
        monkeypatch.setattr(cli.shutil, "which",
                            lambda n: "/usr/bin/mdcat" if n == "mdcat" else None)
        calls = {}
        monkeypatch.setattr(
            cli.subprocess, "run",
            lambda cmd, **k: calls.update(cmd=cmd) or _ns(stdout="MD"),
        )
        cli._render_text("# hi")
        assert calls["cmd"][0] == "mdcat"
        assert "MD" in capsys.readouterr().out

    def test_falls_back_to_bat(self, monkeypatch, capsys):
        monkeypatch.setattr(cli.shutil, "which",
                            lambda n: "/usr/bin/bat" if n == "bat" else None)
        monkeypatch.setattr(
            cli.subprocess, "run", lambda cmd, **k: _ns(stdout="BAT")
        )
        cli._render_text("# hi")
        assert "BAT" in capsys.readouterr().out

    def test_plain_when_no_renderer(self, monkeypatch, capsys):
        monkeypatch.setattr(cli.shutil, "which", lambda n: None)
        cli._render_text("plain text")
        assert "plain text" in capsys.readouterr().out

    def test_no_color_emits_plain_no_subprocess(self, monkeypatch, capsys):
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.setattr(
            cli.subprocess, "run",
            lambda *a, **k: pytest.fail("no renderer subprocess under NO_COLOR"),
        )
        cli._render_text("# hi\n\nbody")
        assert capsys.readouterr().out == "# hi\n\nbody\n"


class TestCmdPreview:
    def test_command_echo_branch(self, monkeypatch, capsys):
        # A command path is not a file: echo path and description.
        assert cli.cmd_preview("omarchy theme set", "Apply a theme") == 0
        out = capsys.readouterr().out
        assert "omarchy theme set" in out
        assert "Apply a theme" in out

    def test_disk_fallback_reads_manual_file(self, monkeypatch, tmp_path, capsys):
        mdir = tmp_path / "manual"
        mdir.mkdir()
        (mdir / "04-nav.md").write_text("# Navigation\n\nbody text\n", encoding="utf-8")
        monkeypatch.setattr(cli, "manual_dir", lambda: mdir)
        monkeypatch.setattr(cli.shutil, "which", lambda n: None)  # plain render
        assert cli.cmd_preview("04-nav.md") == 0
        assert "body text" in capsys.readouterr().out

    def test_index_hit_renders_section_text(self, monkeypatch):
        sec = _ns(page_file="04.md", anchor="nav", text="SECTION BODY")
        monkeypatch.setattr(cli, "load_index", lambda p: ([sec], {}))
        rendered = {}
        monkeypatch.setattr(cli, "_render_text", lambda t: rendered.update(t=t))
        assert cli.cmd_preview("04.md", "nav") == 0
        assert rendered["t"] == "SECTION BODY"

    def test_index_hit_falls_back_to_page_text(self, monkeypatch):
        # No matching anchor -> use whole-page text from the index.
        monkeypatch.setattr(cli, "load_index", lambda p: ([], {"04.md": "PAGE"}))
        rendered = {}
        monkeypatch.setattr(cli, "_render_text", lambda t: rendered.update(t=t))
        assert cli.cmd_preview("04.md", "missing-anchor") == 0
        assert rendered["t"] == "PAGE"

    def test_preview_file_fast_path_skips_index(self, monkeypatch):
        from om_search.index import preview_key
        from om_search.paths import preview_dir
        (preview_dir() / preview_key("04.md", "nav")).write_text(
            "FAST SECTION", encoding="utf-8"
        )
        rendered = {}
        monkeypatch.setattr(cli, "_render_text", lambda t: rendered.update(t=t))
        monkeypatch.setattr(
            cli, "load_index",
            lambda p: pytest.fail("fast path must not parse the index"),
        )
        assert cli.cmd_preview("04.md", "nav") == 0
        assert rendered["t"] == "FAST SECTION"


class TestCmdOpen:
    def test_opens_full_page_at_resolved_heading(self, monkeypatch):
        sec = _ns(page_file="04.md", anchor="nav", heading="Navigating")
        monkeypatch.setattr(cli, "load_index", lambda p: ([sec], {}))
        monkeypatch.setattr(cli, "page_text", lambda cand: "FULLPAGE")
        seen = {}
        monkeypatch.setattr(
            cli, "view_markdown",
            lambda t, jump_to=None: seen.update(t=t, jump=jump_to),
        )
        assert cli.cmd_open("04.md", "nav") == 0
        assert seen == {"t": "FULLPAGE", "jump": "Navigating"}

    def test_no_anchor_opens_page_top(self, monkeypatch):
        monkeypatch.setattr(cli, "load_index", lambda p: ([], {}))
        monkeypatch.setattr(cli, "page_text", lambda cand: "FULLPAGE")
        seen = {}
        monkeypatch.setattr(
            cli, "view_markdown",
            lambda t, jump_to=None: seen.update(t=t, jump=jump_to),
        )
        assert cli.cmd_open("04.md") == 0
        assert seen == {"t": "FULLPAGE", "jump": None}


class TestCmdLinks:
    def test_no_links_returns_0(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "page_text", lambda cand: "no links here")
        assert cli.cmd_links("04.md") == 0
        assert "No links" in capsys.readouterr().err

    def test_selection_navigates_to_target_page(self, monkeypatch):
        monkeypatch.setattr(
            cli, "page_text",
            lambda cand: "see [nav](04-navigation.md) and [top](05-the-top-bar.md)",
        )
        monkeypatch.setattr(
            cli, "run_simple_fzf",
            lambda items, **k: next(i for i in items if "05-the-top-bar" in i),
        )
        got = {}
        monkeypatch.setattr(cli, "cmd_picker", lambda **kw: got.update(kw) or 0)
        assert cli.cmd_links("03.md") == 0
        assert got["mode"] == "doc"
        assert got["page_filter"] == "05-the-top-bar.md"

    def test_anchor_prefilters_query(self, monkeypatch):
        monkeypatch.setattr(
            cli, "page_text",
            lambda cand: "jump [g](04-navigation.md#grouping-windows)",
        )
        monkeypatch.setattr(cli, "run_simple_fzf", lambda items, **k: items[0])
        got = {}
        monkeypatch.setattr(cli, "cmd_picker", lambda **kw: got.update(kw) or 0)
        cli.cmd_links("03.md")
        assert got["page_filter"] == "04-navigation.md"
        assert got["query"] == "grouping windows"

    def test_back_from_target_reshows_link_list(self, monkeypatch):
        monkeypatch.setattr(
            cli, "page_text", lambda cand: "[nav](04-navigation.md)"
        )
        seq = iter([lambda items: items[0], lambda items: None])
        monkeypatch.setattr(
            cli, "run_simple_fzf", lambda items, **k: next(seq)(items)
        )
        calls = {"picker": 0}
        def fake_picker(**kw):
            calls["picker"] += 1
            return cli.GO_BACK
        monkeypatch.setattr(cli, "cmd_picker", fake_picker)
        assert cli.cmd_links("03.md") == 0
        assert calls["picker"] == 1  # entered target once, backed out, list reshown

    def test_links_intercepted_in_main(self, monkeypatch):
        seen = {}
        monkeypatch.setattr(cli, "cmd_links", lambda p: seen.update(p=p) or 0)
        assert cli.main(["links", "03-coming-from-mac-or-windows.md"]) == 0
        assert seen == {"p": "03-coming-from-mac-or-windows.md"}


class TestLoadSectionsAndListPages:
    def test_load_sections_uses_index_when_present(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cli, "load_index", lambda p: (["S"], {}))
        assert cli._load_sections(tmp_path) == ["S"]

    def test_load_sections_disk_fallback(self, monkeypatch, tmp_path):
        (tmp_path / "01-intro.md").write_text(
            "# Intro\n\nhello\n", encoding="utf-8"
        )
        monkeypatch.setattr(cli, "load_index", lambda p: None)
        sections = cli._load_sections(tmp_path)
        assert sections and sections[0].page_file == "01-intro.md"

    def test_list_pages_dedupes_from_index(self, monkeypatch, tmp_path):
        s = _ns(page_file="04.md", page_number=4, page_title="Nav")
        s2 = _ns(page_file="04.md", page_number=4, page_title="Nav")
        monkeypatch.setattr(cli, "load_index", lambda p: ([s, s2], {}))
        pages = cli._list_pages(tmp_path)
        assert pages == [{"number": 4, "title": "Nav", "file": "04.md"}]


class TestEnsureManual:
    def test_exits_when_manual_missing(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(cli, "ensure_manual", lambda repo: None)
        monkeypatch.setattr(cli, "manual_dir", lambda: tmp_path / "absent")
        with pytest.raises(SystemExit) as exc:
            cli._ensure_manual()
        assert exc.value.code == 1
        assert "Manual not found" in capsys.readouterr().err

    def test_returns_manual_dir_when_present(self, monkeypatch, tmp_path):
        mdir = tmp_path / "manual"
        mdir.mkdir()
        monkeypatch.setattr(cli, "ensure_manual", lambda repo: None)
        monkeypatch.setattr(cli, "manual_dir", lambda: mdir)
        assert cli._ensure_manual() == mdir


class TestCmdUpdateNoManual:
    def test_reports_when_manual_dir_absent(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(cli, "update_manual", lambda repo: True)
        monkeypatch.setattr(cli, "manual_dir", lambda: tmp_path / "absent")
        monkeypatch.setattr(cli, "find_commands", lambda: [])
        assert cli.cmd_update() == 0
        assert "No manual directory found" in capsys.readouterr().err