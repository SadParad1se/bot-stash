from __future__ import annotations

import pytest

from sadparad1se_bot_stash import StashBot
from sadparad1se_bot_stash.migrations import upgrade_table

pytest_plugins = ["maubot.testing.fixtures"]


@pytest.fixture
def maubot_plugin_class():
    return StashBot


@pytest.fixture
def maubot_upgrade_table():
    return upgrade_table


@pytest.fixture
def maubot_plugin_config():
    return None
