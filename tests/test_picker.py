"""Tests for fzf integration — preview, section reading, and actions."""

import json

import pytest

from om_search.index import DocCandidate, CmdCandidate, build_index, INDEX_FILENAME
from om_search.picker import action_for, section_text, picker_header
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
        assert "Enter: open" in h

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


class TestAction:
    def test_action_picks_pager_and_text_for_doc(self):
        cand = DocCandidate(
            page_file=FIXTURE_FILE, anchor="navigating",
            page_title="Navigation", heading="Navigating",
        )
        pager, text = action_for(cand)
        assert pager in ("glow", "less", "cat")
        assert "Super + Space" in text

    def test_action_echoes_command_for_cmd(self):
        cand = CmdCandidate(
            path="omarchy capture screenshot",
            description="Take a screenshot",
        )
        pager, text = action_for(cand)
        assert pager == "echo"
        assert text == "omarchy capture screenshot"