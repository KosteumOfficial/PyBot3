from __future__ import annotations

from typing import Any


class BaseAdapter:
    platform = "base"

    def __init__(self, bot: Any, token: str | None = None, **kwargs: Any) -> None:
        self.bot = bot
        self.token = token
        self.kwargs = kwargs
        self.running = False

    async def start(self) -> None:
        self.running = True

    async def stop(self) -> None:
        self.running = False

    async def run_polling(self) -> None:
        return None

    def normalize_event(self, native_event: Any) -> Any:
        return native_event

    async def send_message(self, chat_id: str | int | None, text: str, *, keyboard=None, **kwargs: Any) -> Any:
        raise NotImplementedError

    async def send_photo(self, chat_id: str | int | None, file_path: str, *, caption: str | None = None, keyboard=None, **kwargs: Any) -> Any:
        raise NotImplementedError

    async def edit_message(self, message_id: str | int | None, text: str, *, keyboard=None, **kwargs: Any) -> Any:
        raise NotImplementedError

    async def delete_message(self, message_id: str | int | None, **kwargs: Any) -> Any:
        raise NotImplementedError
