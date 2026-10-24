import os
import random
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is required")

DB_PATH = os.getenv("DB_PATH", "casik_starsbot.sqlite3")
START_BALANCE = 1000
BONUS_MIN, BONUS_MAX = 50, 150
BONUS_COOLDOWN = 24 * 60 * 60
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
db_lock = threading.Lock()


def db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER NOT NULL DEFAULT 1000,
        last_bonus INTEGER NOT NULL DEFAULT 0
    )""")
    return conn


def ensure_user(user_id):
    with db_lock, db() as conn:
        conn.execute("INSERT OR IGNORE INTO users(user_id,balance,last_bonus) VALUES(?,?,0)",
                     (user_id, START_BALANCE))
        row = conn.execute("SELECT balance,last_bonus FROM users WHERE user_id=?",
                           (user_id,)).fetchone()
        return row[0], row[1]


def change_balance(user_id, delta):
    with db_lock, db() as conn:
        conn.execute("INSERT OR IGNORE INTO users(user_id,balance,last_bonus) VALUES(?,?,0)",
                     (user_id, START_BALANCE))
        balance = conn.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)).fetchone()[0]
        if delta < 0 and balance < -delta:
            return None
        balance += delta
        conn.execute("UPDATE users SET balance=? WHERE user_id=?", (balance, user_id))
        return balance


def menu():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🎰 Слоты · 100 ⭐", callback_data="slots"),
        types.InlineKeyboardButton("🎲 Кости · 50 ⭐", callback_data="dice"),
        types.InlineKeyboardButton("⭐ Баланс", callback_data="balance"),
        types.InlineKeyboardButton("🎁 Ежедневный бонус", callback_data="bonus"),
    )
    return kb


def home_text():
    return ("<b>⭐ Casik Stars Bot</b>\n\n"
            "Игровые звёзды, слоты и кости.\n"
            "Новый игрок получает <b>1000 ⭐</b>.\n\n"
            "Выбери действие ниже:")


@bot.message_handler(commands=["start", "menu", "help"])
def start(message):
    balance, _ = ensure_user(message.from_user.id)
    bot.send_message(message.chat.id, home_text() + f"\n\nТвой баланс: <b>{balance} ⭐</b>",
                     reply_markup=menu())


@bot.callback_query_handler(func=lambda call: call.data == "balance")
def balance_action(call):
    balance, _ = ensure_user(call.from_user.id)
    bot.answer_callback_query(call.id, "Баланс обновлён")
    bot.send_message(call.message.chat.id, f"⭐ Твой баланс: <b>{balance} ⭐</b>",
                     reply_markup=menu())


@bot.callback_query_handler(func=lambda call: call.data == "bonus")
def bonus_action(call):
    ensure_user(call.from_user.id)
    now = int(time.time())
    with db_lock, db() as conn:
        last = conn.execute("SELECT last_bonus FROM users WHERE user_id=?",
                            (call.from_user.id,)).fetchone()[0]
        if now - last < BONUS_COOLDOWN:
            remaining = BONUS_COOLDOWN - (now - last)
            hours, rem = divmod(remaining, 3600)
            minutes = rem // 60
            bot.answer_callback_query(call.id, f"Бонус уже получен. Подожди {hours} ч. {minutes} мин.",
                                      show_alert=True)
            return
        reward = random.randint(BONUS_MIN, BONUS_MAX)
        conn.execute("UPDATE users SET balance=balance+?, last_bonus=? WHERE user_id=?",
                     (reward, now, call.from_user.id))
        balance = conn.execute("SELECT balance FROM users WHERE user_id=?",
                               (call.from_user.id,)).fetchone()[0]
    bot.answer_callback_query(call.id, f"+{reward} ⭐")
    bot.send_message(call.message.chat.id,
                     f"🎁 Ежедневный бонус: <b>+{reward} ⭐</b>\nБаланс: <b>{balance} ⭐</b>",
                     reply_markup=menu())


@bot.callback_query_handler(func=lambda call: call.data == "slots")
def slots_action(call):
    stake = 100
    balance = change_balance(call.from_user.id, -stake)
    if balance is None:
        bot.answer_callback_query(call.id, "Не хватает ⭐. Забери ежедневный бонус.", show_alert=True)
        return
    symbols = ["🍒", "🍋", "7️⃣", "💎"]
    roll = [random.choice(symbols) for _ in range(3)]
    win = stake * 5 if len(set(roll)) == 1 else 0
    balance = change_balance(call.from_user.id, win)
    result = "🎉 Три одинаковых! Выигрыш <b>500 ⭐</b>." if win else "Не повезло — попробуй ещё раз."
    bot.answer_callback_query(call.id, "Слоты!")
    bot.send_message(call.message.chat.id,
                     f"🎰 <b>{' | '.join(roll)}</b>\nСтавка: {stake} ⭐\n{result}\n"
                     f"Твой баланс: <b>{balance} ⭐</b>",
                     reply_markup=menu())


@bot.callback_query_handler(func=lambda call: call.data == "dice")
def dice_action(call):
    stake = 50
    balance = change_balance(call.from_user.id, -stake)
    if balance is None:
        bot.answer_callback_query(call.id, "Не хватает ⭐. Забери ежедневный бонус.", show_alert=True)
        return
    roll = random.randint(1, 6)
    win = stake * 5 if roll == 6 else 0
    balance = change_balance(call.from_user.id, win)
    result = "🎉 Выпала шестёрка! Выигрыш <b>250 ⭐</b>." if win else "В этот раз без выигрыша."
    bot.answer_callback_query(call.id, "Бросок костей!")
    bot.send_message(call.message.chat.id,
                     f"🎲 Выпало: <b>{roll}</b>\nСтавка: {stake} ⭐\n{result}\n"
                     f"Твой баланс: <b>{balance} ⭐</b>",
                     reply_markup=menu())


class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Casik Stars Bot is running")
    def log_message(self, *args):
        pass


def main():
    port = int(os.getenv("PORT", "10000"))
    threading.Thread(target=lambda: ThreadingHTTPServer(("0.0.0.0", port), Health).serve_forever(),
                     daemon=True).start()
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)


if __name__ == "__main__":
    main()
