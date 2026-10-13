from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Filter:
    predicate: Callable[[Any], bool]

    def __call__(self, ctx: Any) -> bool:
        return bool(self.predicate(ctx))

    def __and__(self, other: "Filter") -> "Filter":
        return Filter(lambda ctx: bool(self(ctx)) and bool(other(ctx)))

    def __or__(self, other: "Filter") -> "Filter":
        return Filter(lambda ctx: bool(self(ctx)) or bool(other(ctx)))

    def __invert__(self) -> "Filter":
        return Filter(lambda ctx: not bool(self(ctx)))


class _FilterFactory:
    @staticmethod
    def text(ctx: Any) -> bool:
        return bool(getattr(ctx, "text", None))

    @staticmethod
    def command(name: str | None = None):
        return Filter(lambda ctx: bool(ctx.command and (name is None or ctx.command == name)))

    @staticmethod
    def regex(pattern: str):
        return Filter(lambda ctx: bool(ctx.text is not None and re.search(pattern, ctx.text)))

    @staticmethod
    def user(user_id: int | str):
        return Filter(lambda ctx: getattr(ctx.user, "id", None) == user_id)

    @staticmethod
    def chat(chat_id: int | str):
        return Filter(lambda ctx: getattr(ctx.chat, "id", None) == chat_id)

    @staticmethod
    def photo(ctx: Any) -> bool:
        return any(a.kind == "photo" for a in getattr(ctx.message, "attachments", []))

    @staticmethod
    def video(ctx: Any) -> bool:
        return any(a.kind == "video" for a in getattr(ctx.message, "attachments", []))

    @staticmethod
    def document(ctx: Any) -> bool:
        return any(a.kind == "document" for a in getattr(ctx.message, "attachments", []))

    @staticmethod
    def callback_data(value: str | None = None):
        return Filter(lambda ctx: bool(ctx.callback_data and (value is None or ctx.callback_data == value)))

    @staticmethod
    def custom(predicate: Callable[[Any], bool]):
        return Filter(predicate)


filters = _FilterFactory()

__all__ = ["Filter", "filters"]
