from __future__ import annotations

from typing import Any

from .types import Button, Keyboard, Message


class Context:
    def __init__(
        self,
        *,
        bot: Any,
        platform: str,
        native_event: Any = None,
        user: Any = None,
        chat: Any = None,
        text: str | None = None,
        message: Message | None = None,
        command: str | None = None,
        args: list[str] | None = None,
        callback_data: str | None = None,
        callback_query_id: str | None = None,
        event_name: str | None = None,
    ) -> None:
        self.bot = bot
        self.platform = platform
        self.native_event = native_event
        self.user = user
        self.chat = chat
        self.text = text
        self.message = message
        self.command = command
        self.args = args or []
        self.callback_data = callback_data
        self.callback_query_id = callback_query_id
        self.event_name = event_name

    @property
    def sender(self):
        return self.user

    async def reply(self, text: str | None = None, *, keyboard: Keyboard | None = None, photo: str | None = None, **kwargs):
        if photo is not None:
            return await self.bot.adapter.send_photo(self.chat.id if self.chat else None, photo, caption=text, keyboard=keyboard, **kwargs)
        return await self.bot.adapter.send_message(self.chat.id if self.chat else None, text or self.text or "", keyboard=keyboard, **kwargs)

    async def send(self, text: str, *, keyboard: Keyboard | None = None, **kwargs):
        return await self.bot.adapter.send_message(self.chat.id if self.chat else None, text, keyboard=keyboard, **kwargs)

    async def edit(self, text: str, *, keyboard: Keyboard | None = None, **kwargs):
        return await self.bot.adapter.edit_message(self.message.id if self.message else None, text, keyboard=keyboard, **kwargs)

    async def delete(self, **kwargs):
        return await self.bot.adapter.delete_message(self.message.id if self.message else None, **kwargs)

    async def reply_photo(self, path: str, *, caption: str | None = None, keyboard: Keyboard | None = None, **kwargs):
        return await self.bot.adapter.send_photo(self.chat.id if self.chat else None, path, caption=caption, keyboard=keyboard, **kwargs)

    async def answer_callback(self, text: str | None = None, *, show_alert: bool = False) -> None:
        if not self.callback_query_id:
            return
        await self.bot.adapter.answer_callback_query(
            self.callback_query_id,
            text=text,
            show_alert=show_alert,
        )

    def __repr__(self) -> str:
        return f"Context(platform={self.platform!r}, command={self.command!r}, text={self.text!r})"


__all__ = ["Context"]
