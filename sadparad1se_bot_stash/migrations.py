from __future__ import annotations

from mautrix.util.async_db import Connection, UpgradeTable

upgrade_table = UpgradeTable()


@upgrade_table.register(description="Create global stash storage")
async def upgrade_v1(conn: Connection) -> None:
    await conn.execute(
        """
        CREATE TABLE stash_entries (
            normalized_key TEXT PRIMARY KEY,
            content        TEXT NOT NULL
        )
        """
    )
