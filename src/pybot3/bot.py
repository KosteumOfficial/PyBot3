from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .adapters.discord import DiscordAdapter
from .adapters.telegram import TelegramAdapter
from .adapters.whatsapp import WhatsAppAdapter
from .dispatcher import Dispatcher
from .exceptions import InvalidConfigurationError, UnsupportedFeatureError
from .fsm import FSM
from .lifecycle import Lifecycle
from .logging import get_logger
from .router import Router


class Bot:
    def __init__(
        self,
        *,
        platform: str,
        token: str | None = None,
        adapter: Any | None = None,
        name: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.platform = platform.lower()
        self.token = token
        self.name = name or f"{self.platform}-bot"
        self.dry_run = bool(kwargs.pop("dry_run", False))
        self.kwargs = kwargs
        self.logger = kwargs.pop("logger", get_logger(self.name))
        self.dispatcher = Dispatcher()
        self.router = Router()
        self.fsm = FSM()
        self.lifecycle = Lifecycle()
        self.adapter = adapter or self._create_adapter()
        self._running = False

    def _create_adapter(self) -> Any:
        if self.platform == "telegram":
            return TelegramAdapter(self, token=self.token, dry_run=self.dry_run, **self.kwargs)
        if self.platform == "discord":
            return DiscordAdapter(self, token=self.token, dry_run=self.dry_run, **self.kwargs)
        if self.platform == "whatsapp":
            return WhatsAppAdapter(self, token=self.token, dry_run=self.dry_run, **self.kwargs)
        raise InvalidConfigurationError(f"Unsupported platform '{self.platform}'.")

    def command(self, name: str | None = None, *filters: Any, priority: int = 0, stop_propagation: bool = False):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.dispatcher.add_handler(
                kind="command",
                func=func,
                filters=filters,
                name=name or func.__name__,
                priority=priority,
                stop_propagation=stop_propagation,
            )
            return func

        return decorator

    def message(self, *filters: Any, priority: int = 0, stop_propagation: bool = False):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.dispatcher.add_handler(
                kind="message",
                func=func,
                filters=filters,
                priority=priority,
                stop_propagation=stop_propagation,
            )
            return func

        return decorator

    def event(self, name: str, *filters: Any, priority: int = 0, stop_propagation: bool = False):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.dispatcher.add_handler(
                kind="event",
                func=func,
                filters=filters,
                name=name,
                priority=priority,
                stop_propagation=stop_propagation,
            )
            return func

        return decorator

    def callback(self, *filters: Any, priority: int = 0, stop_propagation: bool = False):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.dispatcher.add_handler(
                kind="callback",
                func=func,
                filters=filters,
                priority=priority,
                stop_propagation=stop_propagation,
            )
            return func

        return decorator

    def middleware(self):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.dispatcher.middlewares.append(func)
            return func

        return decorator

    def include_router(self, router: Router) -> None:
        for handler in router.handlers:
            self.dispatcher.add_handler(
                kind=handler.kind,
                func=handler.func,
                filters=handler.filters,
                name=handler.name,
                priority=handler.priority,
                stop_propagation=handler.stop_propagation,
            )

    async def dispatch(self, native_event: Any) -> None:
        if hasattr(self.adapter, "normalize_event"):
            context = self.adapter.normalize_event(native_event)
        else:
            context = native_event
        if context is None:
            return
        if hasattr(context, "bot"):
            context.bot = self
        self.logger.debug("Dispatching event for platform=%s", self.platform)
        await self.dispatcher.dispatch(context)

    async def run(self) -> None:
        if self._running:
            return
        self._running = True
        self.logger.info("Starting bot %s on %s", self.name, self.platform)
        try:
            await self.lifecycle.trigger_start(self)
            await self.adapter.start()
            await self.adapter.run_polling()
        finally:
            if self._running:
                await self.stop()

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self.logger.info("Stopping bot %s on %s", self.name, self.platform)
        await self.lifecycle.trigger_stop(self)
        await self.adapter.stop()

    async def __aenter__(self) -> "Bot":
        await self.run()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()

    async def close(self) -> None:
        await self.stop()


__all__ = ["Bot"]
