# bot-stash

A [maubot](https://github.com/maubot/maubot) plugin that stores Matrix messages under aliases.

## Commands

Keys are case-insensitive, global to the plugin instance, and shared by every user and room that can access the bot.

### Create or append the stash entry

Store text:

```text
!stash <alias> [text]
```

Store a message by replying to it with:

```text
!stash <alias> [optional text]
```

### Show stash entry

Retrieve or delete the entry:

```text
!unstash <alias>
```

### Delete stash entry

```text
!destash <alias>
```

---

## Build and install

The plugin requires maubot 0.6.0 or later.

For development, install [uv](https://docs.astral.sh/uv/) and run:

```sh
uv run pytest
uv run ruff check .
uv run ruff format .
uv run mbc build
```
