from __future__ import annotations

from copy import deepcopy

from sadparad1se_bot_stash import cleanup_event_content, parse_command


class FakeContent:
    def __init__(self, content: dict) -> None:
        self.content = content

    def serialize(self) -> dict:
        return deepcopy(self.content)


class FakeEvent:
    def __init__(self, content: dict) -> None:
        self.content = FakeContent(content)


def test_parse_multiline_stash() -> None:
    assert parse_command("!stash valheim\n\nsome text\nmore text", "stash") == (
        "!stash valheim\n\n",
        "valheim",
        "some text\nmore text",
    )


def test_parse_rejects_missing_key_and_returns_remainder() -> None:
    assert parse_command("!stash", "stash") is None
    assert parse_command("!unstash key extra", "unstash") == (
        "!unstash key ",
        "key",
        "extra",
    )
    assert parse_command("!unstash key", "unstash") == ("!unstash key", "key", "")


def test_relations_are_removed_without_mutating_input() -> None:
    original = {
        "msgtype": "m.image",
        "body": "map.png",
        "file": {
            "url": "mxc://example/map",
            "key": {"kty": "oct", "k": "secret"},
            "iv": "iv",
            "hashes": {"sha256": "hash"},
            "v": "v2",
        },
        "m.relates_to": {"m.in_reply_to": {"event_id": "$old"}},
        "m.new_content": {"body": "edited"},
    }
    result = cleanup_event_content(FakeEvent(original))
    assert "m.relates_to" not in result
    assert "m.new_content" not in result
    assert "m.relates_to" in original
    assert result["file"] == original["file"]


def test_cleanup_removes_command_prefix_from_text_and_formatted_body() -> None:
    original = {
        "msgtype": "m.text",
        "body": "!stash valheim some bold text",
        "format": "org.matrix.custom.html",
        "formatted_body": "!stash valheim some <strong>bold</strong> text",
    }
    result = cleanup_event_content(FakeEvent(original), "!stash valheim ")
    assert result["body"] == "some bold text"
    assert result["formatted_body"] == "some <strong>bold</strong> text"
