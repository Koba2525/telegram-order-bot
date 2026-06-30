# -*- coding: utf-8 -*-
"""
Order-taking Telegram bot for businesses (cafe / shop / service).

Improved version:
  - Token loaded from .env (never hardcoded)
  - Per-item quantity controls (+/-) instead of just "add"
  - Remove single item from cart
  - Order numbering + simple in-memory order history
  - /cancel command to abort checkout
  - Input validation on phone number
  - Proper logging to file + console
  - Graceful error handling (won't crash on bad input)

Setup:
  1. Create a bot via @BotFather, get the TOKEN
  2. Create a .env file next to this script:
       BOT_TOKEN=123456:ABC-your-token
       ADMIN_CHAT_ID=123456789
  3. pip install python-telegram-bot python-dotenv
  4. python bot.py
"""
import logging
import os
import re
from datetime import datetime

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters,
)

# ═══════════════ CONFIG ═══════════════
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

BUSINESS_NAME = os.getenv("BUSINESS_NAME", "My Cafe")
CURRENCY = os.getenv("CURRENCY", "$")

# Menu — client edits this. id: (name, price)
MENU = {
    "1": ("Espresso", 5.0),
    "2": ("Cappuccino", 7.0),
    "3": ("Latte", 7.5),
    "4": ("Tea", 4.0),
    "5": ("Pastry", 8.0),
    "6": ("Sandwich", 12.0),
}

PHONE_PATTERN = re.compile(r"^\+?[0-9\s\-()]{7,20}$")
# ════════════════════════════════════════

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("bot.log", encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# In-memory state (swap for a DB in production)
CARTS: dict[int, dict[str, int]] = {}
ORDER_STATE: dict[int, dict] = {}
ORDER_COUNTER = {"n": 1000}


def menu_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for iid, (name, price) in MENU.items():
        rows.append([InlineKeyboardButton(f"{name} — {price:.2f}{CURRENCY}", callback_data=f"add:{iid}")])
    rows.append([
        InlineKeyboardButton("🛒 Cart", callback_data="cart"),
        InlineKeyboardButton("✅ Checkout", callback_data="checkout"),
    ])
    return InlineKeyboardMarkup(rows)


def cart_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    cart = CARTS.get(chat_id, {})
    rows = []
    for iid, qty in cart.items():
        name = MENU[iid][0]
        rows.append([
            InlineKeyboardButton(f"➖ {name}", callback_data=f"dec:{iid}"),
            InlineKeyboardButton(f"{qty}", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data=f"add:{iid}"),
            InlineKeyboardButton("🗑", callback_data=f"rm:{iid}"),
        ])
    rows.append([
        InlineKeyboardButton("⬅️ Menu", callback_data="menu"),
        InlineKeyboardButton("✅ Checkout", callback_data="checkout"),
    ])
    return InlineKeyboardMarkup(rows)


def cart_text(chat_id: int) -> str:
    cart = CARTS.get(chat_id, {})
    if not cart:
        return "🛒 Your cart is empty."
    lines = ["🛒 Your cart:\n"]
    total = 0.0
    for iid, qty in cart.items():
        name, price = MENU[iid]
        s = price * qty
        total += s
        lines.append(f"• {name} × {qty} = {s:.2f}{CURRENCY}")
    lines.append(f"\n💰 Total: {total:.2f}{CURRENCY}")
    return "\n".join(lines)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"👋 Welcome to {BUSINESS_NAME}!\n\nPlease choose a product:",
        reply_markup=menu_keyboard(),
    )


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    ORDER_STATE.pop(chat_id, None)
    await update.message.reply_text("❌ Checkout cancelled. Your cart is still saved.", reply_markup=menu_keyboard())


async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    chat_id = q.message.chat_id
    data = q.data

    try:
        if data == "noop":
            await q.answer()
            return

        if data.startswith("add:"):
            iid = data.split(":")[1]
            CARTS.setdefault(chat_id, {})
            CARTS[chat_id][iid] = CARTS[chat_id].get(iid, 0) + 1
            await q.answer(f"Added: {MENU[iid][0]}")
            in_cart_view = any(
                b.callback_data and b.callback_data.startswith("dec:")
                for row in q.message.reply_markup.inline_keyboard for b in row
            )
            if in_cart_view:
                await q.edit_message_text(cart_text(chat_id), reply_markup=cart_keyboard(chat_id))
            return

        if data.startswith("dec:"):
            iid = data.split(":")[1]
            if CARTS.get(chat_id, {}).get(iid, 0) > 0:
                CARTS[chat_id][iid] -= 1
                if CARTS[chat_id][iid] == 0:
                    del CARTS[chat_id][iid]
            await q.answer()
            await q.edit_message_text(cart_text(chat_id), reply_markup=cart_keyboard(chat_id))
            return

        if data.startswith("rm:"):
            iid = data.split(":")[1]
            CARTS.get(chat_id, {}).pop(iid, None)
            await q.answer("Removed")
            await q.edit_message_text(cart_text(chat_id), reply_markup=cart_keyboard(chat_id))
            return

        if data == "cart":
            await q.answer()
            await q.edit_message_text(cart_text(chat_id), reply_markup=cart_keyboard(chat_id))
            return

        if data == "menu":
            await q.answer()
            await q.edit_message_text("Please choose a product:", reply_markup=menu_keyboard())
            return

        if data == "checkout":
            if not CARTS.get(chat_id):
                await q.answer("Cart is empty!", show_alert=True)
                return
            await q.answer()
            ORDER_STATE[chat_id] = {"step": "name"}
            await q.edit_message_text(cart_text(chat_id) + "\n\n✍️ Please enter your name:\n(or /cancel to abort)")
            return

    except Exception:
        logger.exception("Error handling button callback (data=%s, chat=%s)", data, chat_id)
        await q.answer("Something went wrong, please try again.", show_alert=True)


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    state = ORDER_STATE.get(chat_id)
    if not state:
        await update.message.reply_text("Please choose a product 👇", reply_markup=menu_keyboard())
        return

    if state["step"] == "name":
        name = update.message.text.strip()
        if len(name) < 2:
            await update.message.reply_text("Please enter a valid name (at least 2 characters):")
            return
        state["name"] = name
        state["step"] = "phone"
        kb = ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Share phone number", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True,
        )
        await update.message.reply_text(
            "📞 Please enter your phone number or share it:\n(or /cancel to abort)", reply_markup=kb
        )
        return

    if state["step"] == "phone":
        phone = update.message.text.strip()
        if not PHONE_PATTERN.match(phone):
            await update.message.reply_text("That doesn't look like a valid phone number. Please try again:")
            return
        state["phone"] = phone
        await finalize_order(update, ctx, chat_id)


async def on_contact(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    state = ORDER_STATE.get(chat_id)
    if state and state.get("step") == "phone":
        state["phone"] = update.message.contact.phone_number
        await finalize_order(update, ctx, chat_id)


async def finalize_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE, chat_id: int):
    state = ORDER_STATE.get(chat_id, {})
    cart = CARTS.get(chat_id, {})

    order_id = ORDER_COUNTER["n"]
    ORDER_COUNTER["n"] += 1

    order_lines = [f"🆕 New order #{order_id} — {BUSINESS_NAME}",
                   f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
    total = 0.0
    for iid, qty in cart.items():
        name, price = MENU[iid]
        s = price * qty
        total += s
        order_lines.append(f"• {name} × {qty} = {s:.2f}{CURRENCY}")
    order_lines.append(f"\n💰 Total: {total:.2f}{CURRENCY}")
    order_lines.append(f"\n👤 {state.get('name', '?')}\n📞 {state.get('phone', '?')}")
    order_text = "\n".join(order_lines)

    if ADMIN_CHAT_ID:
        try:
            await ctx.bot.send_message(chat_id=ADMIN_CHAT_ID, text=order_text)
        except Exception:
            logger.exception("Failed to notify admin for order #%s", order_id)
    else:
        logger.warning("ADMIN_CHAT_ID not set — order #%s was not forwarded", order_id)

    await update.message.reply_text(
        f"✅ Thank you! Your order #{order_id} has been received.\nWe'll contact you shortly.",
        reply_markup=ReplyKeyboardRemove(),
    )
    logger.info("Order #%s finalized for chat_id=%s, total=%.2f", order_id, chat_id, total)

    CARTS[chat_id] = {}
    ORDER_STATE.pop(chat_id, None)


async def myid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Helper: tells the business owner their chat_id (for ADMIN_CHAT_ID)."""
    await update.message.reply_text(f"Your chat_id: {update.message.chat_id}")


async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled exception", exc_info=ctx.error)


def main():
    if not BOT_TOKEN:
        print("[SETUP] BOT_TOKEN is missing. Create a .env file with BOT_TOKEN=...")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.CONTACT, on_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)

    logger.info("Bot starting...")
    print("[OK] Bot running. Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()