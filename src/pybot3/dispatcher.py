from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .exceptions import HandlerError


class Dispatcher:
    def __init__(self):
        self.handlers: list[dict[str, Any]] = []
        self.middlewares: list[Callable[[Any, Callable[[], Any]], Any]] = []

    def add_handler(self, *, kind: str, func: Callable[..., Any], filters: tuple[Any, ...] = (), name: str | None = None, priority: int = 0, stop_propagation: bool = False):
        self.handlers.append(
            {
                "kind": kind,
                "func": func,
                "filters": filters,
                "name": name,
                "priority": priority,
                "stop_propagation": stop_propagation,
            }
        )

    def _matches(self, ctx: Any, filters: tuple[Any, ...]) -> bool:
        if not filters:
            return True
        for filter_ in filters:
            if callable(filter_):
                if not filter_(ctx):
                    return False
            elif not bool(filter_):
                return False
        return True

    async def _run_handlers(self, ctx: Any) -> None:
        handlers = sorted(self.handlers, key=lambda item: item["priority"], reverse=True)
        for item in handlers:
            if item["kind"] == "message" and not getattr(ctx, "text", None) and not getattr(ctx, "message", None):
                continue
            if item["kind"] == "command" and getattr(ctx, "command", None) != item["name"]:
                continue
            if item["kind"] == "callback" and not getattr(ctx, "callback_data", None):
                continue
            if item["kind"] == "event" and getattr(ctx, "event_name", None) != item["name"]:
                continue
            if not self._matches(ctx, item["filters"]):
                continue
            try:
                result = item["func"](ctx)
                if hasattr(result, "__await__"):
                    await result
            except Exception as exc:  # pragma: no cover - safety net
                raise HandlerError(f"Handler '{item['name'] or item['func'].__name__}' failed") from exc
            if item["stop_propagation"]:
                break

    async def dispatch(self, ctx: Any) -> None:
        async def call_next() -> None:
            await self._run_handlers(ctx)

        for middleware in reversed(self.middlewares):
            previous = call_next

            async def chain(current_middleware=middleware, current_handler=previous) -> None:
                result = current_middleware(ctx, current_handler)
                if hasattr(result, "__await__"):
                    await result

            call_next = chain

        await call_next()


__all__ = ["Dispatcher"]
