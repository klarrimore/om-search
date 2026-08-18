"""Parsing the Omarchy manual markdown files into searchable sections."""

import re
from dataclasses import dataclass
from pathlib import Path

H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
H2_RE = re.compile(r"^##\s+(.+?)\s*\[?#?\]?\s*$", re.MULTILINE)
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

    The page title comes from the first H1. The text before the first H2
    becomes the intro section (empty heading). Each H2 opens a new section
    that runs until the next H2.
    """
    text = path.read_text(encoding="utf-8")
    page_file = path.name
    page_number = _number_from_filename(page_file)

    title_match = H1_RE.search(text)
    page_title = title_match.group(1).strip() if title_match else page_file

    h2_matches = list(H2_RE.finditer(text))
    sections: list[Section] = []

    if not h2_matches:
        return [Section(page_file, page_number, page_title, "", "", text.strip())]

    intro_text = text[: h2_matches[0].start()].strip()
    if intro_text:
        intro_heading = ""
        sections.append(
            Section(page_file, page_number, page_title, intro_heading, "", intro_text)
        )

    for i, match in enumerate(h2_matches):
        heading = match.group(1).strip()
        end = h2_matches[i + 1].start() if i + 1 < len(h2_matches) else len(text)
        body = text[match.end() : end].strip()
        sections.append(
            Section(
                page_file,
                page_number,
                page_title,
                heading,
                anchor_from_heading(heading),
                f"## {heading}\n\n{body}",
            )
        )

    return sections


def _number_from_filename(name: str) -> int:
    """Extract the leading page number from a manual filename.

    Returns 0 when the name has no numeric prefix.
    """
    match = re.match(r"^(\d+)-", name)
    return int(match.group(1)) if match else 0