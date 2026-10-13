from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


class Middleware:
    def __init__(self, func: Callable[[Any, Callable[[], Awaitable[Any]]], Awaitable[Any]]):
        self.func = func

    async def __call__(self, ctx: Any, call_next: Callable[[], Awaitable[Any]]) -> Any:
        return await self.func(ctx, call_next)


class MiddlewareStack:
    def __init__(self):
        self._middleware: list[Middleware] = []

    def add(self, middleware: Middleware) -> None:
        self._middleware.append(middleware)

    def wrap(self, handler: Callable[[Any], Awaitable[Any]]) -> Callable[[Any], Awaitable[Any]]:
        async def runner(ctx: Any) -> Any:
            async def call_next() -> Any:
                return await handler(ctx)

            for middleware in reversed(self._middleware):
                previous = call_next

                async def chain(current_middleware: Middleware = middleware, current_handler: Callable[[], Awaitable[Any]] = previous) -> Any:
                    return await current_middleware(ctx, current_handler)

                call_next = chain

            return await call_next()

        return runner

    def __iter__(self):
        return iter(self._middleware)


__all__ = ["Middleware", "MiddlewareStack"]
