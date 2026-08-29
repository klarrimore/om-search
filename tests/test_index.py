"""Tests for building, rendering, and parsing the fzf candidate index."""

from om_search.index import (
    DocCandidate,
    CmdCandidate,
    _body_excerpt,
    build_candidates,
    build_index,
    load_index,
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


def test_render_doc_includes_body_excerpt_field():
    cand = DocCandidate(
        page_file="35-networking.md", anchor="sharing-your-wi-fi",
        page_title="Networking", heading="Sharing your Wi-Fi",
        text="## Sharing your Wi-Fi\n\nRun _Setup > Network > QR Code_ while you're on Wi-Fi.",
    )
    line = render_candidate(cand)
    parts = line.split("\t")
    assert len(parts) == 5
    assert parts[3].startswith("[doc] Networking")
    # Body excerpt present and flattened (no newlines)
    assert "QR Code" in parts[4]
    assert "\n" not in parts[4]


def test_parse_fzf_line_round_trips_five_field_doc():
    cand = DocCandidate(
        page_file="35-networking.md", anchor="sharing-your-wi-fi",
        page_title="Networking", heading="Sharing your Wi-Fi",
        body_excerpt="Run QR Code while you're on Wi-Fi",
    )
    parsed = parse_fzf_line(render_candidate(cand))
    assert parsed == cand


def test_parse_fzf_line_accepts_legacy_four_field_doc():
    line = "\t".join(["doc", "04-navigation.md", "navigating", "[doc] Navigation  ::  Navigating"])
    parsed = parse_fzf_line(line)
    assert parsed is not None
    assert parsed.type == "doc"
    assert parsed.body_excerpt == ""
    assert parsed.page_file == "04-navigation.md"


def test_body_excerpt_strips_heading_markers_and_truncates():
    text = "## Heading\n\nThis is a **long** body with   extra spaces and\nnewlines."
    excerpt = _body_excerpt(text, max_len=80)
    # H2 marker stripped, whitespace collapsed, inline markers preserved
    assert excerpt.startswith("Heading This is a **long** body")
    assert "\n" not in excerpt
    assert len(excerpt) <= 80


def test_body_excerpt_empty_for_noise():
    assert _body_excerpt("## \n\n  \n") == ""


def test_build_index_round_trip(tmp_path):
    mdir = tmp_path / "manual"
    mdir.mkdir()
    (mdir / "01-hello.md").write_text(
        "# Hello\n\nIntro text.\n\n## Section One\n\nBody text here.\n"
    )
    (mdir / "02-two.md").write_text(
        "# Two\n\nOnly intro, no headings.\n"
    )
    index_path = tmp_path / "index.json"

    build_index(mdir, index_path)
    assert index_path.exists()

    sections, page_texts = load_index(index_path)
    assert len(sections) == 3  # 2 intros + 1 H2 section
    assert len(page_texts) == 2
    assert page_texts["01-hello.md"].startswith("# Hello")
    assert any(s.heading == "Section One" for s in sections)
    assert any("Body text here." in s.text for s in sections)


def test_load_missing_index_returns_none(tmp_path):
    assert load_index(tmp_path / "nope.json") is None


def test_load_corrupt_index_returns_none(tmp_path):
    index_path = tmp_path / "index.json"
    index_path.write_text("not json {")
    assert load_index(index_path) is None


def test_load_version_mismatch_returns_none(tmp_path):
    index_path = tmp_path / "index.json"
    index_path.write_text('{"version": 999, "sections": [], "page_texts": {}}')
    assert load_index(index_path) is None