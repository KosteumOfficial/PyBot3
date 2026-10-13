from __future__ import annotations

import asyncio
import logging
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

from pybot3 import Bot, Button, Keyboard, filters


@dataclass(frozen=True)
class Service:
    id: str
    name: str
    price: int
    duration_minutes: int


SERVICES = (
    Service("cut", "Чоловіча стрижка", 400, 45),
    Service("combo", "Стрижка + борода", 600, 60),
    Service("beard", "Оформлення бороди", 300, 30),
)
SLOT_STEP_MINUTES = 30
PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9 ()-]*$")
LOGGER = logging.getLogger("barbershop")


@dataclass
class BookingDraft:
    service: Service
    appointment_date: date | None = None
    start_minute: int | None = None
    customer_name: str | None = None


class BookingStore:
    def __init__(self, database_path: str | Path = "barbershop.sqlite3") -> None:
        self.connection = sqlite3.connect(database_path, timeout=10, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                customer_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                service_id TEXT NOT NULL,
                service_name TEXT NOT NULL,
                price INTEGER NOT NULL,
                duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
                appointment_date TEXT NOT NULL,
                start_minute INTEGER NOT NULL CHECK (start_minute >= 0 AND start_minute < 1440),
                status TEXT NOT NULL CHECK (status IN ('pending', 'confirmed', 'cancelled')),
                created_at TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS bookings_date_status
            ON bookings (appointment_date, status, start_minute)
            """
        )

    def is_available(
        self,
        appointment_date: date,
        start_minute: int,
        duration_minutes: int,
    ) -> bool:
        row = self.connection.execute(
            """
            SELECT 1
            FROM bookings
            WHERE appointment_date = ?
              AND status IN ('pending', 'confirmed')
              AND start_minute < ?
              AND start_minute + duration_minutes > ?
            LIMIT 1
            """,
            (
                appointment_date.isoformat(),
                start_minute + duration_minutes,
                start_minute,
            ),
        ).fetchone()
        return row is None

    def create_booking(
        self,
        *,
        user_id: int,
        chat_id: int,
        customer_name: str,
        phone: str,
        service: Service,
        appointment_date: date,
        start_minute: int,
    ) -> int | None:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            if not self.is_available(
                appointment_date,
                start_minute,
                service.duration_minutes,
            ):
                self.connection.execute("ROLLBACK")
                return None
            cursor = self.connection.execute(
                """
                INSERT INTO bookings (
                    user_id, chat_id, customer_name, phone, service_id,
                    service_name, price, duration_minutes, appointment_date,
                    start_minute, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    user_id,
                    chat_id,
                    customer_name,
                    phone,
                    service.id,
                    service.name,
                    service.price,
                    service.duration_minutes,
                    appointment_date.isoformat(),
                    start_minute,
                    datetime.now().astimezone().isoformat(timespec="seconds"),
                ),
            )
            booking_id = int(cursor.lastrowid)
            self.connection.execute("COMMIT")
            return booking_id
        except Exception:
            self.connection.execute("ROLLBACK")
            raise

    def get_booking(self, booking_id: int) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM bookings WHERE id = ?", (booking_id,)
        ).fetchone()

    def list_bookings(self, *, statuses: tuple[str, ...], since: date) -> list[sqlite3.Row]:
        if not statuses:
            return []
        placeholders = ",".join("?" for _ in statuses)
        return list(
            self.connection.execute(
                f"""
                SELECT * FROM bookings
                WHERE status IN ({placeholders}) AND appointment_date >= ?
                ORDER BY appointment_date, start_minute
                LIMIT 20
                """,
                (*statuses, since.isoformat()),
            ).fetchall()
        )

    def update_status(self, booking_id: int, status: str) -> bool:
        if status not in {"confirmed", "cancelled"}:
            raise ValueError(f"Unsupported booking status: {status}")
        cursor = self.connection.execute(
            """
            UPDATE bookings SET status = ?
            WHERE id = ? AND status = 'pending'
            """,
            (status, booking_id),
        )
        return cursor.rowcount == 1

    def list_user_bookings(self, user_id: int, *, since: date) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                """
                SELECT * FROM bookings
                WHERE user_id = ? AND status IN ('pending', 'confirmed')
                  AND appointment_date >= ?
                ORDER BY appointment_date, start_minute
                LIMIT 10
                """,
                (user_id, since.isoformat()),
            ).fetchall()
        )

    def close(self) -> None:
        self.connection.close()


def parse_admin_ids(value: str) -> frozenset[int]:
    try:
        admin_ids = frozenset(
            int(item.strip()) for item in value.split(",") if item.strip()
        )
    except ValueError as exc:
        raise ValueError(
            "BARBERSHOP_ADMIN_USER_IDS must be comma-separated numeric Telegram user IDs."
        ) from exc
    if any(admin_id <= 0 for admin_id in admin_ids):
        raise ValueError("Telegram admin user IDs must be positive integers.")
    return admin_ids


def format_time(start_minute: int) -> str:
    return f"{start_minute // 60:02d}:{start_minute % 60:02d}"


def render_booking(row: sqlite3.Row) -> str:
    status = {
        "pending": "очікує підтвердження",
        "confirmed": "підтверджено",
        "cancelled": "скасовано",
    }.get(row["status"], row["status"])
    return (
        f"Запис #{row['id']}\n"
        f"{row['appointment_date']} о {format_time(row['start_minute'])}\n"
        f"{row['service_name']} — {row['price']} грн ({row['duration_minutes']} хв)\n"
        f"Клієнт: {row['customer_name']}\n"
        f"Телефон: {row['phone']}\n"
        f"Статус: {status}"
    )


def build_bot(
    *,
    token: str,
    admin_ids: frozenset[int],
    store: BookingStore,
    shop_name: str,
    timezone: ZoneInfo,
    open_hour: int = 10,
    close_hour: int = 20,
    adapter: Any | None = None,
) -> Bot:
    if not 0 <= open_hour < close_hour <= 24:
        raise ValueError("Opening hours must satisfy 0 <= open hour < close hour <= 24.")
    bot = Bot(platform="telegram", token=token, name="barbershop", adapter=adapter)
    drafts: dict[int, BookingDraft] = {}

    def today() -> date:
        return datetime.now(timezone).date()

    def is_admin(ctx) -> bool:
        return ctx.user is not None and int(ctx.user.id) in admin_ids

    async def require_private_chat(ctx) -> bool:
        if ctx.chat is not None and ctx.chat.type == "private":
            return True
        if ctx.callback_query_id:
            await ctx.answer_callback(
                "Для запису відкрийте особистий чат із ботом.",
                show_alert=True,
            )
        elif ctx.chat is not None:
            await ctx.reply(
                "Для приватності відкрийте особистий чат із ботом."
            )
        return False

    def is_working_day(day: date) -> bool:
        return day.weekday() < 6

    def available_slots(day: date, service: Service) -> list[int]:
        if day < today() or day > today() + timedelta(days=14) or not is_working_day(day):
            return []
        first = open_hour * 60
        last = close_hour * 60 - service.duration_minutes
        now = datetime.now(timezone)
        current_minute = now.hour * 60 + now.minute
        return [
            minute
            for minute in range(first, last + 1, SLOT_STEP_MINUTES)
            if day != today() or minute > current_minute
            if store.is_available(day, minute, service.duration_minutes)
        ]

    def main_keyboard() -> Keyboard:
        return Keyboard(
            buttons=[
                [Button("Записатися", callback_data="book:start")],
                [Button("Мої записи", callback_data="book:mine")],
            ]
        )

    async def notify_admins(text: str, keyboard: Keyboard | None = None) -> None:
        for admin_id in sorted(admin_ids):
            await bot.adapter.send_message(admin_id, text, keyboard=keyboard)

    async def show_service_menu(ctx) -> None:
        await ctx.reply(
            f"Оберіть послугу в {shop_name}:",
            keyboard=Keyboard(
                buttons=[
                    [
                        Button(
                            f"{service.name} — {service.price} грн",
                            callback_data=f"book:service:{service.id}",
                        )
                    ]
                    for service in SERVICES
                ]
                + [[Button("Скасувати", callback_data="book:cancel")]]
            ),
        )

    async def show_dates(ctx, draft: BookingDraft) -> None:
        days = [
            today() + timedelta(days=offset)
            for offset in range(15)
            if is_working_day(today() + timedelta(days=offset))
            and available_slots(today() + timedelta(days=offset), draft.service)
        ]
        if not days:
            await ctx.reply("На найближчі два тижні вільних годин немає.")
            drafts.pop(int(ctx.user.id), None)
            return
        await ctx.reply(
            "Оберіть дату (показані лише дні з вільним часом):",
            keyboard=Keyboard(
                buttons=[
                    [
                        Button(
                            day.strftime("%d.%m (%a)"),
                            callback_data=f"book:date:{day.isoformat()}",
                        )
                    ]
                    for day in days
                ]
                + [[Button("Скасувати", callback_data="book:cancel")]]
            ),
        )

    async def show_times(ctx, draft: BookingDraft) -> None:
        if draft.appointment_date is None:
            await ctx.reply("Сеанс запису завершився. Почніть знову командою /start.")
            drafts.pop(int(ctx.user.id), None)
            return
        slots = available_slots(draft.appointment_date, draft.service)
        if not slots:
            await ctx.reply("На цю дату вільного часу більше немає. Оберіть іншу дату.")
            await show_dates(ctx, draft)
            return
        buttons = [
            [
                Button(
                    format_time(minute),
                    callback_data=f"book:time:{minute}",
                )
            ]
            for minute in slots
        ]
        buttons.append([Button("Назад до дат", callback_data="book:back_dates")])
        buttons.append([Button("Скасувати", callback_data="book:cancel")])
        await ctx.reply(
            f"Вільний час на {draft.appointment_date.strftime('%d.%m.%Y')}:",
            keyboard=Keyboard(buttons=buttons),
        )

    def booking_keyboard(booking_id: int) -> Keyboard:
        return Keyboard(
            buttons=[
                [
                    Button("Підтвердити", callback_data=f"admin:confirm:{booking_id}"),
                    Button("Відхилити", callback_data=f"admin:cancel:{booking_id}"),
                ]
            ]
        )

    @bot.command("start")
    async def start(ctx) -> None:
        if not await require_private_chat(ctx):
            return
        drafts.pop(int(ctx.user.id), None)
        await ctx.reply(
            f"Вітаємо у {shop_name}! Тут можна обрати послугу й зручний час.",
            keyboard=main_keyboard(),
        )

    @bot.command("cancel")
    async def cancel(ctx) -> None:
        if not await require_private_chat(ctx):
            return
        drafts.pop(int(ctx.user.id), None)
        await ctx.reply("Запис скасовано. Щоб почати знову, натисніть «Записатися».")

    @bot.command("admin")
    async def admin(ctx) -> None:
        if not await require_private_chat(ctx):
            return
        if not is_admin(ctx):
            LOGGER.warning("Rejected /admin access from Telegram user ID %s", ctx.user.id)
            await ctx.reply("У вас немає доступу до адмін-панелі.")
            return
        await ctx.reply(
            f"Адмін-панель {shop_name}",
            keyboard=Keyboard(
                buttons=[
                    [Button("Очікують підтвердження", callback_data="admin:pending")],
                    [Button("Найближчі записи", callback_data="admin:upcoming")],
                ]
            ),
        )

    @bot.command("mybookings")
    async def my_bookings(ctx) -> None:
        if not await require_private_chat(ctx):
            return
        rows = store.list_user_bookings(int(ctx.user.id), since=today())
        if not rows:
            await ctx.reply("У вас немає майбутніх записів.")
            return
        await ctx.reply("\n\n".join(render_booking(row) for row in rows))

    @bot.callback()
    async def handle_callback(ctx) -> None:
        if not await require_private_chat(ctx):
            return
        data = ctx.callback_data or ""
        await ctx.answer_callback()
        user_id = int(ctx.user.id)

        if data == "book:start":
            drafts.pop(user_id, None)
            await show_service_menu(ctx)
            return
        if data == "book:mine":
            rows = store.list_user_bookings(user_id, since=today())
            text = (
                "\n\n".join(render_booking(row) for row in rows)
                if rows
                else "У вас немає майбутніх записів."
            )
            await ctx.reply(text, keyboard=main_keyboard())
            return
        if data == "book:cancel":
            drafts.pop(user_id, None)
            await ctx.reply("Запис скасовано.", keyboard=main_keyboard())
            return
        if data.startswith("book:service:"):
            service_id = data.removeprefix("book:service:")
            service = next((item for item in SERVICES if item.id == service_id), None)
            if service is None:
                await ctx.reply("Цю послугу більше не знайти. Почніть запис знову.")
                return
            draft = BookingDraft(service=service)
            drafts[user_id] = draft
            await show_dates(ctx, draft)
            return
        if data.startswith("book:date:"):
            draft = drafts.get(user_id)
            if draft is None:
                await ctx.reply("Сеанс запису завершився. Натисніть «Записатися».")
                return
            try:
                selected_date = date.fromisoformat(data.removeprefix("book:date:"))
            except ValueError:
                await ctx.reply("Некоректна дата. Оберіть дату зі списку.")
                return
            if selected_date not in {
                today() + timedelta(days=offset) for offset in range(15)
            } or not is_working_day(selected_date):
                await ctx.reply("Ця дата недоступна. Оберіть дату зі списку.")
                return
            draft.appointment_date = selected_date
            await show_times(ctx, draft)
            return
        if data == "book:back_dates":
            draft = drafts.get(user_id)
            if draft is None:
                await ctx.reply("Сеанс запису завершився. Натисніть «Записатися».")
                return
            await show_dates(ctx, draft)
            return
        if data.startswith("book:time:"):
            draft = drafts.get(user_id)
            if draft is None or draft.appointment_date is None:
                await ctx.reply("Сеанс запису завершився. Натисніть «Записатися».")
                return
            try:
                start_minute = int(data.removeprefix("book:time:"))
            except ValueError:
                await ctx.reply("Некоректний час. Оберіть час зі списку.")
                return
            if start_minute not in available_slots(draft.appointment_date, draft.service):
                await ctx.reply("Цей час щойно зайняли. Оберіть інший.")
                await show_times(ctx, draft)
                return
            draft.start_minute = start_minute
            await ctx.reply(
                f"Ви обрали {draft.service.name}, "
                f"{draft.appointment_date.strftime('%d.%m.%Y')} о {format_time(start_minute)}.\n"
                "Напишіть ваше ім'я:"
            )
            return
        if data.startswith("admin:"):
            if not is_admin(ctx):
                LOGGER.warning("Rejected admin callback from Telegram user ID %s", user_id)
                await ctx.reply("У вас немає доступу до адмін-панелі.")
                return
            if data == "admin:pending":
                rows = store.list_bookings(statuses=("pending",), since=today())
                await ctx.reply(
                    "\n\n".join(render_booking(row) for row in rows)
                    if rows
                    else "Немає записів, що очікують підтвердження."
                )
                for row in rows:
                    await ctx.send(
                        f"Дії для запису #{row['id']}:",
                        keyboard=booking_keyboard(int(row["id"])),
                    )
                return
            if data == "admin:upcoming":
                rows = store.list_bookings(
                    statuses=("pending", "confirmed"),
                    since=today(),
                )
                await ctx.reply(
                    "\n\n".join(render_booking(row) for row in rows)
                    if rows
                    else "Найближчих записів немає."
                )
                return
            action = data.split(":")
            if len(action) == 3 and action[1] in {"confirm", "cancel"}:
                try:
                    booking_id = int(action[2])
                except ValueError:
                    await ctx.reply("Некоректний номер запису.")
                    return
                row = store.get_booking(booking_id)
                if row is None:
                    await ctx.reply("Запис не знайдено.")
                    return
                status = "confirmed" if action[1] == "confirm" else "cancelled"
                if not store.update_status(booking_id, status):
                    await ctx.reply("Цей запис уже оброблений.")
                    return
                status_text = "підтверджено" if status == "confirmed" else "скасовано"
                await ctx.reply(f"Запис #{booking_id} {status_text}.")
                customer_message = (
                    f"Ваш запис #{booking_id} підтверджено."
                    if status == "confirmed"
                    else f"На жаль, запис #{booking_id} скасовано. Напишіть нам, щоб обрати інший час."
                )
                await bot.adapter.send_message(int(row["chat_id"]), customer_message)
                return
            await ctx.reply("Невідома дія адмін-панелі.")
            return
        await ctx.reply("Кнопка застаріла. Відкрийте /start.")

    @bot.message(filters.custom(lambda ctx: ctx.event_name == "message"))
    async def collect_booking_details(ctx) -> None:
        if not await require_private_chat(ctx):
            return
        text = (ctx.text or "").strip()
        if not text or text.startswith("/"):
            return
        user_id = int(ctx.user.id)
        draft = drafts.get(user_id)
        if draft is None:
            await ctx.reply("Щоб записатися, натисніть /start.")
            return
        if draft.start_minute is None:
            await ctx.reply("Спочатку оберіть дату й час кнопками.")
            return
        if draft.customer_name is None:
            if len(text) < 2 or len(text) > 80:
                await ctx.reply("Введіть ім'я довжиною від 2 до 80 символів.")
                return
            draft.customer_name = text
            await ctx.reply("Тепер надішліть номер телефону у міжнародному форматі.")
            return
        phone = re.sub(r"\s+", " ", text)
        digit_count = sum(character.isdigit() for character in phone)
        if not PHONE_PATTERN.fullmatch(phone) or not 7 <= digit_count <= 15:
            await ctx.reply("Не схоже на номер телефону. Введіть номер ще раз.")
            return
        if draft.appointment_date is None or draft.start_minute is None:
            drafts.pop(user_id, None)
            await ctx.reply("Сеанс запису завершився. Почніть знову через /start.")
            return
        booking_id = store.create_booking(
            user_id=user_id,
            chat_id=int(ctx.chat.id),
            customer_name=draft.customer_name,
            phone=phone,
            service=draft.service,
            appointment_date=draft.appointment_date,
            start_minute=draft.start_minute,
        )
        if booking_id is None:
            draft.start_minute = None
            await ctx.reply("Цей час щойно зайняли. Оберіть інший.")
            await show_times(ctx, draft)
            return
        drafts.pop(user_id, None)
        row = store.get_booking(booking_id)
        assert row is not None
        await ctx.reply(
            f"Дякуємо, {draft.customer_name}! Запит на запис #{booking_id} надіслано.\n"
            "Адміністратор підтвердить його окремим повідомленням.",
            keyboard=main_keyboard(),
        )
        await notify_admins(
            f"Новий запит на запис:\n\n{render_booking(row)}\n"
            f"Telegram user ID: {user_id}",
            keyboard=booking_keyboard(booking_id),
        )

    return bot


async def run_bot() -> None:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env before starting the bot.")
    admin_ids = parse_admin_ids(os.getenv("BARBERSHOP_ADMIN_USER_IDS", ""))
    if not admin_ids:
        raise SystemExit(
            "Set BARBERSHOP_ADMIN_USER_IDS to at least one numeric Telegram user ID."
        )
    try:
        timezone = ZoneInfo(os.getenv("BARBERSHOP_TIMEZONE", "Europe/Kyiv"))
    except ZoneInfoNotFoundError as exc:
        raise SystemExit(f"Unknown timezone: {exc}") from exc
    database_path = Path(os.getenv("BARBERSHOP_DATABASE", "barbershop.sqlite3"))
    store = BookingStore(database_path)
    bot = build_bot(
        token=token,
        admin_ids=admin_ids,
        store=store,
        shop_name=os.getenv("BARBERSHOP_NAME", "Barbershop"),
        timezone=timezone,
        open_hour=int(os.getenv("BARBERSHOP_OPEN_HOUR", "10")),
        close_hour=int(os.getenv("BARBERSHOP_CLOSE_HOUR", "20")),
    )
    try:
        await bot.run()
    finally:
        await bot.stop()
        store.close()


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("PYBOT3_LOG_LEVEL", "INFO").upper())
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        LOGGER.info("Bot stopped by keyboard interrupt")
