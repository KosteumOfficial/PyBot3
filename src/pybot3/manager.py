from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


class BotManager:
    def __init__(self) -> None:
        self.bots: list[Any] = []

    def register(self, bot: Any) -> Any:
        self.bots.append(bot)
        return bot

    def unregister(self, bot: Any) -> None:
        self.bots = [item for item in self.bots if item is not bot]

    async def run_all(self) -> None:
        for bot in self.bots:
            await bot.run()

    async def stop_all(self) -> None:
        for bot in reversed(self.bots):
            await bot.stop()


__all__ = ["BotManager"]
