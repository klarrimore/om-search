"""Tests for manual parsing."""

import re
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "manual"

# Test targets imported from the package
from om_search.manual import Section, PageInfo, parse_manual_file, anchor_from_heading, list_pages


class TestListPages:
    def test_returns_all_pages(self):
        pages = list_pages(FIXTURES)
        titles = [p.page_title for p in pages]
        assert "Welcome to Omarchy!" in titles
        assert "Screenshots & Recording" in titles

    def test_sorted_by_page_number(self):
        pages = list_pages(FIXTURES)
        assert pages[0].page_number == 4
        assert pages[1].page_number == 12

    def test_page_file_included(self):
        pages = list_pages(FIXTURES)
        assert pages[0].page_file == "04-navigation.md"

    def test_page_info_dataclass(self):
        pages = list_pages(FIXTURES)
        assert isinstance(pages[0], PageInfo)


class TestAnchorFromHeading:
    def test_basic_heading(self):
        assert anchor_from_heading("Screenshots") == "screenshots"

    def test_with_spaces_and_punctuation(self):
        assert anchor_from_heading("The top bar") == "the-top-bar"

    def test_special_chars_removed(self):
        assert anchor_from_heading("Clipboard & History!") == "clipboard-history"

    def test_trailing_cruft(self):
        assert anchor_from_heading("Navigating [#]") == "navigating"


class TestParseManualFile:
    def test_parses_page_title_from_h1(self):
        f = FIXTURES / "04-navigation.md"
        sections = parse_manual_file(f)
        assert all(s.page_title == "Welcome to Omarchy!" for s in sections)

    def test_parses_page_number_from_filename(self):
        f = FIXTURES / "04-navigation.md"
        sections = parse_manual_file(f)
        assert all(s.page_number == 4 for s in sections)

    def test_parses_page_file_from_filename(self):
        f = FIXTURES / "04-navigation.md"
        sections = parse_manual_file(f)
        assert all(s.page_file == "04-navigation.md" for s in sections)

    def test_intro_section_has_empty_heading(self):
        f = FIXTURES / "04-navigation.md"
        sections = parse_manual_file(f)
        intro = [s for s in sections if s.heading == ""]
        assert len(intro) == 1
        assert "Omarchy is an omakase Linux distribution" in intro[0].text

    def test_h2_sections_parsed(self):
        f = FIXTURES / "04-navigation.md"
        sections = parse_manual_file(f)
        headings = [s.heading for s in sections if s.heading]
        assert "Navigating" in headings
        assert "The top bar" in headings
        assert "Themes" in headings

    def test_table_content_included(self):
        f = FIXTURES / "04-navigation.md"
        sections = parse_manual_file(f)
        nav = [s for s in sections if s.heading == "Navigating"][0]
        assert "Super + Space" in nav.text

    def test_page_with_two_sections(self):
        f = FIXTURES / "12-screenshots-recording.md"
        sections = parse_manual_file(f)
        headings = [s.heading for s in sections]
        assert "Screenshots" in headings
        assert "Screen recording" in headings
        assert len(sections) == 3  # intro + 2 sections

    def test_anchor_derived(self):
        f = FIXTURES / "12-screenshots-recording.md"
        sections = parse_manual_file(f)
        screenshots = [s for s in sections if s.heading == "Screenshots"][0]
        assert screenshots.anchor == "screenshots"


class TestH3Sections:
    """The live Omarchy manual uses H3 for subsections; nearly half the pages
    have no H2 at all, so H3 must also open a section (regression)."""

    def _write(self, tmp_path, body):
        f = tmp_path / "14-h3-page.md"
        f.write_text(body, encoding="utf-8")
        return f

    def test_h3_only_page_splits_into_subsections(self, tmp_path):
        f = self._write(
            tmp_path,
            "# Navigation\n\nIntro blurb.\n\n"
            "### Dwindle vs scrolling layout\n\nDwindle body.\n\n"
            "### Grouping windows\n\nGrouping body.\n",
        )
        sections = parse_manual_file(f)
        headings = [s.heading for s in sections]
        assert headings == ["", "Dwindle vs scrolling layout", "Grouping windows"]
        assert len(sections) == 3  # intro + 2 subsections, not one blob

    def test_h3_section_has_anchor_and_body(self, tmp_path):
        f = self._write(
            tmp_path,
            "# Navigation\n\n### Grouping windows\n\nUse Super+Tab to group.\n",
        )
        grouping = [s for s in parse_manual_file(f) if s.heading == "Grouping windows"][0]
        assert grouping.anchor == "grouping-windows"
        assert "Super+Tab" in grouping.text

    def test_h3_text_preserves_heading_level(self, tmp_path):
        f = self._write(tmp_path, "# T\n\n### Sub\n\nbody\n")
        sub = [s for s in parse_manual_file(f) if s.heading == "Sub"][0]
        assert sub.text.startswith("### Sub")

    def test_mixed_h2_and_h3_both_open_sections(self, tmp_path):
        f = self._write(
            tmp_path,
            "# T\n\n## Top\n\ntop body\n\n### Nested\n\nnested body\n\n## Other\n\nother\n",
        )
        headings = [s.heading for s in parse_manual_file(f) if s.heading]
        assert headings == ["Top", "Nested", "Other"]


from om_search.manual import extract_links


class TestExtractLinks:
    def test_extracts_page_links_in_order(self):
        text = (
            "See [navigation](04-navigation.md) and "
            "[the top bar](05-the-top-bar.md).\n"
        )
        assert extract_links(text) == [
            ("navigation", "04-navigation.md", ""),
            ("the top bar", "05-the-top-bar.md", ""),
        ]

    def test_captures_anchor_fragment(self):
        text = "Jump to [grouping](04-navigation.md#grouping-windows)."
        assert extract_links(text) == [
            ("grouping", "04-navigation.md", "grouping-windows"),
        ]

    def test_ignores_external_and_relative_non_manual_links(self):
        text = (
            "[site](https://omarchy.org) [img](./pic.png) "
            "[real](12-screenshots-recording.md)"
        )
        assert extract_links(text) == [
            ("real", "12-screenshots-recording.md", ""),
        ]

    def test_no_links_returns_empty(self):
        assert extract_links("# Heading\n\nplain body, no links.\n") == []