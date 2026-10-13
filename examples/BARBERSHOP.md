# Barbershop Telegram bot

## Setup

1. Create a Telegram bot with BotFather and copy its token.
2. Find the numeric Telegram user ID for each administrator. Configure IDs, not usernames; usernames can change.
3. Install the library with the callback-query API:

   ```bash
   python -m pip install "pybot3>=0.1.1"
   ```

   If `0.1.1` has not been published yet, install the checked-out project instead:

   ```bash
   python -m pip install -e .
   ```

4. Create a `.env` file in the repository root:

   ```dotenv
   TELEGRAM_BOT_TOKEN=replace-with-your-bot-token
   BARBERSHOP_ADMIN_USER_IDS=123456789,987654321
   BARBERSHOP_NAME=Barbershop
   BARBERSHOP_TIMEZONE=Europe/Kyiv
   BARBERSHOP_DATABASE=barbershop.sqlite3
   BARBERSHOP_OPEN_HOUR=10
   BARBERSHOP_CLOSE_HOUR=20
   ```

5. Start the bot:

   ```bash
   python examples/barbershop_bot.py
   ```

Never commit `.env`, the SQLite database, or real bot tokens.

## Customer flow

- `/start` opens the booking menu.
- The customer chooses a service, an available working day, and a free time.
- The customer enters a name and phone number. The booking is then stored as pending and sent to administrators.
- A pending booking reserves its full service duration, preventing overlapping appointments even when several requests arrive at once.
- The customer can inspect future bookings using `/mybookings` or the “Мої записи” button. `/cancel` clears an unfinished booking flow.

The bot offers appointments up to 14 days ahead, in 30-minute start increments, Monday through Saturday. Slots earlier than the current local time are hidden. All times use `BARBERSHOP_TIMEZONE`.

Only private chats are allowed for booking and administration so customer contact details are not collected in group chats. Completed bookings persist in SQLite; an unfinished booking draft is kept in memory and must be restarted if the bot process restarts.

## Administrator flow

- `/admin` opens the admin panel only for IDs in `BARBERSHOP_ADMIN_USER_IDS`.
- Administrators can list pending or upcoming bookings and confirm or reject each pending request.
- Authorization is checked again for every admin callback; knowing a callback value or username does not grant access.
- Customers receive a Telegram message when their booking is confirmed or rejected.

## Customization and operations

Edit the `SERVICES` tuple near the top of `barbershop_bot.py` to change services, prices, and durations. Business hours are configured as whole hours with the environment variables above. The sample intentionally handles bookings in one local SQLite database; back up that file and run only one bot polling process per Telegram token.

Booking details, including customer names and phone numbers, are personal data. Restrict access to the database and server, configure a retention policy appropriate for the shop, and do not publish the database or send it to public logs.
