"""Parsing the Omarchy manual markdown files into searchable sections."""

import re
from dataclasses import dataclass
from pathlib import Path

H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
HEADING_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*\[?#?\]?\s*$", re.MULTILINE)
ANCHOR_CHARS_RE = re.compile(r"[^a-z0-9\s-]")


@dataclass(frozen=True)
class Section:
    """One searchable slice of the manual: a page's intro or an H2 section."""

    page_file: str
    page_number: int
    page_title: str
    heading: str
    anchor: str
    text: str


@dataclass(frozen=True)
class PageInfo:
    """Metadata about one manual page, used for browsing."""

    page_file: str
    page_number: int
    page_title: str


def anchor_from_heading(heading: str) -> str:
    """Convert a markdown heading into the anchor slug the website uses.

    Lowercases, replaces runs of spaces with hyphens, and drops anything
    that is not a letter, digit, space, or hyphen.
    """
    slug = ANCHOR_CHARS_RE.sub("", heading.lower())
    return re.sub(r"\s+", "-", slug).strip("-")


def list_pages(mdir: Path) -> list[PageInfo]:
    """Scan the manual directory and return metadata for every page.

    Pages are sorted by their numeric prefix.  Only ``.md`` files that
    start with a digit are included.
    """
    pages: list[PageInfo] = []
    for f in sorted(mdir.glob("[0-9]*.md")):
        text = f.read_text(encoding="utf-8")
        match = H1_RE.search(text)
        title = match.group(1).strip() if match else f.stem
        num = _number_from_filename(f.name)
        pages.append(PageInfo(page_file=f.name, page_number=num, page_title=title))
    return pages


def parse_manual_file(path: Path) -> list[Section]:
    """Split one manual page into sections.

    The page title comes from the first H1. The text before the first
    subheading becomes the intro section (empty heading). Each H2 or H3
    heading opens a new section that runs until the next heading of either
    level. (The Omarchy manual uses H3 for most subsections and only
    sometimes H2, so both must act as boundaries.)
    """
    text = path.read_text(encoding="utf-8")
    page_file = path.name
    page_number = _number_from_filename(page_file)

    title_match = H1_RE.search(text)
    page_title = title_match.group(1).strip() if title_match else page_file

    heading_matches = list(HEADING_RE.finditer(text))
    sections: list[Section] = []

    if not heading_matches:
        return [Section(page_file, page_number, page_title, "", "", text.strip())]

    intro_text = text[: heading_matches[0].start()].strip()
    if intro_text:
        sections.append(
            Section(page_file, page_number, page_title, "", "", intro_text)
        )

    for i, match in enumerate(heading_matches):
        hashes = match.group(1)
        heading = match.group(2).strip()
        end = (
            heading_matches[i + 1].start()
            if i + 1 < len(heading_matches)
            else len(text)
        )
        body = text[match.end() : end].strip()
        sections.append(
            Section(
                page_file,
                page_number,
                page_title,
                heading,
                anchor_from_heading(heading),
                f"{hashes} {heading}\n\n{body}",
            )
        )

    return sections


def _number_from_filename(name: str) -> int:
    """Extract the leading page number from a manual filename.

    Returns 0 when the name has no numeric prefix.
    """
    match = re.match(r"^(\d+)-", name)
    return int(match.group(1)) if match else 0