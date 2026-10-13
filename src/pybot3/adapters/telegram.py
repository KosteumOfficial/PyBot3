from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import aiohttp

from ..context import Context
from ..exceptions import AuthenticationError, NetworkError, RateLimitError, UnsupportedFeatureError
from ..types import Attachment, Button, Chat, Keyboard, Message, User
from .base import BaseAdapter


class TelegramAdapter(BaseAdapter):
    platform = "telegram"

    def __init__(self, bot: Any, token: str | None = None, **kwargs: Any) -> None:
        super().__init__(bot, token, **kwargs)
        self.dry_run = bool(kwargs.get("dry_run", False))
        self.api_url = kwargs.get("api_url", "https://api.telegram.org")
        self.timeout = kwargs.get("timeout", 30)
        self.session = kwargs.get("session")
        self._owns_session = self.session is None
        self.offset = 0
        self._last_update = None

    def _mock_result(self, *, chat_id: str | int | None = None, message_id: int = 1, method: str | None = None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ok": True,
            "result": {
                "message_id": message_id,
                "chat": {"id": chat_id if chat_id is not None else 0},
                "date": 0,
                "text": payload.get("text") if payload else "",
            },
        }

    def normalize_event(self, native_event: dict[str, Any]) -> Context:
        return self._build_context(native_event)

    async def _request(self, method: str, payload: dict[str, Any] | None = None, *, files: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.session is None:
            self.session = aiohttp.ClientSession()
        url = f"{self.api_url}/bot{self.token}/{method}"
        try:
            if files:
                form = aiohttp.FormData()
                for key, value in (payload or {}).items():
                    if isinstance(value, (dict, list)):
                        form.add_field(key, json.dumps(value))
                    else:
                        form.add_field(key, str(value))
                for key, value in files.items():
                    form.add_field(key, value)
                async with self.session.post(url, data=form) as response:
                    data = await response.json(content_type=None)
            else:
                async with self.session.post(url, json=payload or {}) as response:
                    data = await response.json(content_type=None)
        except aiohttp.ClientError as exc:  # pragma: no cover - network safety
            raise NetworkError(f"Telegram API request failed for {method}.") from exc

        if not data.get("ok"):
            description = data.get("description", "Unknown Telegram API error")
            if data.get("error_code") == 429:
                raise RateLimitError(description)
            raise AuthenticationError(description)
        return data

    def _build_context(self, update: dict[str, Any]) -> Context:
        callback_query = update.get("callback_query")
        if callback_query:
            user = callback_query.get("from") or {}
            chat = callback_query.get("message", {}).get("chat") if callback_query.get("message") else {}
            msg = callback_query.get("message")
            message_obj = Message(
                id=msg.get("message_id") if msg else None,
                text=msg.get("text") if msg else None,
                chat=Chat(
                    id=chat.get("id"),
                    type=chat.get("type", "private"),
                    username=chat.get("username"),
                    title=chat.get("title"),
                ) if chat else None,
                from_user=User(
                    id=user.get("id"),
                    username=user.get("username"),
                    first_name=user.get("first_name"),
                    last_name=user.get("last_name"),
                    is_bot=user.get("is_bot", False),
                    language_code=user.get("language_code"),
                    extra=user,
                ) if user else None,
                native_event=update,
            )
            text = callback_query.get("data")
            return Context(
                bot=self.bot,
                platform=self.platform,
                native_event=update,
                user=User(
                    id=user.get("id"),
                    username=user.get("username"),
                    first_name=user.get("first_name"),
                    last_name=user.get("last_name"),
                    is_bot=user.get("is_bot", False),
                    language_code=user.get("language_code"),
                    extra=user,
                ) if user else None,
                chat=Chat(
                    id=chat.get("id"),
                    type=chat.get("type", "private"),
                    username=chat.get("username"),
                    title=chat.get("title"),
                ) if chat else None,
                text=text,
                message=message_obj,
                command=self._parse_command(text),
                args=self._parse_args(text),
                callback_data=callback_query.get("data"),
                callback_query_id=callback_query.get("id"),
                event_name="callback_query",
            )

        message = update.get("message") or update.get("edited_message") or update.get("channel_post")
        if not message:
            return Context(bot=self.bot, platform=self.platform, native_event=update, event_name="unknown")

        user = message.get("from") or {}
        chat = message.get("chat") or {}
        text = message.get("text") or message.get("caption")
        attachments = self._extract_attachments(message)
        user_obj = User(
            id=user.get("id"),
            username=user.get("username"),
            first_name=user.get("first_name"),
            last_name=user.get("last_name"),
            is_bot=user.get("is_bot", False),
            language_code=user.get("language_code"),
            extra=user,
        ) if user else None
        chat_obj = Chat(
            id=chat.get("id"),
            type=chat.get("type", "private"),
            username=chat.get("username"),
            title=chat.get("title"),
            extra=chat,
        ) if chat else None
        message_obj = Message(
            id=message.get("message_id"),
            text=text,
            chat=chat_obj,
            from_user=user_obj,
            attachments=attachments,
            native_event=message,
            extra=message,
        )
        return Context(
            bot=self.bot,
            platform=self.platform,
            native_event=update,
            user=user_obj,
            chat=chat_obj,
            text=text,
            message=message_obj,
            command=self._parse_command(text),
            args=self._parse_args(text),
            event_name="message",
        )

    def _extract_attachments(self, message: dict[str, Any]) -> list[Attachment]:
        attachments: list[Attachment] = []
        for key in ("photo", "video", "document", "audio", "voice"):
            value = message.get(key)
            if not value:
                continue
            if key == "photo":
                attachments.append(Attachment(kind="photo", file_id=str(value[-1].get("file_id")), extra=value))
            elif key == "video":
                attachments.append(Attachment(kind="video", file_id=str(value.get("file_id")), extra=value))
            else:
                attachments.append(Attachment(kind=key, file_id=str(value.get("file_id")), extra=value))
        return attachments

    @staticmethod
    def _parse_command(text: str | None) -> str | None:
        if not text:
            return None
        if not text.startswith("/"):
            return None
        return text.split()[0][1:]

    @staticmethod
    def _parse_args(text: str | None) -> list[str]:
        if not text:
            return []
        if not text.startswith("/"):
            return text.split()
        return text.split()[1:]

    def _reply_markup(self, keyboard: Keyboard | None) -> dict[str, Any] | None:
        if keyboard is None:
            return None
        inline_keyboard: list[list[dict[str, Any]]] = []
        for row in keyboard.buttons:
            inline_row: list[dict[str, Any]] = []
            for button in row:
                data: dict[str, Any] = {"text": button.text}
                if button.callback_data is not None:
                    data["callback_data"] = button.callback_data
                elif button.url is not None:
                    data["url"] = button.url
                inline_row.append(data)
            inline_keyboard.append(inline_row)
        return {"inline_keyboard": inline_keyboard}

    async def start(self) -> None:
        if self.dry_run:
            self.running = True
            return
        if not self.token:
            raise AuthenticationError("Telegram token is required.")
        self.running = True
        try:
            await self.get_me()
        except Exception:
            self.running = False
            if self._owns_session and self.session is not None:
                await self.session.close()
                self.session = None
            raise

    async def stop(self) -> None:
        self.running = False
        if self._owns_session and self.session is not None:
            await self.session.close()
            self.session = None

    async def get_me(self) -> dict[str, Any]:
        response = await self._request("getMe")
        return response.get("result", {})

    async def send_message(self, chat_id: str | int | None, text: str, *, keyboard: Keyboard | None = None, **kwargs: Any) -> dict[str, Any]:
        if chat_id is None:
            raise ValueError("Telegram chat_id is required.")
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if keyboard is not None:
            payload["reply_markup"] = self._reply_markup(keyboard)
        if self.dry_run:
            return self._mock_result(chat_id=chat_id, payload=payload).get("result", {})
        response = await self._request("sendMessage", payload)
        return response.get("result", {})

    async def send_photo(self, chat_id: str | int | None, file_path: str, *, caption: str | None = None, keyboard: Keyboard | None = None, **kwargs: Any) -> dict[str, Any]:
        if chat_id is None:
            raise ValueError("Telegram chat_id is required.")
        payload: dict[str, Any] = {"chat_id": chat_id}
        if caption:
            payload["caption"] = caption
        if keyboard is not None:
            payload["reply_markup"] = self._reply_markup(keyboard)
        if self.dry_run:
            return self._mock_result(chat_id=chat_id, payload=payload).get("result", {})
        file_name = Path(file_path).name if file_path else "upload.jpg"
        if file_path.startswith(("http://", "https://")):
            payload["photo"] = file_path
            response = await self._request("sendPhoto", payload)
            return response.get("result", {})
        with open(file_path, "rb") as photo_file:
            response = await self._request("sendPhoto", payload, files={"photo": photo_file})
        return response.get("result", {})

    async def edit_message(self, message_id: str | int | None, text: str, *, keyboard: Keyboard | None = None, **kwargs: Any) -> dict[str, Any]:
        if message_id is None:
            raise ValueError("Telegram message_id is required.")
        payload: dict[str, Any] = {"message_id": message_id, "text": text}
        if keyboard is not None:
            payload["reply_markup"] = self._reply_markup(keyboard)
        if self.dry_run:
            return self._mock_result(chat_id=kwargs.get("chat_id"), payload=payload).get("result", {})
        response = await self._request("editMessageText", payload)
        return response.get("result", {})

    async def delete_message(self, message_id: str | int | None, **kwargs: Any) -> dict[str, Any]:
        if message_id is None:
            raise ValueError("Telegram message_id is required.")
        if self.dry_run:
            return {"message_id": message_id, "deleted": True}
        response = await self._request("deleteMessage", {"message_id": message_id})
        return response.get("result", {})

    async def answer_callback_query(
        self,
        callback_query_id: str,
        *,
        text: str | None = None,
        show_alert: bool = False,
    ) -> None:
        if self.dry_run:
            return None
        payload: dict[str, Any] = {
            "callback_query_id": callback_query_id,
            "show_alert": show_alert,
        }
        if text is not None:
            payload["text"] = text
        await self._request("answerCallbackQuery", payload)

    async def run_polling(self) -> None:
        if self.dry_run:
            return None
        while self.running:
            response = await self._request("getUpdates", {"offset": self.offset, "timeout": self.timeout})
            for update in response.get("result", []):
                self.offset = max(self.offset, int(update.get("update_id", 0)) + 1)
                self._last_update = update
                await self.bot.dispatch(update)
            await asyncio.sleep(0.2)


__all__ = ["TelegramAdapter"]
