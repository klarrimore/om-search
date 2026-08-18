"""Tests for building, rendering, and parsing the fzf candidate index."""

from om_search.index import (
    DocCandidate,
    CmdCandidate,
    build_candidates,
    render_candidate,
    parse_fzf_line,
)
from om_search.manual import Section
from om_search.commands import Command


def test_build_candidates_sections_and_commands():
    sections = [
        Section(
            page_file="04-navigation.md", page_number=4,
            page_title="Welcome to Omarchy!", heading="Navigating",
            anchor="navigating", text="## Navigating\n\nSuper + Space opens the menu.",
        ),
        Section(
            page_file="04-navigation.md", page_number=4,
            page_title="Welcome to Omarchy!", heading="",
            anchor="", text="Omarchy is an omakase Linux distribution.",
        ),
    ]
    commands = [
        Command(group="capture", name="screenshot", path="omarchy capture screenshot",
                description="Take a screenshot"),
    ]

    candidates = build_candidates(sections, commands)
    assert len(candidates) == 3

    docs = [c for c in candidates if c.type == "doc"]
    cmds = [c for c in candidates if c.type == "cmd"]
    assert len(docs) == 2
    assert len(cmds) == 1

    assert docs[0].heading == ""
    assert docs[1].heading == "Navigating"
    assert cmds[0].path == "omarchy capture screenshot"


class TestBuildMode:
    def test_doc_mode_excludes_commands(self):
        sections = [
            Section(page_file="01-test.md", page_number=1,
                    page_title="Test", heading="",
                    anchor="", text="Content."),
        ]
        commands = [
            Command(group="t", name="c", path="omarchy t c", description="cmd"),
        ]
        candidates = build_candidates(sections, commands, mode="doc")
        assert all(c.type == "doc" for c in candidates)

    def test_cmd_mode_excludes_docs(self):
        sections = [
            Section(page_file="01-test.md", page_number=1,
                    page_title="Test", heading="",
                    anchor="", text="Content."),
        ]
        commands = [
            Command(group="t", name="c", path="omarchy t c", description="cmd"),
        ]
        candidates = build_candidates(sections, commands, mode="cmd")
        assert all(c.type == "cmd" for c in candidates)

    def test_page_filter_filters_docs(self):
        sections = [
            Section(page_file="01-a.md", page_number=1,
                    page_title="A", heading="", anchor="", text="A."),
            Section(page_file="02-b.md", page_number=2,
                    page_title="B", heading="", anchor="", text="B."),
        ]
        candidates = build_candidates(sections, [], page_filter="01-a.md")
        assert len(candidates) == 1
        assert candidates[0].page_file == "01-a.md"

    def test_group_filter_filters_commands(self):
        commands = [
            Command(group="audio", name="vol", path="omarchy audio vol",
                    description="Volume"),
            Command(group="capture", name="shot", path="omarchy capture shot",
                    description="Screenshot"),
        ]
        candidates = build_candidates([], commands, group_filter="audio")
        assert len(candidates) == 1
        assert candidates[0].path == "omarchy audio vol"


def test_render_round_trips_doc():
    cand = DocCandidate(
        page_file="04-navigation.md", anchor="navigating",
        page_title="Welcome to Omarchy!", heading="Navigating",
    )
    line = render_candidate(cand)
    assert line.startswith("doc\t")
    assert "04-navigation.md" in line
    assert "navigating" in line
    assert "Welcome to Omarchy!" in line

    parsed = parse_fzf_line(line)
    assert parsed == cand


def test_render_round_trips_cmd():
    cand = CmdCandidate(
        path="omarchy capture screenshot", description="Take a screenshot",
    )
    line = render_candidate(cand)
    assert line.startswith("cmd\t")
    assert "omarchy capture screenshot" in line
    assert "Take a screenshot" in line

    parsed = parse_fzf_line(line)
    assert parsed == cand


def test_parse_unknown_type_returns_none():
    assert parse_fzf_line("unknown\tstuff") is None


def test_parse_malformed_returns_none():
    assert parse_fzf_line("") is None
    assert parse_fzf_line("doc\t") is None


def test_render_display_field_for_cmd_contains_both():
    cand = CmdCandidate(path="omarchy theme list", description="List themes")
    line = render_candidate(cand)
    assert "omarchy theme list" in line
    assert "List themes" in line