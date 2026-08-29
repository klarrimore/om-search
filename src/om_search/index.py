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
    return _interleave(docs, cmds)


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

    ``--with-nth 4`` shows only the display field.  fzf then searches
    the transformed line (field 4 — the full display text), so users
    can find pages by typing words from the heading or title.
    """
    if cand.type == "doc":
        doc = cast(DocCandidate, cand)
        display = (
            f"[doc] {doc.page_title}  ::  {doc.heading}"
            if doc.heading
            else f"[doc] {doc.page_title}"
        )
        excerpt = doc.body_excerpt or _body_excerpt(doc.text)
        return "\t".join([cand.type, doc.page_file, doc.anchor, display, excerpt])
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
        excerpt = fields[4] if len(fields) >= 5 else ""
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