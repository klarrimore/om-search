"""Parsing `omarchy commands --json` output into structured command entries."""

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Command:
    """One command entry from the Omarchy CLI command tree."""

    group: str
    name: str
    path: str
    description: str


def parse_commands_json(raw: str) -> list[Command]:
    """Parse the output of `omarchy commands --json` into a flat command list.

    Accepts several plausible JSON shapes:
    - Grouped dict: {"group": {"description": "...", "commands": {"name": {...}}}}
    - Flat list: [{"group": "...", "command": "...", "description": "..."}]
    - Full-path list: [{"command": "omarchy group name", "description": "..."}]

    Returns an empty list when the JSON cannot be parsed or has no recognizable
    command shape.
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return []

    if isinstance(data, dict):
        return _parse_grouped_dict(data)
    elif isinstance(data, list):
        return _parse_flat_list(data)
    return []


def _parse_grouped_dict(data: dict[str, Any]) -> list[Command]:
    results: list[Command] = []
    for group, group_data in data.items():
        if not isinstance(group_data, dict):
            continue
        commands = group_data.get("commands") or group_data.get("subcommands")
        if not isinstance(commands, dict):
            continue
        for cmd_name, cmd_data in commands.items():
            if not isinstance(cmd_data, dict):
                continue
            desc = cmd_data.get("description", "") or ""
            results.append(
                Command(
                    group=group,
                    name=cmd_name,
                    path=f"omarchy {group} {cmd_name}",
                    description=str(desc),
                )
            )
    results.sort(key=lambda c: c.path)
    return results


def _parse_flat_list(data: list[Any]) -> list[Command]:
    results: list[Command] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        desc = (item.get("description") or item.get("desc") or item.get("summary") or "")
        # Full-path shape: {"command": "omarchy group name"}
        cmd = item.get("command") or item.get("name") or ""
        if not isinstance(cmd, str) or not cmd:
            continue
        if cmd.startswith("omarchy "):
            _parse_with_path(cmd, str(desc), results)
        else:
            # Flat shape: {"group": "...", "command": "..."}
            group = (item.get("group") or item.get("group_name") or "")
            name = cmd
            if group and name:
                results.append(
                    Command(
                        group=str(group),
                        name=str(name),
                        path=f"omarchy {group} {name}",
                        description=str(desc),
                    )
                )
    results.sort(key=lambda c: c.path)
    return results


def _parse_with_path(cmd: str, desc: str, results: list[Command]) -> None:
    parts = cmd.split()
    # "omarchy group name" → group=parts[1], name=parts[2]
    if len(parts) >= 3:
        results.append(
            Command(
                group=parts[1],
                name=parts[2],
                path=cmd,
                description=desc,
            )
        )