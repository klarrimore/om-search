"""Building the unified search index from manual sections and CLI commands."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Union, cast

from om_search.commands import Command
from om_search.manual import Section


@dataclass(frozen=True)
class DocCandidate:
    """A manual section candidate for the fuzzy picker."""

    type: str = "doc"
    page_file: str = ""
    anchor: str = ""
    page_title: str = ""
    heading: str = ""
    text: str = ""


@dataclass(frozen=True)
class CmdCandidate:
    """A CLI command candidate for the fuzzy picker."""

    type: str = "cmd"
    path: str = ""
    description: str = ""


Candidate = Union[DocCandidate, CmdCandidate]


def _interleave(docs: Sequence[Candidate], cmds: Sequence[Candidate], docs_per_cmd: int = 4) -> list[Candidate]:
    """Interleave docs and commands so commands are visible early in the list.

    Places one command roughly every `docs_per_cmd` items.  Remaining items
    of the larger group are appended at the end.
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
    sections: list[Section], commands: list[Command]
) -> list[Candidate]:
    """Merge manual sections and CLI commands into a single candidate list.

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
    ]
    cmds = [
        CmdCandidate(path=c.path, description=c.description)
        for c in sorted(commands, key=lambda c: c.path)
    ]
    return _interleave(docs, cmds)


def render_candidate(cand: Candidate) -> str:
    """Render a candidate as a tab-delimited fzf line.

    Field layout (0-indexed):
      0: type        ("doc" | "cmd")
      1: page_file   (doc)  | path       (cmd)   -- preview key
      2: anchor      (doc)  | description (cmd)   -- preview key
      3: display     human-readable line for the picker

    The display text is a single field so `--with-nth 4` works for both types.
    The full section text is never embedded in the line (it may contain
    newlines); the preview and action commands read it from the file.
    """
    if cand.type == "doc":
        doc = cast(DocCandidate, cand)
        display = (
            f"[doc] {doc.page_title}  ::  {doc.heading}"
            if doc.heading
            else f"[doc] {doc.page_title}"
        )
        return "\t".join([cand.type, doc.page_file, doc.anchor, display])
    else:
        cmd = cast(CmdCandidate, cand)
        display = f"[cmd] {cmd.path}  ::  {cmd.description}"
        return "\t".join([cand.type, cmd.path, cmd.description, display])


def parse_fzf_line(line: str) -> Candidate | None:
    """Parse a rendered fzf line back into its candidate."""
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
        return DocCandidate(
            page_file=fields[1],
            anchor=fields[2],
            page_title=title,
            heading=heading if sep else "",
        )
    else:
        if len(fields) < 3:
            return None
        return CmdCandidate(path=fields[1], description=fields[2])
