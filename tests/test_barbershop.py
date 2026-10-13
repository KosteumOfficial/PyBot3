from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from pybot3 import Bot
from examples.barbershop_bot import (
    BookingStore,
    SERVICES,
    build_bot,
    parse_admin_ids,
)


def test_booking_store_prevents_overlapping_pending_appointments(tmp_path):
    store = BookingStore(tmp_path / "appointments.sqlite3")
    appointment_date = date(2026, 10, 20)

    first_id = store.create_booking(
        user_id=1,
        chat_id=1,
        customer_name="Олена",
        phone="+380671234567",
        service=SERVICES[0],
        appointment_date=appointment_date,
        start_minute=600,
    )
    conflicting_id = store.create_booking(
        user_id=2,
        chat_id=2,
        customer_name="Іван",
        phone="+380671234568",
        service=SERVICES[2],
        appointment_date=appointment_date,
        start_minute=630,
    )

    assert first_id is not None
    assert conflicting_id is None
    assert store.update_status(first_id, "cancelled")
    assert store.is_available(appointment_date, 630, SERVICES[2].duration_minutes)
    store.close()


def test_admin_ids_require_numeric_telegram_ids():
    assert parse_admin_ids("12, 34") == frozenset({12, 34})
    with pytest.raises(ValueError, match="numeric Telegram user IDs"):
        parse_admin_ids("admin")


def callback_update(user_id: int, data: str, *, chat_type: str = "private") -> dict:
    return {
        "update_id": user_id,
        "callback_query": {
            "id": f"query-{user_id}-{data}",
            "from": {"id": user_id, "first_name": "Test"},
            "data": data,
            "message": {
                "message_id": 1,
                "text": "menu",
                "chat": {"id": user_id, "type": chat_type},
            },
        },
    }


def message_update(user_id: int, text: str) -> dict:
    return {
        "update_id": user_id,
        "message": {
            "message_id": 2,
            "text": text,
            "chat": {"id": user_id, "type": "private"},
            "from": {"id": user_id, "first_name": "Test"},
        },
    }


@pytest.mark.asyncio
async def test_booking_flow_and_admin_id_access(tmp_path):
    store = BookingStore(tmp_path / "appointments.sqlite3")
    adapter = Bot(platform="telegram", token="test", dry_run=True).adapter
    bot = build_bot(
        token="test",
        admin_ids=frozenset({900}),
        store=store,
        shop_name="Test Shop",
        timezone=ZoneInfo("Europe/Kyiv"),
        adapter=adapter,
    )

    customer_id = 55
    await bot.dispatch(callback_update(customer_id, "book:start"))
    await bot.dispatch(callback_update(customer_id, "book:service:cut"))
    appointment_date = datetime.now(ZoneInfo("Europe/Kyiv")).date() + timedelta(days=1)
    while appointment_date.weekday() == 6:
        appointment_date += timedelta(days=1)
    await bot.dispatch(
        callback_update(customer_id, f"book:date:{appointment_date.isoformat()}")
    )
    await bot.dispatch(callback_update(customer_id, "book:time:600"))
    await bot.dispatch(message_update(customer_id, "Тестовий клієнт"))
    await bot.dispatch(message_update(customer_id, "+380671234567"))

    bookings = store.list_bookings(statuses=("pending",), since=appointment_date)
    assert len(bookings) == 1
    booking_id = int(bookings[0]["id"])

    await bot.dispatch(callback_update(777, f"admin:confirm:{booking_id}"))
    assert store.get_booking(booking_id)["status"] == "pending"

    await bot.dispatch(callback_update(900, f"admin:confirm:{booking_id}"))
    assert store.get_booking(booking_id)["status"] == "confirmed"
    store.close()


@pytest.mark.asyncio
async def test_booking_flow_rejects_group_chat(tmp_path):
    store = BookingStore(tmp_path / "appointments.sqlite3")
    adapter = Bot(platform="telegram", token="test", dry_run=True).adapter
    bot = build_bot(
        token="test",
        admin_ids=frozenset({900}),
        store=store,
        shop_name="Test Shop",
        timezone=ZoneInfo("Europe/Kyiv"),
        adapter=adapter,
    )

    customer_id = 55
    await bot.dispatch(
        callback_update(customer_id, "book:service:cut", chat_type="group")
    )
    appointment_date = datetime.now(ZoneInfo("Europe/Kyiv")).date() + timedelta(days=1)
    while appointment_date.weekday() == 6:
        appointment_date += timedelta(days=1)
    await bot.dispatch(
        callback_update(customer_id, f"book:date:{appointment_date.isoformat()}")
    )
    await bot.dispatch(callback_update(customer_id, "book:time:600"))
    await bot.dispatch(message_update(customer_id, "Тестовий клієнт"))
    await bot.dispatch(message_update(customer_id, "+380671234567"))

    assert store.list_bookings(statuses=("pending",), since=appointment_date) == []
    store.close()
