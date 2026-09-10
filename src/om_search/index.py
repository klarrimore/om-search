"""Building the unified search index from manual sections and CLI commands."""

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Union, cast

from om_search.commands import Command
from om_search.manual import Section, parse_manual_file


INDEX_VERSION = 1
INDEX_FILENAME = "index.json"
BODY_EXCERPT_LENGTH = 150

# The body excerpt is shown dimmed in the picker so the title/heading stays
# prominent while the excerpt remains fuzzy-matchable (fzf --ansi matches
# against the text with these codes stripped).
_DIM = "\x1b[2m"
_RESET = "\x1b[0m"
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


HAS_REAL_CONTENT_RE = re.compile(r"[a-zA-Z0-9]{3,}")


@dataclass(frozen=True)
class DocCandidate:
    """A manual section candidate for the fuzzy picker."""

    type: str = "doc"
    page_file: str = ""
    anchor: str = ""
    page_title: str = ""
    heading: str = ""
    text: str = ""
    body_excerpt: str = ""


@dataclass(frozen=True)
class CmdCandidate:
    """A CLI command candidate for the fuzzy picker."""

    type: str = "cmd"
    path: str = ""
    description: str = ""


Candidate = Union[DocCandidate, CmdCandidate]


def _interleave(
    docs: Sequence[Candidate], cmds: Sequence[Candidate], docs_per_cmd: int = 4
) -> list[Candidate]:
    """Interleave docs and commands so commands are visible early in the list.

    Places one command roughly every ``docs_per_cmd`` items.  Remaining
    items of the larger group are appended at the end.
    """
    result: list[Candidate] = []
    di, ci = 0, 0
    while di < len(docs) or ci < len(cmds):
        for _ in range(docs_per_cmd):
            if di < len(docs):
                result.append(docs[di])
                di += 1
        if ci < len(cmds):
            result.append(cmds[ci])
            ci += 1
    return result


def build_candidates(
    sections: list[Section],
    commands: list[Command],
    mode: str = "all",
    page_filter: str | None = None,
    group_filter: str | None = None,
    query: str = "",
) -> list[Candidate]:
    """Merge manual sections and CLI commands into a single candidate list.

    Parameters
    ----------
    sections:
        Parsed manual sections.
    commands:
        Parsed CLI command entries.
    mode:
        ``"all"`` (default), ``"doc"``, or ``"cmd"``.
    page_filter:
        If set, only include sections from this page file name.
    group_filter:
        If set, only include commands from this group.
    query:
        If set, rank candidates before handing them to fzf. Relevance is
        primary; newer manual page numbers break ties among similarly
        relevant doc sections.

    Results are interleaved so commands appear throughout the list rather
    than always at the bottom.  Within each type, docs sort by page number
    and commands sort by path.
    """
    docs = [
        DocCandidate(
            page_file=s.page_file,
            anchor=s.anchor,
            page_title=s.page_title,
            heading=s.heading,
            text=s.text,
        )
        for s in sorted(sections, key=lambda s: (s.page_number, s.heading))
        if mode != "cmd"
        and (page_filter is None or s.page_file == page_filter)
    ]
    cmds = [
        CmdCandidate(path=c.path, description=c.description)
        for c in sorted(commands, key=lambda c: c.path)
        if mode != "doc"
        and (group_filter is None or c.group == group_filter)
    ]
    candidates = _interleave(docs, cmds)
    if query:
        return rank_candidates(candidates, query)
    return candidates


def rank_candidates(candidates: Sequence[Candidate], query: str) -> list[Candidate]:
    """Rank candidates for an initial query before interactive fzf filtering.

    The project still relies on fzf for live fuzzy matching, but pre-ranking
    gives scripted/eval runs a deterministic ordering and makes the first
    screen favor exact title, heading, and command-path matches. Manual pages
    with higher page numbers are treated as newer when relevance ties.
    """
    terms = _query_terms(query)
    if not terms:
        return list(candidates)

    return sorted(
        candidates,
        key=lambda cand: _rank_key(cand, " ".join(terms), terms),
        reverse=True,
    )


def _query_terms(query: str) -> list[str]:
    """Normalize a query into searchable terms."""
    return re.findall(r"[a-z0-9]+", query.lower())


def _rank_key(cand: Candidate, query: str, terms: Sequence[str]) -> tuple[int, int, int]:
    """Return (relevance, recency, command boost) for descending sort."""
    if cand.type == "doc":
        doc = cast(DocCandidate, cand)
        title_heading = f"{doc.page_title} {doc.heading}".lower()
        body = doc.text.lower()
        relevance = _field_score(query, terms, title_heading, 120)
        relevance += _field_score(query, terms, body, 35)
        return relevance, _page_number_from_file(doc.page_file), 0

    cmd = cast(CmdCandidate, cand)
    path = cmd.path.lower()
    description = cmd.description.lower()
    relevance = _field_score(query, terms, path, 140)
    relevance += _field_score(query, terms, description, 45)
    return relevance, 0, 1


def _field_score(query: str, terms: Sequence[str], text: str, weight: int) -> int:
    """Score exact phrase and term coverage for one candidate field."""
    if not text:
        return 0

    score = 0
    if query in text:
        score += weight * 3

    for term in terms:
        if term in text:
            score += weight

    return score


def _page_number_from_file(page_file: str) -> int:
    """Extract manual page number from a candidate file name."""
    match = re.match(r"^(\d+)-", page_file)
    return int(match.group(1)) if match else 0


def _body_excerpt(text: str, max_len: int = BODY_EXCERPT_LENGTH) -> str:
    """Flatten first ``max_len`` chars of text for fzf body matching.

    Strips markdown heading markers, collapses whitespace, and truncates.
    If the excerpt after flattening is too short to be useful, return empty
    so fzf does not waste time matching tiny noise.
    """
    cleaned = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)
    flat = " ".join(cleaned.split())
    if not HAS_REAL_CONTENT_RE.search(flat):
        return ""
    return flat[:max_len]


def _section_to_dict(section: Section) -> dict[str, Any]:
    """Convert a Section to a JSON-serialisable dict."""
    return {
        "page_file": section.page_file,
        "page_number": section.page_number,
        "page_title": section.page_title,
        "heading": section.heading,
        "anchor": section.anchor,
        "text": section.text,
    }


def _section_from_dict(d: dict[str, Any]) -> Section:
    """Reconstruct a Section from a dict."""
    return Section(
        page_file=d["page_file"],
        page_number=d["page_number"],
        page_title=d["page_title"],
        heading=d["heading"],
        anchor=d["anchor"],
        text=d["text"],
    )


def build_index(mdir: Path, index_path: Path) -> None:
    """Parse all manual pages and write a pre-built JSON index.

    The index stores every section (with full text) plus the raw
    markdown of each page.  Call after cloning or updating the manual.
    """
    sections: list[dict[str, Any]] = []
    page_texts: dict[str, str] = {}
    for f in sorted(mdir.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        page_texts[f.name] = text
        for section in parse_manual_file(f):
            sections.append(_section_to_dict(section))

    data = {
        "version": INDEX_VERSION,
        "sections": sections,
        "page_texts": page_texts,
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_index(index_path: Path) -> tuple[list[Section], dict[str, str]] | None:
    """Load the pre-built JSON index.

    Returns ``(sections, page_texts)`` on success, ``None`` when the
    index is missing, corrupt, or has an incompatible version.
    """
    if not index_path.exists():
        return None
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
        if data.get("version") != INDEX_VERSION:
            return None
        sections = [_section_from_dict(s) for s in data["sections"]]
        page_texts = data.get("page_texts", {})
        return sections, page_texts
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def render_candidate(cand: Candidate) -> str:
    """Render a candidate as a tab-delimited fzf line.

    Field layout (0-indexed)::

        0: type        ("doc" | "cmd")               -- preview key
        1: page_file   (doc) | path       (cmd)       -- preview key
        2: anchor      (doc) | description (cmd)      -- preview key
        3: display     human-readable line for picker
        4: body        (doc) body excerpt for matching | (cmd) empty

    The picker runs with ``--with-nth 4,5``, so fzf both displays and
    searches the display field (4) and the dimmed body excerpt (5) — this
    is what makes doc bodies discoverable, since fzf can only match text it
    presents. The excerpt is wrapped in dim ANSI so the heading/title stays
    prominent; ``parse_fzf_line`` strips those codes back off.
    """
    if cand.type == "doc":
        doc = cast(DocCandidate, cand)
        display = (
            f"[doc] {doc.page_title}  ::  {doc.heading}"
            if doc.heading
            else f"[doc] {doc.page_title}"
        )
        excerpt = doc.body_excerpt or _body_excerpt(doc.text)
        shown = f"{_DIM}{excerpt}{_RESET}" if excerpt else ""
        return "\t".join([cand.type, doc.page_file, doc.anchor, display, shown])
    else:
        cmd = cast(CmdCandidate, cand)
        display = f"[cmd] {cmd.path}  ::  {cmd.description}"
        return "\t".join([cand.type, cmd.path, cmd.description, display, ""])


def parse_fzf_line(line: str) -> Candidate | None:
    """Parse a rendered fzf line back into its candidate.

    Accepts both 4-field (legacy without excerpt) and 5-field lines.
    """
    fields = line.split("\t")
    if not fields or fields[0] not in ("doc", "cmd"):
        return None
    if fields[0] == "doc":
        if len(fields) < 4:
            return None
        # Recover title/heading from the display text, stripping the type prefix
        display = fields[3]
        if display.startswith("[doc] "):
            display = display[6:]
        elif display.startswith("[cmd] "):
            display = display[6:]
        title, sep, heading = display.partition("  ::  ")
        excerpt = _ANSI_RE.sub("", fields[4]) if len(fields) >= 5 else ""
        return DocCandidate(
            page_file=fields[1],
            anchor=fields[2],
            page_title=title,
            heading=heading if sep else "",
            body_excerpt=excerpt,
        )
    else:
        if len(fields) < 3:
            return None
        return CmdCandidate(path=fields[1], description=fields[2])
