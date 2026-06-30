# Order Bot — Deployment Guide

## What the Bot Does
For businesses (cafe / shop / service):
- Client sees the menu with buttons
- Adds items to the cart
- Places an order (Name + Phone number)
- The order automatically goes to the business owner in Telegram

---

## Deployment — 4 Steps

### 1. Bot Creation (2 minutes)
- Search for **@BotFather** in Telegram
- Type `/newbot`
- Give it a name (e.g., "My Cafe")
- You will receive a **TOKEN** (long code)

### 2. Insert the TOKEN
- Open `bot.py`
- Find `BOT_TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"`
- Paste your token: `BOT_TOKEN = "123456:ABC..."`

### 3. Get your chat_id (Where orders will arrive)
- First run the bot: `python bot.py`
- Write `/myid` to your bot in Telegram
- You will receive a number — this is your chat_id
- Paste it into `bot.py`: `ADMIN_CHAT_ID = 123456789`

### 4. Change the Menu (Your Products)
Find `MENU` in `bot.py` and change it:
```python
MENU = {
    "1": ("Espresso",   5.0),
    "2": ("Cappuccino",  7.0),
    # Add your products here
}