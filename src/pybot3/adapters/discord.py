from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from ..exceptions import AuthenticationError, UnsupportedFeatureError
from .base import BaseAdapter


class DiscordAdapter(BaseAdapter):
    platform = "discord"

    def __init__(self, bot: Any, token: str | None = None, **kwargs: Any) -> None:
        super().__init__(bot, token, **kwargs)
        self.base_url = "https://discord.com/api/v10"
        self.session = kwargs.get("session")

    async def start(self) -> None:
        if not self.token:
            raise AuthenticationError("Discord token is required.")
        self.running = True

    async def stop(self) -> None:
        self.running = False

    async def run_polling(self) -> None:
        if self.kwargs.get("dry_run") or getattr(self, "dry_run", False):
            return None
        while self.running:
            await asyncio.sleep(1)

    async def send_message(self, chat_id: str | int | None, text: str, *, keyboard=None, **kwargs: Any) -> Any:
        if not chat_id:
            raise ValueError("Discord message requires a channel_id.")
        if self.session is None:
            self.session = aiohttp.ClientSession()
        headers = {"Authorization": f"Bot {self.token}", "Content-Type": "application/json"}
        payload = {"content": text}
        if keyboard is not None:
            payload["components"] = [{"type": 1, "components": [{"type": 2, "label": button.text, "custom_id": button.callback_data or button.text, "url": button.url} for row in keyboard.buttons for button in row]}]
        async with self.session.post(f"{self.base_url}/channels/{chat_id}/messages", headers=headers, json=payload) as response:
            if response.status >= 400:
                raise UnsupportedFeatureError(f"Discord API request failed with status {response.status}.")
            return await response.json()

    async def send_photo(self, chat_id: str | int | None, file_path: str, *, caption: str | None = None, keyboard=None, **kwargs: Any) -> Any:
        raise UnsupportedFeatureError("Discord photo support is not implemented in this adapter version.")

    async def edit_message(self, message_id: str | int | None, text: str, *, keyboard=None, **kwargs: Any) -> Any:
        raise UnsupportedFeatureError("Discord message editing is not implemented in this adapter version.")

    async def delete_message(self, message_id: str | int | None, **kwargs: Any) -> Any:
        raise UnsupportedFeatureError("Discord message deletion is not implemented in this adapter version.")
