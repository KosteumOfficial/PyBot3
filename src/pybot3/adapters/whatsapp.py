from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from ..exceptions import AuthenticationError, UnsupportedFeatureError
from .base import BaseAdapter


class WhatsAppAdapter(BaseAdapter):
    platform = "whatsapp"

    def __init__(self, bot: Any, token: str | None = None, **kwargs: Any) -> None:
        super().__init__(bot, token, **kwargs)
        self.phone_number_id = kwargs.get("phone_number_id")
        self.base_url = "https://graph.facebook.com/v20.0"
        self.session = kwargs.get("session")

    async def start(self) -> None:
        if not self.token:
            raise AuthenticationError("WhatsApp bearer token is required.")
        if not self.phone_number_id:
            raise AuthenticationError("WhatsApp phone_number_id is required.")
        self.running = True

    async def stop(self) -> None:
        self.running = False

    async def run_polling(self) -> None:
        if self.kwargs.get("dry_run") or getattr(self, "dry_run", False):
            return None
        while self.running:
            await asyncio.sleep(1)

    async def send_message(self, chat_id: str | int | None, text: str, *, keyboard=None, **kwargs: Any) -> Any:
        if not self.phone_number_id:
            raise AuthenticationError("WhatsApp requires a phone_number_id to send messages.")
        if self.session is None:
            self.session = aiohttp.ClientSession()
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        payload = {
            "messaging_product": "whatsapp",
            "to": str(chat_id),
            "type": "text",
            "text": {"body": text},
        }
        async with self.session.post(f"{self.base_url}/{self.phone_number_id}/messages", headers=headers, json=payload) as response:
            if response.status >= 400:
                raise UnsupportedFeatureError(f"WhatsApp API request failed with status {response.status}.")
            return await response.json()

    async def send_photo(self, chat_id: str | int | None, file_path: str, *, caption: str | None = None, keyboard=None, **kwargs: Any) -> Any:
        raise UnsupportedFeatureError("WhatsApp media sending requires additional business platform configuration and is not implemented in this version.")

    async def edit_message(self, message_id: str | int | None, text: str, *, keyboard=None, **kwargs: Any) -> Any:
        raise UnsupportedFeatureError("WhatsApp message editing is not supported by the platform API.")

    async def delete_message(self, message_id: str | int | None, **kwargs: Any) -> Any:
        raise UnsupportedFeatureError("WhatsApp message deletion is not supported by the platform API.")
