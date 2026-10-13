# PyBot3

PyBot3 is a modular asynchronous Python library for building bots on multiple platforms through a shared API.

## Features

- Unified bot core with routers, handlers, middleware, and filters
- Shared context object for platform-independent bot logic
- Built-in in-memory FSM state management
- Telegram adapter with long-polling support and dry-run mode for tests
- Extensible adapter system for Discord and WhatsApp
- Typed message and keyboard models
- Async-first design
- Lifecycle hooks, logging, configuration helpers, and multi-bot manager support

## Installation

```bash
pip install pybot3
```

## Basic example

```python
from pybot3 import Bot

bot = Bot(platform="telegram", token="YOUR_TELEGRAM_TOKEN")


@bot.command("start")
async def start(ctx):
    await ctx.reply("Hello from PyBot3!")


@bot.message()
async def echo(ctx):
    if ctx.text:
        await ctx.reply(f"You wrote: {ctx.text}")


async def main():
    await bot.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Multi-bot example

```python
from pybot3 import Bot, BotManager

manager = BotManager()
telegram_bot = manager.register(Bot(platform="telegram", token="TOKEN_TG"))
discord_bot = manager.register(Bot(platform="discord", token="TOKEN_DC"))

@telegram_bot.command("start")
async def start(ctx):
    await ctx.reply("Telegram is live")

@discord_bot.command("start")
async def discord_start(ctx):
    await ctx.reply("Discord is live")
```

## Lifecycle hooks

```python
from pybot3 import Bot

bot = Bot(platform="telegram", token="TOKEN")

@bot.lifecycle.on_start
async def startup(bot):
    print("Starting bot")

@bot.lifecycle.after_stop
async def shutdown(bot):
    print("Bot stopped")
```

## Supported adapters

- Telegram: implemented and tested for core message sending and polling flows
- Discord: adapter skeleton with HTTP-based send support
- WhatsApp Business: adapter scaffold for API integration

## Environment variables

Copy `.env.example` and set your secrets there.

## Barbershop booking bot

A complete sample Telegram bot is in [examples/barbershop_bot.py](examples/barbershop_bot.py). It accepts booking requests, stores them in SQLite, and lets Telegram users listed in `BARBERSHOP_ADMIN_USER_IDS` review and confirm/cancel them. Every admin command and callback checks the caller's Telegram user ID.

See [examples/BARBERSHOP.md](examples/BARBERSHOP.md) for setup and operation instructions. The sample uses PyBot3 `0.1.1` or later for callback-query acknowledgements.

## License

This project is licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later).

You may inspect, modify, and use it for private or internal development. If you distribute modified versions or run them as a network service, you must make the corresponding source code available under the same license.

This keeps the project open and prevents re-licensing it under a closed-source or misleading proprietary claim.

## Project status

This is a working first version of the library core. It is designed to be extended with additional adapters and features in future releases.
