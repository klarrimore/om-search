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