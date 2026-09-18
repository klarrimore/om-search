"""CLI entry-route and private navigation endpoint contracts."""

from __future__ import annotations

import types

import pytest

from om_search import cli
from om_search.commands import Command
from om_search.index import CmdCandidate, DocCandidate
from om_search.manual import Section
from om_search.picker import _load_manifest, build_navigation_dataset, navigation_rows


def test_parser_defaults_and_query():
    args = cli.build_parser().parse_args([])
    assert args.query == []
    args = cli.build_parser().parse_args(["screenshot", "region", "--docs"])
    assert args.query == ["screenshot", "region"]
    assert args.docs is True


def test_private_nav_data_dispatches_before_argparse(monkeypatch):
    seen = {}
    monkeypatch.setattr(cli, "cmd_nav_data", lambda path, route: seen.update(path=path, route=route) or 0)
    assert cli.main(["nav-data", "/tmp/dataset", "12"]) == 0
    assert seen == {"path": "/tmp/dataset", "route": "12"}


def test_private_nav_transition_dispatches_flags(monkeypatch):
    seen = {}
    monkeypatch.setattr(cli, "cmd_nav_transition", lambda path, route, args: seen.update(path=path, route=route, args=args) or 0)
    assert cli.main(["nav-transition", "/tmp/dataset", "4", "--enter", "doc", "2", "--row", "9"]) == 0
    assert seen == {"path": "/tmp/dataset", "route": "4", "args": ["--enter", "doc", "2", "--row", "9"]}


def test_private_reader_dispatches_and_rejects_bad_arity(monkeypatch, capsys):
    seen = {}
    monkeypatch.setattr(
        cli,
        "cmd_nav_reader_preview",
        lambda *args: seen.update(args=args) or 0,
    )
    assert cli.main(["nav-reader-preview", "/tmp/dataset", "4", "12"]) == 0
    assert seen["args"] == ("/tmp/dataset", "4", "12")
    assert cli.main(["nav-reader-move", "/tmp/dataset"]) == 1
    assert "Invalid navigation reader:" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("argv", "entry", "mode"),
    [
        ([], "home", "all"),
        (["screenshot"], "search:all", "all"),
        (["--docs"], "search:doc", "doc"),
        (["--cmds"], "search:cmd", "cmd"),
        (["--pages"], "pages", "doc"),
        (["--groups"], "groups", "cmd"),
        (["--page", "04-navigation.md"], "search:doc", "doc"),
        (["--group", "capture"], "search:cmd", "cmd"),
    ],
)
def test_main_selects_deterministic_entry_route(monkeypatch, argv, entry, mode):
    seen = {}
    monkeypatch.setattr(cli, "cmd_picker", lambda **kwargs: seen.update(kwargs) or 0)
    assert cli.main(argv) == 0
    assert seen["entry_route"] == entry
    assert seen["mode"] == mode


def test_main_preserves_initial_query_for_browse_route(monkeypatch):
    seen = {}
    monkeypatch.setattr(cli, "cmd_picker", lambda **kwargs: seen.update(kwargs) or 0)
    cli.main(["theme", "--pages"])
    assert seen["entry_route"] == "pages"
    assert seen["query"] == "theme"


def test_cmd_picker_flat_output_never_builds_dataset(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "_ensure_manual", lambda: tmp_path)
    monkeypatch.setattr(cli, "_load_content", lambda _: ([Section("01.md", 1, "One", "", "", "body")], {}))
    monkeypatch.setattr(cli, "find_commands", lambda: [Command("g", "x", "omarchy g x", "Do x")])
    monkeypatch.setattr(cli.sys.stdout, "isatty", lambda: False)
    monkeypatch.setattr(cli, "build_navigation_dataset", lambda *a, **k: pytest.fail("flat output must not build a dataset"))
    assert cli.cmd_picker(query="body") == 0
    assert "[doc] One" in capsys.readouterr().out


def test_cmd_picker_degraded_cmd_entry_is_explicit(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "_ensure_manual", lambda: tmp_path)
    monkeypatch.setattr(cli, "_load_content", lambda _: ([], {}))
    monkeypatch.setattr(cli, "find_commands", lambda: [])
    assert cli.cmd_picker(mode="cmd", plain=True) == 1
    assert "degraded mode" in capsys.readouterr().err


def test_cmd_picker_interactive_runs_once_and_resolves_command(monkeypatch, tmp_path, capsys):
    section = Section("01.md", 1, "One", "", "", "body")
    command = Command("g", "x", "omarchy g x", "Do x")
    monkeypatch.setattr(cli, "_ensure_manual", lambda: tmp_path)
    monkeypatch.setattr(cli, "_load_content", lambda _: ([section], {}))
    monkeypatch.setattr(cli, "find_commands", lambda: [command])
    monkeypatch.setattr(cli.sys.stdout, "isatty", lambda: True)
    dataset = build_navigation_dataset([section], [command], page_texts={"01.md": "body"})
    monkeypatch.setattr(cli, "build_navigation_dataset", lambda *a, **k: dataset)
    monkeypatch.setattr(cli, "run_fzf", lambda *a, **k: next(row.split("\t")[1] for row in navigation_rows(dataset.path, dataset.entry_routes["search:all"]).splitlines() if row.startswith("cmd\t")))
    try:
        assert cli.cmd_picker(query="x") == 0
        assert capsys.readouterr().out.strip() == "omarchy g x"
    finally:
        dataset.__exit__()


def test_nav_preview_rejects_unknown_id(capsys, tmp_path):
    assert cli.cmd_nav_preview(str(tmp_path), "1") == 1
    assert "Invalid navigation dataset" in capsys.readouterr().err


def test_nav_copy_rejects_document_rows(monkeypatch, capsys, tmp_path):
    section = Section("01.md", 1, "One", "", "", "body")
    dataset = build_navigation_dataset([section], [], page_texts={"01.md": "body"})
    try:
        assert cli.cmd_nav_copy(str(dataset.path), "1") == 1
        assert "Invalid navigation row" in capsys.readouterr().err
    finally:
        dataset.__exit__()


def test_reader_private_commands_render_directly_and_move_silently(
    monkeypatch, capsys, tmp_path
):
    section = Section("01.md", 1, "One", "", "", "line zero\nline one\nline two")
    dataset = build_navigation_dataset([section], [], page_texts={"01.md": section.text})
    try:
        preview_id = next(iter(_load_manifest(dataset.path)["previews"]))
        monkeypatch.setattr("om_search.picker.render_markdown", lambda text: text)
        monkeypatch.setenv("NO_COLOR", "1")
        assert cli.cmd_nav_reader_preview(str(dataset.path), preview_id, "3") == 0
        output = capsys.readouterr()
        assert output.err == ""
        assert output.out.startswith("Line 1/3\n")
        assert "▶ line zero" in output.out
        assert "\x1b[" not in output.out
        assert cli.cmd_nav_reader_move(str(dataset.path), preview_id, "down", "3") == 0
        assert capsys.readouterr().out == ""
        assert cli.cmd_nav_reader_preview(str(dataset.path), preview_id, "3") == 0
        assert capsys.readouterr().out.startswith("Line 2/3\n")
        assert cli.cmd_nav_reader_preview(str(dataset.path), preview_id, "0") == 1
        assert "Invalid navigation reader:" in capsys.readouterr().err
        assert cli.cmd_nav_reader_move(str(dataset.path), preview_id, "sideways") == 1
        assert "Invalid navigation reader:" in capsys.readouterr().err
        assert cli.cmd_nav_reader_preview(str(tmp_path), "1") == 1
        assert "Invalid navigation reader:" in capsys.readouterr().err
    finally:
        dataset.__exit__()
