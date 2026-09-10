"""Eval cases for first-result ranking quality."""

import json
from pathlib import Path
from typing import Any

from om_search.commands import Command
from om_search.index import CmdCandidate, DocCandidate, build_candidates
from om_search.manual import Section


EVAL_PATH = Path(__file__).parent / "evals" / "ranking_cases.json"


def test_ranking_eval_expected_result_is_first():
    data = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    sections = [_section(item) for item in data["sections"]]
    commands = [_command(item) for item in data["commands"]]

    for case in data["cases"]:
        candidates = build_candidates(sections, commands, query=case["query"])
        assert candidates, case["query"]
        top = candidates[0]
        assert top.type == case["expected_type"], case["query"]

        if isinstance(top, DocCandidate):
            assert top.page_file == case["expected_page_file"], case["query"]
        elif isinstance(top, CmdCandidate):
            assert top.path == case["expected_path"], case["query"]

        if "max_results" in case:
            assert len(candidates) <= case["max_results"], case["query"]


def _section(item: dict[str, Any]) -> Section:
    return Section(
        page_file=item["page_file"],
        page_number=item["page_number"],
        page_title=item["page_title"],
        heading=item["heading"],
        anchor=item["anchor"],
        text=item["text"],
    )


def _command(item: dict[str, Any]) -> Command:
    return Command(
        group=item["group"],
        name=item["name"],
        path=item["path"],
        description=item["description"],
    )
