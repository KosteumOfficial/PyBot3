import asyncio

from pybot3 import Bot, filters

bot = Bot(platform="telegram", token="YOUR_TELEGRAM_TOKEN", dry_run=True)


@bot.command("start")
async def start(ctx):
    await ctx.reply("Hello! This bot is running on PyBot3.")


@bot.message(filters.text)
async def echo(ctx):
    if ctx.text:
        await ctx.reply(f"You wrote: {ctx.text}")


async def main() -> None:
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
