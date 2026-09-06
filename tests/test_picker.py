"""Tests for fzf integration — preview, section reading, and actions."""

import json
import types

import pytest

import om_search.picker as picker
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


class TestRunFzf:
    def test_search_scope_includes_body_excerpt_field(self, monkeypatch):
        """Regression: fzf must search field 5 (body excerpt), not just the
        display field, or doc bodies become undiscoverable. fzf only matches
        text it presents, so --with-nth must include both 4 and 5."""
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return types.SimpleNamespace(stdout="")

        monkeypatch.setattr("om_search.picker.subprocess.run", fake_run)
        run_fzf(["doc\ta.md\tanchor\t[doc] Title\tbody words here"])

        cmd = captured["cmd"]
        assert "--with-nth" in cmd
        assert cmd[cmd.index("--with-nth") + 1] == "4,5"


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