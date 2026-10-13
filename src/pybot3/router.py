from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class HandlerRecord:
    name: str | None
    kind: str
    func: Callable[..., Any]
    filters: tuple[Any, ...] = ()
    priority: int = 0
    stop_propagation: bool = False


class Router:
    def __init__(self):
        self.handlers: list[HandlerRecord] = []

    def _register(
        self,
        kind: str,
        func: Callable[..., Any],
        *,
        name: str | None = None,
        filters: tuple[Any, ...] = (),
        priority: int = 0,
        stop_propagation: bool = False,
    ) -> Callable[..., Any]:
        self.handlers.append(
            HandlerRecord(
                name=name or getattr(func, "__name__", None),
                kind=kind,
                func=func,
                filters=filters,
                priority=priority,
                stop_propagation=stop_propagation,
            )
        )
        return func

    def command(self, name: str | None = None, *filters: Any, priority: int = 0, stop_propagation: bool = False):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._register("command", func, name=name or func.__name__, filters=filters, priority=priority, stop_propagation=stop_propagation)
            return func

        return decorator

    def message(self, *filters: Any, priority: int = 0, stop_propagation: bool = False):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._register("message", func, filters=filters, priority=priority, stop_propagation=stop_propagation)
            return func

        return decorator

    def event(self, name: str, *filters: Any, priority: int = 0, stop_propagation: bool = False):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._register("event", func, name=name, filters=filters, priority=priority, stop_propagation=stop_propagation)
            return func

        return decorator

    def callback(self, *filters: Any, priority: int = 0, stop_propagation: bool = False):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._register("callback", func, filters=filters, priority=priority, stop_propagation=stop_propagation)
            return func

        return decorator


__all__ = ["Router", "HandlerRecord"]
