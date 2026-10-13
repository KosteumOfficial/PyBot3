import pytest

from pybot3 import Bot, BotManager, Lifecycle, Settings


@pytest.mark.asyncio
async def test_lifecycle_hooks_fire():
    bot = Bot(platform="telegram", token="abc", dry_run=True)
    events = []

    @bot.lifecycle.on_start
    async def startup(current):
        events.append(("start", current.name))

    @bot.lifecycle.after_stop
    async def shutdown(current):
        events.append(("stop", current.name))

    await bot.run()
    await bot.stop()
    assert events == [("start", bot.name), ("stop", bot.name)]


def test_settings_from_env():
    settings = Settings.from_env("PYBOT3_TEST")
    assert settings.platform is None
    assert settings.log_level == "INFO"


def test_manager_registers_and_stops_bots():
    manager = BotManager()
    bot = Bot(platform="telegram", token="abc", dry_run=True)
    manager.register(bot)
    assert manager.bots == [bot]
