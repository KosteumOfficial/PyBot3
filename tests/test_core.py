import asyncio

import pytest

from pybot3 import Bot, Router, filters
from pybot3.fsm import FSM
from pybot3.types import Button, Keyboard


@pytest.mark.asyncio
async def test_bot_command_registration_and_execution():
    bot = Bot(platform="telegram", token="abc", dry_run=True)
    seen = []

    @bot.command("start")
    async def start(ctx):
        seen.append(ctx.command)
        await ctx.reply("Hello")

    update = {
        "update_id": 1,
        "message": {
            "message_id": 2,
            "text": "/start",
            "chat": {"id": 42, "type": "private", "username": "alice"},
            "from": {"id": 7, "username": "alice", "first_name": "Alice", "is_bot": False},
        },
    }

    await bot.dispatch(update)
    assert seen == ["start"]


@pytest.mark.asyncio
async def test_router_inclusion_and_filter_match():
    bot = Bot(platform="telegram", token="abc", dry_run=True)
    router = Router()
    seen = []

    @router.command("help")
    async def help_handler(ctx):
        seen.append(ctx.command)

    bot.include_router(router)
    update = {
        "update_id": 2,
        "message": {
            "message_id": 3,
            "text": "/help",
            "chat": {"id": 11, "type": "private"},
            "from": {"id": 11, "username": "bob", "first_name": "Bob", "is_bot": False},
        },
    }

    await bot.dispatch(update)
    assert seen == ["help"]


def test_filters_work_on_context():
    ctx = type("Ctx", (), {"text": "/ping now", "command": "ping", "user": type("User", (), {"id": 99})(), "chat": type("Chat", (), {"id": 5})()})()
    assert filters.command("ping")(ctx)
    assert filters.regex(r"ping")(ctx)


def test_fsm_transitions():
    fsm = FSM()
    assert fsm.get("user-1").state == "idle"
    fsm.set_state("user-1", "awaiting_name")
    assert fsm.get("user-1").state == "awaiting_name"
    fsm.update_data("user-1", name="Alice")
    assert fsm.get("user-1").data["name"] == "Alice"


def test_telegram_reply_markup_serialization():
    keyboard = Keyboard(buttons=[[Button("Profile", callback_data="profile"), Button("Help", callback_data="help")]])
    markup = Bot(platform="telegram", token="abc", dry_run=True).adapter._reply_markup(keyboard)
    assert markup["inline_keyboard"][0][0]["callback_data"] == "profile"
    assert markup["inline_keyboard"][0][1]["callback_data"] == "help"


@pytest.mark.asyncio
async def test_callback_context_can_acknowledge_telegram_callback():
    bot = Bot(platform="telegram", token="abc", dry_run=True)
    ctx = bot.adapter.normalize_event(
        {
            "callback_query": {
                "id": "callback-123",
                "from": {"id": 7},
                "data": "book:start",
                "message": {
                    "message_id": 1,
                    "chat": {"id": 7, "type": "private"},
                },
            }
        }
    )
    calls = []

    async def record_request(method, payload=None, **kwargs):
        calls.append((method, payload))
        return {"ok": True}

    bot.adapter._request = record_request
    bot.adapter.dry_run = False

    await ctx.answer_callback("Done")

    assert calls == [
        (
            "answerCallbackQuery",
            {
                "callback_query_id": "callback-123",
                "show_alert": False,
                "text": "Done",
            },
        )
    ]
