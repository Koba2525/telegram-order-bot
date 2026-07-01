# Telegram Order Bot for Businesses

A ready-to-deploy Telegram bot for cafes, shops, and service businesses.
Customers browse the menu, build a cart, and place orders — all inside Telegram.
Every order is instantly forwarded to the business owner.

---

## Features

- Inline menu with buttons
- Cart with +/- quantity controls and item removal
- Checkout flow: name + phone number collection
- Phone number validation
- Contact sharing button (one tap instead of typing)
- Unique order numbering (#1000, #1001...)
- Order instantly forwarded to business owner via Telegram
- /cancel command to abort checkout at any step
- Errors logged to bot.log — bot never crashes on bad input
- Config via .env — token never hardcoded

---

## Requirements

```
python-telegram-bot
python-dotenv
```

Install:
```bash
pip install python-telegram-bot python-dotenv
```

---

## Setup

**Step 1 — Create a bot**
- Open Telegram, search for @BotFather
- Send /newbot, follow the prompts
- Copy the TOKEN you receive

**Step 2 — Create .env file**

Create a file named `.env` next to `bot.py`:
```
BOT_TOKEN=123456:ABC-your-token-here
ADMIN_CHAT_ID=0
BUSINESS_NAME=My Cafe
CURRENCY=$
```

**Step 3 — Get your chat_id**
- Run the bot: `python bot.py`
- Send /myid to your bot in Telegram
- Copy the number you receive
- Update .env: `ADMIN_CHAT_ID=123456789`
- Restart the bot

**Step 4 — Edit the menu**

Open `bot.py` and update the MENU dictionary:
```python
MENU = {
    "1": ("Espresso",   5.0),
    "2": ("Cappuccino", 7.0),
    "3": ("Your item",  0.0),
}
```

**Step 5 — Run**
```bash
python bot.py
```

---

## File Structure

```
project/
├── bot.py          # Main bot code
├── .env            # Your credentials (never share this)
├── .gitignore      # Excludes .env and bot.log from Git
└── bot.log         # Auto-generated log file
```

---

## .gitignore

```
.env
bot.log
```

---

## Customization

| What | Where |
|------|-------|
| Menu items and prices | MENU dict in bot.py |
| Business name | BUSINESS_NAME in .env |
| Currency symbol | CURRENCY in .env |
| Welcome message | start() function in bot.py |

---

## Built With

- Python 3.10+
- python-telegram-bot 20+
- python-dotenv
