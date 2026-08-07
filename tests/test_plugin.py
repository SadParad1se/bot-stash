from __future__ import annotations

import asyncio

from maubot.matrix import MaubotMessageEvent
from maubot.testing import make_message
from mautrix.types import (
    ContentURI,
    EventType,
    ImageInfo,
    InReplyTo,
    MediaMessageEventContent,
    MessageEvent,
    MessageType,
    RelatesTo,
)


async def test_store_and_restore_text_globally(maubot_plugin, maubot_test_bot) -> None:
    await asyncio.wait_for(
        maubot_test_bot.send(
            "!stash Valheim\n\nsome text\nmore text", room_id="!source:example.com"
        ),
        timeout=3,
    )
    assert maubot_test_bot.responded[-1].content.body == "Stash entry Valheim updated."

    maubot_test_bot.responded.clear()
    await maubot_test_bot.send("!unstash valheim", room_id="!other:example.com")
    assert len(maubot_test_bot.responded) == 1
    restored = maubot_test_bot.responded[0]
    assert restored.room_id == "!other:example.com"
    assert restored.content.body == "some text\nmore text"


async def test_existing_key_appends_in_order(maubot_plugin, maubot_test_bot) -> None:
    await maubot_test_bot.send("!stash Key first")
    await maubot_test_bot.send("!stash KEY second")
    assert maubot_test_bot.responded[-1].content.body == "Stash entry KEY updated."

    maubot_test_bot.responded.clear()
    await maubot_test_bot.send("!unstash key")
    assert [event.content.body for event in maubot_test_bot.responded] == ["first", "second"]


async def test_reply_media_is_stored_and_relation_removed(
    maubot_plugin, maubot_test_bot, monkeypatch
) -> None:
    await maubot_test_bot.send("!stash map original", room_id="!source:example.com")
    target = MessageEvent(
        type=EventType.ROOM_MESSAGE,
        room_id="!source:example.com",
        event_id="$image",
        sender="@alice:example.com",
        timestamp=1,
        content=MediaMessageEventContent(
            msgtype=MessageType.IMAGE,
            body="map.png",
            url=ContentURI("mxc://example.com/map"),
            info=ImageInfo(mimetype="image/png", size=42, width=10, height=20),
            relates_to=RelatesTo(in_reply_to=InReplyTo(event_id="$older")),
        ),
    )

    async def get_event(room_id, event_id):
        assert room_id == "!source:example.com"
        assert event_id == "$image"
        return MaubotMessageEvent(target, maubot_test_bot.client)

    monkeypatch.setattr(maubot_test_bot.client, "get_event", get_event)
    command_event = make_message(
        "!stash map notes", room_id="!source:example.com", sender="@bob:example.com"
    )
    command_event.content.relates_to = RelatesTo(in_reply_to=InReplyTo(event_id="$image"))
    await maubot_test_bot.dispatch(
        EventType.ROOM_MESSAGE, MaubotMessageEvent(command_event, maubot_test_bot.client)
    )
    assert maubot_test_bot.responded[-1].content.body == "Stash entry map updated."

    maubot_test_bot.responded.clear()
    await maubot_test_bot.send("!unstash MAP", room_id="!destination:example.com")
    assert [event.content.body for event in maubot_test_bot.responded] == [
        "original",
        "notes",
        "map.png",
    ]
    media = maubot_test_bot.responded[2].content
    assert media.url == "mxc://example.com/map"
    assert media.info.mimetype == "image/png"
    assert media.get_reply_to() is None


async def test_destash_removes_entry(maubot_plugin, maubot_test_bot) -> None:
    await maubot_test_bot.send("!stash disposable value")
    await maubot_test_bot.send("!destash DISPOSABLE")
    assert maubot_test_bot.responded[-1].content.body == 'Stash named "DISPOSABLE" deleted.'

    await maubot_test_bot.send("!unstash disposable")
    assert maubot_test_bot.responded[-1].content.body == 'No stash named "disposable" exists.'


async def test_empty_and_unknown_stashes_report_errors(maubot_plugin, maubot_test_bot) -> None:
    await maubot_test_bot.send("!stash empty")
    assert maubot_test_bot.responded[-1].content.body.startswith("Add text")

    await maubot_test_bot.send("!unstash unknown")
    assert maubot_test_bot.responded[-1].content.body == 'No stash named "unknown" exists.'


async def test_undecryptable_reply_reports_error(
    maubot_plugin, maubot_test_bot, monkeypatch
) -> None:
    async def get_event(room_id, event_id):
        return None

    monkeypatch.setattr(maubot_test_bot.client, "get_event", get_event)
    command_event = make_message("!stash secret", sender="@bob:example.com")
    command_event.content.relates_to = RelatesTo(in_reply_to=InReplyTo(event_id="$encrypted"))
    await maubot_test_bot.dispatch(
        EventType.ROOM_MESSAGE, MaubotMessageEvent(command_event, maubot_test_bot.client)
    )
    assert "couldn't decrypt" in maubot_test_bot.responded[-1].content.body
