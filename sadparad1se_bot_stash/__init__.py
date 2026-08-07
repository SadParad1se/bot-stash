from __future__ import annotations

import json
import re
from typing import Any

from maubot import MessageEvent, Plugin
from maubot.handlers import command
from mautrix.types import EventType, MessageType
from mautrix.types.event.message import MessageEvent as MautrixMessageEvent
from mautrix.util.async_db import UpgradeTable

from .migrations import upgrade_table

SUPPORTED_MESSAGE_TYPES = frozenset(
    {
        MessageType.TEXT,
        MessageType.NOTICE,
        MessageType.EMOTE,
        MessageType.IMAGE,
        MessageType.VIDEO,
        MessageType.AUDIO,
        MessageType.FILE,
    }
)


def parse_command(body: str, command_name: str) -> tuple[str, str, str] | None:
    match = re.fullmatch(rf"(!{command_name}\s(\S+)\s*)(.*)", body, re.IGNORECASE | re.DOTALL)
    if not match:
        return None

    prefix, stash_name, remainder = match.groups()
    return prefix, stash_name, remainder


def cleanup_event_content(
    evt: MessageEvent | MautrixMessageEvent, remove_prefix: str = ""
) -> dict[str, Any]:
    content = evt.content.serialize()

    content.pop("m.relates_to", None)
    content.pop("m.new_content", None)

    if remove_prefix:
        if body := content.get("body", ""):
            content["body"] = body.removeprefix(remove_prefix)
        if formatted_body := content.get("formatted_body", ""):
            content["formatted_body"] = formatted_body.removeprefix(remove_prefix)

    return content


class StashBot(Plugin):
    @classmethod
    def get_db_upgrade_table(cls) -> UpgradeTable:
        return upgrade_table

    async def _get(self, stash_name: str) -> dict[str, Any] | None:
        return await self.database.fetchrow(
            "SELECT normalized_key, content FROM stash_entries WHERE normalized_key=$1",
            stash_name.casefold(),
        )

    async def _create(self, stash_name: str, content: str) -> None:
        await self.database.execute(
            "INSERT INTO stash_entries (normalized_key, content) VALUES ($1, $2)",
            stash_name.casefold(),
            content,
        )

    async def _update(self, stash_name: str, content: str) -> None:
        await self.database.execute(
            "UPDATE stash_entries SET content=$1 WHERE normalized_key = $2",
            content,
            stash_name.casefold(),
        )

    async def _delete(self, stash_name: str) -> None:
        await self.database.execute(
            "DELETE FROM stash_entries WHERE normalized_key=$1", stash_name.casefold()
        )

    @command.new(name="stash", help="Store text or a replied-to message", must_consume_args=False)
    async def stash(self, evt: MessageEvent) -> None:
        parsed = parse_command(evt.content.body, "stash")
        if not parsed:
            await evt.reply("Usage: !stash <stash_name> [text], or reply to a message.")
            return

        cmd_prefix, stash_name, text = parsed

        parts: list[dict[str, Any]] = []
        if text:
            parts.append(
                {
                    "event_type": EventType.ROOM_MESSAGE.t,
                    "content": cleanup_event_content(evt, cmd_prefix),
                }
            )

        if reply_event_id := evt.content.get_reply_to():
            reply_event = await self.client.get_event(evt.room_id, reply_event_id)

            if not reply_event:
                await evt.reply("I couldn't decrypt the replied-to message.")
                return
            if not isinstance(reply_event, MautrixMessageEvent):
                await evt.reply("The replied-to event is not a message I can stash.")
                return

            msg_type = reply_event.content.msgtype
            if msg_type not in SUPPORTED_MESSAGE_TYPES:
                await evt.reply(f"Messages of type {msg_type} cannot be stashed.")
                return
            parts.append(
                {
                    "event_type": EventType.ROOM_MESSAGE.t,
                    "content": cleanup_event_content(reply_event),
                }
            )

        if not parts:
            await evt.reply("Add text after the stash_name or reply to a message to stash it.")
            return

        row = await self._get(stash_name)
        if not row:
            new_payload = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
            await self._create(stash_name, new_payload)
        else:
            old_payload = row["content"]
            existing_parts = json.loads(old_payload)
            combined_payload = json.dumps(
                [*existing_parts, *parts], ensure_ascii=False, separators=(",", ":")
            )
            await self._update(stash_name, combined_payload)

        await evt.reply(f"Stash entry {stash_name} updated.")

    @command.new(name="unstash", help="Send a stored message", must_consume_args=False)
    async def unstash(self, evt: MessageEvent) -> None:
        parsed = parse_command(evt.content.body, "unstash")
        if not parsed:
            await evt.reply("Usage: !unstash <stash_name>")
            return
        _, stash_name, _ = parsed

        row = await self._get(stash_name)
        if not row:
            await evt.reply(f'No stash named "{stash_name}" exists.')
            return

        parts = json.loads(row["content"])
        for part in parts:
            content = MessageEvent.deserialize_content(part["content"])
            await self.client.send_message_event(
                evt.room_id,
                EventType.find(part["event_type"], EventType.Class.MESSAGE),
                content,
            )

    @command.new(name="destash", help="Delete a stored message", must_consume_args=False)
    async def destash(self, evt: MessageEvent) -> None:
        parsed = parse_command(evt.content.body, "destash")
        if not parsed:
            await evt.reply("Usage: !destash <stash_name>")
            return

        _, stash_name, _ = parsed

        row = await self._get(stash_name)
        if not row:
            await evt.reply(f'Stash named "{stash_name}" doesn\'t exist.')
            return

        await self._delete(stash_name)
        await evt.reply(f'Stash named "{stash_name}" deleted.')


__all__ = ["StashBot"]
