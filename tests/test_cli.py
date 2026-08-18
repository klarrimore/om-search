"""Tests for CLI argument parsing — flags and dispatch."""

from om_search.cli import build_parser


def test_parser_defaults():
    parser = build_parser()
    args = parser.parse_args([])
    assert args.docs is False
    assert args.cmds is False
    assert args.page is None
    assert args.group is None
    assert args.update is False
    assert args.pages is False
    assert args.groups is False
    assert args.query == []


def test_parser_query_positional():
    parser = build_parser()
    args = parser.parse_args(["screenshot", "region"])
    assert args.query == ["screenshot", "region"]


def test_parser_docs_flag():
    parser = build_parser()
    args = parser.parse_args(["--docs", "volume"])
    assert args.docs is True
    assert args.cmds is False
    assert args.query == ["volume"]


def test_parser_cmds_flag():
    parser = build_parser()
    args = parser.parse_args(["--cmds"])
    assert args.cmds is True
    assert args.docs is False


def test_parser_page_option():
    parser = build_parser()
    args = parser.parse_args(["--page", "04-navigation.md"])
    assert args.page == "04-navigation.md"


def test_parser_group_option():
    parser = build_parser()
    args = parser.parse_args(["--group", "capture"])
    assert args.group == "capture"


def test_parser_update_flag():
    parser = build_parser()
    args = parser.parse_args(["--update"])
    assert args.update is True


def test_parser_pages_flag():
    parser = build_parser()
    args = parser.parse_args(["--pages"])
    assert args.pages is True


def test_parser_groups_flag():
    parser = build_parser()
    args = parser.parse_args(["--groups"])
    assert args.groups is True


def test_parser_pages_with_query():
    parser = build_parser()
    args = parser.parse_args(["--pages", "theme"])
    assert args.pages is True
    assert args.query == ["theme"]


def test_parser_query_and_flag():
    parser = build_parser()
    args = parser.parse_args(["screenshot", "--docs"])
    assert args.query == ["screenshot"]
    assert args.docs is True


def test_parser_flag_after_query():
    parser = build_parser()
    args = parser.parse_args(["screenshot", "--page", "04-navigation.md"])
    assert args.query == ["screenshot"]
    assert args.page == "04-navigation.md"