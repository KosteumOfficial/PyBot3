from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


class Lifecycle:
    def __init__(self) -> None:
        self._before_start: list[Callable[[Any], Awaitable[Any] | Any]] = []
        self._after_start: list[Callable[[Any], Awaitable[Any] | Any]] = []
        self._before_stop: list[Callable[[Any], Awaitable[Any] | Any]] = []
        self._after_stop: list[Callable[[Any], Awaitable[Any] | Any]] = []

    def on_start(self, func: Callable[[Any], Awaitable[Any] | Any]) -> Callable[[Any], Awaitable[Any] | Any]:
        self._before_start.append(func)
        return func

    def after_start(self, func: Callable[[Any], Awaitable[Any] | Any]) -> Callable[[Any], Awaitable[Any] | Any]:
        self._after_start.append(func)
        return func

    def on_stop(self, func: Callable[[Any], Awaitable[Any] | Any]) -> Callable[[Any], Awaitable[Any] | Any]:
        self._before_stop.append(func)
        return func

    def after_stop(self, func: Callable[[Any], Awaitable[Any] | Any]) -> Callable[[Any], Awaitable[Any] | Any]:
        self._after_stop.append(func)
        return func

    async def trigger_start(self, bot: Any) -> None:
        for hook in self._before_start:
            result = hook(bot)
            if hasattr(result, "__await__"):
                await result
        for hook in self._after_start:
            result = hook(bot)
            if hasattr(result, "__await__"):
                await result

    async def trigger_stop(self, bot: Any) -> None:
        for hook in self._before_stop:
            result = hook(bot)
            if hasattr(result, "__await__"):
                await result
        for hook in self._after_stop:
            result = hook(bot)
            if hasattr(result, "__await__"):
                await result


__all__ = ["Lifecycle"]
