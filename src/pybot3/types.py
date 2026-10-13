from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass
class User:
    id: int | str
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_bot: bool = False
    language_code: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chat:
    id: int | str
    type: str = "private"
    title: str | None = None
    username: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Button:
    text: str
    callback_data: str | None = None
    url: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class Keyboard:
    buttons: list[list[Button]] = field(default_factory=list)


@dataclass
class Attachment:
    kind: str
    file_id: str | None = None
    url: str | None = None
    caption: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    id: int | str | None = None
    text: str | None = None
    chat: Chat | None = None
    from_user: User | None = None
    attachments: list[Attachment] = field(default_factory=list)
    native_event: Any = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class CallbackQuery:
    id: str | None = None
    from_user: User | None = None
    chat: Chat | None = None
    message: Message | None = None
    data: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "User",
    "Chat",
    "Button",
    "Keyboard",
    "Attachment",
    "Message",
    "CallbackQuery",
]
