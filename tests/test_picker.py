"""Observable contracts for hierarchical picker navigation."""

from __future__ import annotations

import types

import pytest

from om_search.commands import Command
from om_search.config import Config
from om_search.manual import Section
from om_search.picker import (
    _load_manifest,
    build_navigation_dataset,
    keys_cheatsheet,
    navigation_preview,
    navigation_reader_move,
    navigation_reader_preview,
    navigation_row,
    navigation_rows,
    navigation_transition_action,
    run_fzf,
)


@pytest.fixture
def dataset():
    sections = [
        Section("01-one.md", 1, "One", "", "", "intro [two](02-two.md#part)"),
        Section("01-one.md", 1, "One", "Part", "part", "body"),
        Section("02-two.md", 2, "Two", "Part", "part", "target body"),
    ]
    commands = [Command("capture", "shot", "omarchy capture shot", "Take a shot")]
    data = build_navigation_dataset(
        sections,
        commands,
        cfg=Config(theme_source="none"),
        page_texts={"01-one.md": "# One\n\nintro [two](02-two.md#part)", "02-two.md": "# Two\n\ntarget body"},
    )
    yield data
    data.__exit__()


def test_home_rows_have_exact_schema_and_degraded_home(tmp_path):
    data = build_navigation_dataset(
        [Section("01.md", 1, "One", "", "", "body")],
        [],
        cfg=Config(theme_source="none"),
    )
    try:
        row = navigation_rows(data.path, data.entry_routes["home"]).splitlines()[0]
        assert len(row.split("\t")) == 7
        fields = row.split("\t")
        assert fields[:5] == ["route", "1", data.entry_routes["search:all"], "0", "0"]
        assert "Command groups" not in navigation_rows(data.path, data.entry_routes["home"])
    finally:
        data.__exit__()


def test_routes_have_parent_target_relationships(dataset):
    home = navigation_rows(dataset.path, dataset.entry_routes["home"]).splitlines()
    pages = home[1].split("\t")
    assert pages[0] == "route"
    assert pages[2] == dataset.entry_routes["pages"]
    assert pages[3] == "0"
    page_row = navigation_rows(dataset.path, dataset.entry_routes["pages"]).splitlines()[0].split("\t")
    assert page_row[2].startswith(tuple(dataset.entry_routes.values()))
    assert page_row[3] == dataset.entry_routes["home"]


def test_doc_rows_and_links_are_materialized(dataset):
    manifest = _load_manifest(dataset.path)
    search_rows = navigation_rows(dataset.path, dataset.entry_routes["search:doc"]).splitlines()
    doc = next(row.split("\t") for row in search_rows if row.startswith("doc\t"))
    assert doc[4] != "0"
    assert doc[2] != "0"  # Ctrl-L target route for the originating page.
    link_route = doc[2]
    link = navigation_rows(dataset.path, link_route).splitlines()[0].split("\t")
    assert link[0] == "link"
    assert link[3] == dataset.entry_routes["search:doc"]
    assert link[4] in manifest["previews"]
    assert "target body" in navigation_preview(dataset.path, link[4])


def _reader_fixture_preview(dataset):
    preview_id = next(iter(_load_manifest(dataset.path)["previews"]))
    manifest = _load_manifest(dataset.path)
    preview_file = manifest["previews"][preview_id]["file"]
    (dataset.path / preview_file).write_text(
        "\n".join(f"line {index}" for index in range(6)), encoding="utf-8"
    )
    return preview_id


def test_reader_cursor_state_is_cached_and_independent(monkeypatch, dataset):
    preview_id = _reader_fixture_preview(dataset)
    other_id = next(
        value for value in _load_manifest(dataset.path)["previews"] if value != preview_id
    )
    calls = []
    monkeypatch.setattr(
        "om_search.picker.render_markdown",
        lambda text: calls.append(text) or text,
    )
    monkeypatch.setenv("NO_COLOR", "1")

    assert navigation_reader_move(dataset.path, preview_id, "reset") == 0
    assert navigation_reader_move(dataset.path, preview_id, "down") == 1
    assert navigation_reader_move(dataset.path, preview_id, "page-down", 4) == 3
    assert navigation_reader_move(dataset.path, preview_id, "down") == 4
    assert navigation_reader_move(dataset.path, preview_id, "down") == 5
    assert navigation_reader_move(dataset.path, preview_id, "down") == 5
    assert navigation_reader_move(dataset.path, preview_id, "up") == 4
    assert navigation_reader_move(dataset.path, other_id, "reset") == 0
    assert navigation_reader_preview(dataset.path, preview_id, 4).startswith("Line 5/6\n")
    assert "▶ line 4" in navigation_reader_preview(dataset.path, preview_id, 4)
    assert navigation_reader_preview(dataset.path, other_id, 4).startswith("Line 1/")
    assert len(calls) == 2


def test_reader_preview_empty_and_rejects_invalid_state(monkeypatch, dataset):
    preview_id = _reader_fixture_preview(dataset)
    manifest = _load_manifest(dataset.path)
    (dataset.path / manifest["previews"][preview_id]["file"]).write_text("", encoding="utf-8")
    monkeypatch.setattr("om_search.picker.render_markdown", lambda text: text)
    assert navigation_reader_preview(dataset.path, preview_id) == "Line 0/0\n"
    assert navigation_reader_move(dataset.path, preview_id, "down") == 0
    for invalid_id in ("0", "999999", "../1"):
        with pytest.raises(ValueError):
            navigation_reader_preview(dataset.path, invalid_id)
    with pytest.raises(ValueError):
        navigation_reader_move(dataset.path, preview_id, "sideways")


def test_transition_actions_are_contextual(dataset):
    pages = navigation_transition_action(dataset.path, dataset.entry_routes["pages"])
    assert "reload-sync" in pages and "clear-query" in pages
    assert "Home › Manual pages" in pages
    doc = navigation_rows(dataset.path, dataset.entry_routes["search:doc"]).splitlines()[0].split("\t")
    reading = navigation_transition_action(
        dataset.path,
        doc[2],
        enter_kind=doc[0],
        parent_route_id=doc[3],
        row_id=doc[1],
    )
    assert "change-prompt(  reading  )" in reading
    assert "nav-reader-preview" in reading
    assert "nav-reader-move" in reading
    assert "execute-silent" in reading
    assert "reload-sync" not in reading and "clear-query" not in reading
    assert "change-preview-window" in reading
    no_links = navigation_transition_action(dataset.path, "0", links=True, parent_route_id=dataset.entry_routes["pages"])
    assert "No links on this page" in no_links


def test_run_fzf_uses_one_dataset_process_and_contextual_keys(monkeypatch, dataset):
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["input"] = kwargs["input"]
        return types.SimpleNamespace(stdout="cmd\t99\t0\t0\t0\tdisplay\tsearch\n", returncode=0)

    monkeypatch.setattr("om_search.picker.subprocess.run", fake_run)
    selected = run_fzf(dataset.path, dataset.entry_routes["home"], cfg=Config(theme_source="none"))
    command = captured["command"]
    assert selected == "99"
    assert "--preview" in command
    assert "nav-preview" in command[command.index("--preview") + 1]
    binds = [command[i + 1] for i, value in enumerate(command) if value == "--bind"]
    bind_text = "\n".join(binds)
    assert any("reload-sync" in bind or "nav-transition" in bind for bind in binds)
    assert "nav-reader-move" in bind_text
    tab_bind = next(bind for bind in binds if bind.startswith("tab:"))
    assert "{1} == doc" in tab_bind and "{1} == link" in tab_bind
    assert "change-preview(om-search nav-preview" in tab_bind
    assert "clear-query" not in tab_bind and "reload-sync" not in tab_bind
    assert any("reading" in bind for bind in binds)
    assert "\tSearch all\t" in captured["input"]


def test_invalid_manifest_ids_and_kinds_are_rejected(dataset):
    with pytest.raises(ValueError):
        navigation_preview(dataset.path, "999999")
    with pytest.raises(ValueError):
        navigation_row(dataset.path, "1", kinds={"cmd"})


def test_cheatsheet_documents_builtin_selector_keys():
    sheet = keys_cheatsheet(Config())
    assert "Built-in selector keys" in sheet
    assert "PageUp / PageDown" in sheet
    assert "move cursor" in sheet
    assert "focus / unfocus reader" in sheet
    assert "Enter / Right" in sheet
    assert "Left / Escape" in sheet
