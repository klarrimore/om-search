"""Tests for parsing `omarchy commands --json` output."""

from om_search.commands import Command, parse_commands_json, list_groups


class TestListGroups:
    def test_returns_unique_sorted_groups(self):
        commands = [
            Command(group="capture", name="screenshot", path="omarchy capture screenshot",
                    description="Take a screenshot"),
            Command(group="audio", name="volume", path="omarchy audio volume",
                    description="Set volume"),
            Command(group="capture", name="qr", path="omarchy capture qr",
                    description="Decode a QR code"),
        ]
        assert list_groups(commands) == ["audio", "capture"]

    def test_empty_list_returns_empty(self):
        assert list_groups([]) == []


class TestParseCommandsJson:
    def test_grouped_dict_shape(self):
        raw = """
        {
          "capture": {
            "description": "Screenshots and screen recording",
            "commands": {
              "qr": {"description": "Decode a QR code from a screenshot region"},
              "screenshot": {"description": "Take a screenshot"}
            }
          },
          "audio": {
            "description": "Audio controls",
            "commands": {
              "volume": {"description": "Set volume"}
            }
          }
        }
        """
        commands = parse_commands_json(raw)
        assert commands == [
            Command(group="audio", name="volume", path="omarchy audio volume",
                    description="Set volume"),
            Command(group="capture", name="qr", path="omarchy capture qr",
                    description="Decode a QR code from a screenshot region"),
            Command(group="capture", name="screenshot", path="omarchy capture screenshot",
                    description="Take a screenshot"),
        ]

    def test_flat_list_shape(self):
        raw = """
        [
          {"group": "capture", "command": "qr", "description": "Decode a QR code"},
          {"group": "capture", "command": "screenshot", "description": "Take a screenshot"}
        ]
        """
        commands = parse_commands_json(raw)
        assert commands == [
            Command(group="capture", name="qr", path="omarchy capture qr",
                    description="Decode a QR code"),
            Command(group="capture", name="screenshot", path="omarchy capture screenshot",
                    description="Take a screenshot"),
        ]

    def test_full_path_shape(self):
        raw = """
        [
          {"command": "omarchy capture qr", "description": "Decode a QR code"},
          {"command": "omarchy theme list", "description": "List themes"}
        ]
        """
        commands = parse_commands_json(raw)
        assert commands == [
            Command(group="capture", name="qr", path="omarchy capture qr",
                    description="Decode a QR code"),
            Command(group="theme", name="list", path="omarchy theme list",
                    description="List themes"),
        ]

    def test_plain_dict_group_to_description(self):
        raw = '{"capture": "Screenshots and screen recording", "audio": "Audio controls"}'
        commands = parse_commands_json(raw)
        assert commands == []  # no command records inside, so nothing to index

    def test_invalid_json_returns_empty(self):
        assert parse_commands_json("{not valid json") == []

    def test_empty_input_returns_empty(self):
        assert parse_commands_json("") == []
