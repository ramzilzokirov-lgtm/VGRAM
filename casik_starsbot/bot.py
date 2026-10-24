import os, time, random, sqlite3, threading, logging
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not TOKEN:
    raise RuntimeError("Set BOT_TOKEN in Render environment variables")
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
DB = os.getenv("DB_PATH", "casik_starsbot.db")
lock = threading.Lock()
logging.basicConfig(level=logging.INFO)

def init_db():
    with sqlite3.connect(DB) as c:
        c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, coins INTEGER NOT NULL DEFAULT 1000, bonus INTEGER NOT NULL DEFAULT 0)")

def get_coins(uid):
    with lock, sqlite3.connect(DB) as c:
        c.execute("INSERT OR IGNORE INTO users(id) VALUES(?)", (uid,))
        return c.execute("SELECT coins FROM users WHERE id=?", (uid,)).fetchone()[0]

def add_coins(uid, amount):
    with lock, sqlite3.connect(DB) as c:
        c.execute("INSERT OR IGNORE INTO users(id) VALUES(?)", (uid,))
        c.execute("UPDATE users SET coins=MAX(0,coins+?) WHERE id=?", (amount,uid))
        return c.execute("SELECT coins FROM users WHERE id=?", (uid,)).fetchone()[0]

def keyboard():
    k=types.InlineKeyboardMarkup(row_width=2)
    k.add(types.InlineKeyboardButton("🎰 Слоты (100 ⭐)",callback_data="slots"),types.InlineKeyboardButton("🎲 Кубик (50 ⭐)",callback_data="dice"))
    k.add(types.InlineKeyboardButton("💰 Баланс",callback_data="balance"),types.InlineKeyboardButton("🎁 Бонус",callback_data="bonus"))
    return k

@bot.message_handler(commands=["start","menu"])
def start(m):
    n=(m.from_user.first_name or "игрок").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    bot.send_message(m.chat.id,f"⭐ <b>Casik Stars Bot</b>\nПривет, {n}!\nСтартовый баланс: <b>{get_coins(m.from_user.id)} ⭐</b>",reply_markup=keyboard())

@bot.callback_query_handler(func=lambda c:c.data in ("slots","dice","balance","bonus"))
def action(c):
    uid=c.from_user.id
    bot.answer_callback_query(c.id)
    if c.data=="balance":
        bot.send_message(c.message.chat.id,f"💰 Баланс: <b>{get_coins(uid)} ⭐</b>",reply_markup=keyboard())
    elif c.data=="bonus":
        now=int(time.time())
        with lock, sqlite3.connect(DB) as con:
            con.execute("INSERT OR IGNORE INTO users(id) VALUES(?)",(uid,))
            last=con.execute("SELECT bonus FROM users WHERE id=?",(uid,)).fetchone()[0]
            if now-last<86400:
                bot.send_message(c.message.chat.id,"⏳ Бонус можно получить раз в 24 часа.",reply_markup=keyboard()); return
            amount=random.randint(50,150)
            con.execute("UPDATE users SET coins=coins+?,bonus=? WHERE id=?",(amount,now,uid))
        bot.send_message(c.message.chat.id,f"🎁 Получено <b>{amount} ⭐</b>!",reply_markup=keyboard())
    else:
        stake=100 if c.data=="slots" else 50
        if get_coins(uid)<stake:
            bot.send_message(c.message.chat.id,"Не хватает ⭐ для этой игры.",reply_markup=keyboard()); return
        add_coins(uid,-stake)
        if c.data=="slots":
            icons=[random.choice(["🍒","🍋","7️⃣","💎"]) for _ in range(3)]
            win=len(set(icons))==1
            label=" | ".join(icons)
        else:
            number=random.randint(1,6); win=number==6; label=f"🎲 Выпало {number}"
        prize=stake*5 if win else 0
        if prize: add_coins(uid,prize)
        bot.send_message(c.message.chat.id,f"{label}\n{'🎉 Победа! +' + str(prize) + ' ⭐' if win else 'В этот раз без выигрыша.'}\nБаланс: <b>{get_coins(uid)} ⭐</b>",reply_markup=keyboard())

class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"Casik Stars Bot running")
    def log_message(self,*args): pass

def main():
    init_db()
    threading.Thread(target=lambda:HTTPServer(("0.0.0.0",int(os.getenv("PORT","10000"))),Health).serve_forever(),daemon=True).start()
    while True:
        try: bot.infinity_polling(skip_pending=True,timeout=30,long_polling_timeout=30)
        except Exception:
            logging.exception("Polling error"); time.sleep(5)

if __name__=="__main__": main()
