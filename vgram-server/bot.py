import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes,
    MessageHandler, filters,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("vgram-shop")
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8436409687"))
DB_PATH = os.getenv("DB_PATH", "/var/data/shop.sqlite3")
CATEGORIES = {
    "numbers": "📱 +888 номера",
    "stars": "⭐ Telegram Stars",
    "premium": "💎 Telegram Premium",
    "nfts": "🖼 NFT",
}
STATUSES = {"new": "🆕 Новый", "progress": "⏳ В работе", "done": "✅ Выполнен", "rejected": "❌ Отклонён"}

def db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
            joined_at TEXT NOT NULL, banned INTEGER NOT NULL DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL,
            name TEXT NOT NULL, price TEXT NOT NULL, stock INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL, quantity INTEGER NOT NULL,
            total TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new',
            created_at TEXT NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL)""")

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def is_admin(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id == ADMIN_ID)

def main_menu():
    rows = [[InlineKeyboardButton(label, callback_data=f"cat:{key}")]
            for key, label in CATEGORIES.items()]
    rows.append([InlineKeyboardButton("📦 Мои заказы", callback_data="myorders")])
    return InlineKeyboardMarkup(rows)

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Статистика", callback_data="adm:stats"),
         InlineKeyboardButton("📦 Заказы", callback_data="adm:orders:new")],
        [InlineKeyboardButton("🛍 Товары", callback_data="adm:products"),
         InlineKeyboardButton("➕ Добавить товар", callback_data="adm:addhelp")],
        [InlineKeyboardButton("👥 Пользователи", callback_data="adm:users"),
         InlineKeyboardButton("📣 Рассылка", callback_data="adm:broadcasthelp")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    with db() as c:
        c.execute("INSERT INTO users(user_id,username,full_name,joined_at) VALUES(?,?,?,?) "
                  "ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,full_name=excluded.full_name",
                  (u.id, u.username or "", u.full_name or "", now()))
        row = c.execute("SELECT banned FROM users WHERE user_id=?", (u.id,)).fetchone()
    if row and row["banned"] and not is_admin(update):
        await update.message.reply_text("Доступ к магазину ограничен.")
        return
    await update.message.reply_text("🛍 Добро пожаловать в магазин!\n\nВыбери категорию:", reply_markup=main_menu())

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Команды:\n/start — магазин\n/help — помощь\n/health — статус")
    
async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("OK — бот работает.")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Нет доступа.")
        return
    await update.message.reply_text("⚙️ Панель администратора", reply_markup=admin_menu())

async def addproduct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Нет доступа.")
        return
    raw = " ".join(context.args)
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) != 4 or parts[0] not in CATEGORIES:
        await update.message.reply_text(
            "Формат команды:\n/addproduct категория | название | цена | остаток\n\n"
            "Категории: numbers, stars, premium, nfts\n"
            "Пример: /addproduct stars | 100 Stars | 2 EUR | 10")
        return
    try:
        stock = int(parts[3])
        if stock < 0 or len(parts[1]) > 180 or len(parts[2]) > 60:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("Остаток должен быть целым числом от 0.")
        return
    with db() as c:
        c.execute("INSERT INTO products(category,name,price,stock,created_at) VALUES(?,?,?,?,?)",
                  (parts[0], parts[1], parts[2], stock, now()))
    await update.message.reply_text("✅ Товар добавлен.")

async def setstock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Нет доступа.")
        return
    try:
        product_id, stock = int(context.args[0]), int(context.args[1])
        if stock < 0: raise ValueError()
    except (ValueError, IndexError):
        await update.message.reply_text("Формат: /setstock ID количество")
        return
    with db() as c:
        cur = c.execute("UPDATE products SET stock=? WHERE id=?", (stock, product_id))
    await update.message.reply_text("✅ Остаток обновлён." if cur.rowcount else "Товар не найден.")

async def setprice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Нет доступа.")
        return
    raw = " ".join(context.args).split("|", 1)
    if len(raw) != 2 or not raw[0].strip() or not raw[1].strip():
        await update.message.reply_text("Формат: /setprice ID | новая цена")
        return
    try: product_id = int(raw[0].strip())
    except ValueError:
        await update.message.reply_text("ID должен быть числом."); return
    with db() as c:
        cur = c.execute("UPDATE products SET price=? WHERE id=?", (raw[1].strip(), product_id))
    await update.message.reply_text("✅ Цена обновлена." if cur.rowcount else "Товар не найден.")

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Нет доступа."); return
    try: uid = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Формат: /ban Telegram_ID"); return
    with db() as c:
        cur = c.execute("UPDATE users SET banned=1 WHERE user_id=?", (uid,))
    await update.message.reply_text("🚫 Пользователь заблокирован." if cur.rowcount else "Пользователь не найден.")

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Нет доступа."); return
    try: uid = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Формат: /unban Telegram_ID"); return
    with db() as c:
        cur = c.execute("UPDATE users SET banned=0 WHERE user_id=?", (uid,))
    await update.message.reply_text("✅ Пользователь разблокирован." if cur.rowcount else "Пользователь не найден.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Нет доступа."); return
    message = " ".join(context.args).strip()
    if not message:
        await update.message.reply_text("Формат: /broadcast текст сообщения")
        return
    context.application.bot_data["broadcast_pending"] = message
    await update.message.reply_text("Подтвердить рассылку всем пользователям?",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Отправить", callback_data="adm:broadcastconfirm"),
            InlineKeyboardButton("Отмена", callback_data="adm:broadcastcancel")]]))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    uid = q.from_user.id
    if data.startswith("adm:") and uid != ADMIN_ID:
        await q.edit_message_text("⛔ Нет доступа."); return

    if data.startswith("cat:"):
        category = data.split(":", 1)[1]
        if category not in CATEGORIES: return
        with db() as c:
            products = c.execute("SELECT * FROM products WHERE category=? AND active=1 ORDER BY id DESC", (category,)).fetchall()
        rows = [[InlineKeyboardButton(f"#{p['id']} {p['name']} — {p['price']} (остаток: {p['stock']})",
                                      callback_data=f"product:{p['id']}")] for p in products if p["stock"] > 0]
        rows.append([InlineKeyboardButton("⬅️ Категории", callback_data="home")])
        await q.edit_message_text(CATEGORIES[category] + "\n\n" + ("Выбери товар:" if rows and len(rows)>1 else "Пока нет товаров в наличии."),
                                  reply_markup=InlineKeyboardMarkup(rows))
    elif data == "home":
        await q.edit_message_text("Выбери категорию:", reply_markup=main_menu())
    elif data.startswith("product:"):
        try: pid = int(data.split(":")[1])
        except ValueError: return
        with db() as c:
            p = c.execute("SELECT * FROM products WHERE id=? AND active=1 AND stock>0", (pid,)).fetchone()
        if not p:
            await q.edit_message_text("Товар закончился или больше недоступен.", reply_markup=main_menu()); return
        await q.edit_message_text(f"🛍 {p['name']}\nЦена: {p['price']}\nОстаток: {p['stock']}\n\nСоздать заявку на покупку?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Заказать 1 шт.", callback_data=f"order:{pid}")],
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"cat:{p['category']}")]]))
    elif data.startswith("order:"):
        try: pid = int(data.split(":")[1])
        except ValueError: return
        with db() as c:
            p = c.execute("SELECT * FROM products WHERE id=? AND active=1 AND stock>0", (pid,)).fetchone()
            if not p:
                await q.edit_message_text("Товар закончился.", reply_markup=main_menu()); return
            cur = c.execute("INSERT INTO orders(user_id,product_id,quantity,total,status,created_at) VALUES(?,?,?,?,?,?)",
                            (uid, pid, 1, p["price"], "new", now()))
            oid = cur.lastrowid
        await q.edit_message_text(f"✅ Заявка #{oid} создана.\nТовар: {p['name']}\nЦена: {p['price']}\n\nАдминистратор свяжется с тобой для подтверждения заказа.",
            reply_markup=main_menu())
        try:
            await context.bot.send_message(ADMIN_ID, f"🆕 Новый заказ #{oid}\nПользователь: {uid} (@{q.from_user.username or 'без username'})\nТовар: {p['name']}\nЦена: {p['price']}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏳ В работу", callback_data=f"adm:status:{oid}:progress"),
                                                    InlineKeyboardButton("❌ Отклонить", callback_data=f"adm:status:{oid}:rejected")]]))
        except Exception: log.exception("Could not notify admin")
    elif data == "myorders":
        with db() as c:
            rows = c.execute("SELECT o.id,o.total,o.status,p.name FROM orders o JOIN products p ON p.id=o.product_id WHERE o.user_id=? ORDER BY o.id DESC LIMIT 10", (uid,)).fetchall()
        text = "📦 Твои заказы:\n\n" + ("\n".join(f"#{r['id']} {r['name']} — {r['total']} — {STATUSES.get(r['status'], r['status'])}" for r in rows) if rows else "Заказов пока нет.")
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ В магазин", callback_data="home")]]))
    elif data == "adm:stats":
        with db() as c:
            users = c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
            orders = c.execute("SELECT COUNT(*) n FROM orders").fetchone()["n"]
            new_orders = c.execute("SELECT COUNT(*) n FROM orders WHERE status='new'").fetchone()["n"]
            completed = c.execute("SELECT COUNT(*) n FROM orders WHERE status='done'").fetchone()["n"]
        await q.edit_message_text(f"📊 Статистика\nПользователей: {users}\nЗаказов: {orders}\nНовых: {new_orders}\nВыполнено: {completed}",
                                  reply_markup=admin_menu())
    elif data == "adm:orders:new" or data == "adm:orders":
        with db() as c:
            rows = c.execute("SELECT o.id,o.user_id,o.total,o.status,p.name FROM orders o JOIN products p ON p.id=o.product_id ORDER BY o.id DESC LIMIT 20").fetchall()
        if not rows:
            await q.edit_message_text("Заказов пока нет.", reply_markup=admin_menu()); return
        lines = ["📦 Последние заказы:"]
        buttons = []
        for r in rows:
            lines.append(f"#{r['id']} · {r['name']} · {r['total']} · user {r['user_id']} · {STATUSES.get(r['status'],r['status'])}")
            if r["status"] in ("new","progress"):
                buttons.append([InlineKeyboardButton(f"#{r['id']} ✅ Выполнен", callback_data=f"adm:status:{r['id']}:done"),
                                InlineKeyboardButton(f"#{r['id']} ❌ Отменить", callback_data=f"adm:status:{r['id']}:rejected")])
        buttons.append([InlineKeyboardButton("⬅️ Панель", callback_data="adm:menu")])
        await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("adm:status:"):
        try: _, _, oid, status = data.split(":")
        except ValueError: return
        if status not in STATUSES: return
        with db() as c:
            row = c.execute("SELECT user_id FROM orders WHERE id=?", (int(oid),)).fetchone()
            if not row:
                await q.edit_message_text("Заказ не найден."); return
            c.execute("UPDATE orders SET status=? WHERE id=?", (status, int(oid)))
        await q.edit_message_text(f"Заказ #{oid}: {STATUSES[status]}", reply_markup=admin_menu())
        try: await context.bot.send_message(row["user_id"], f"Статус заказа #{oid}: {STATUSES[status]}")
        except Exception: pass
    elif data == "adm:products":
        with db() as c:
            rows = c.execute("SELECT id,category,name,price,stock FROM products ORDER BY id DESC LIMIT 30").fetchall()
        text = "🛍 Товары:\n\n" + ("\n".join(f"#{p['id']} [{p['category']}] {p['name']} — {p['price']} · остаток {p['stock']}" for p in rows) if rows else "Товаров пока нет.")
        text += "\n\nКоманды:\n/addproduct категория | название | цена | остаток\n/setprice ID | цена\n/setstock ID количество"
        await q.edit_message_text(text, reply_markup=admin_menu())
    elif data == "adm:addhelp":
        await q.edit_message_text("Добавление товара командой:\n/addproduct категория | название | цена | остаток\n\nКатегории: numbers, stars, premium, nfts\nПример:\n/addproduct premium | Premium 1 месяц | 5 EUR | 10", reply_markup=admin_menu())
    elif data == "adm:users":
        with db() as c:
            rows = c.execute("SELECT user_id,username,full_name,banned FROM users ORDER BY joined_at DESC LIMIT 25").fetchall()
        text = "👥 Последние пользователи:\n\n" + ("\n".join(f"{r['user_id']} @{r['username'] or '—'} · {'🚫' if r['banned'] else '✅'}" for r in rows) if rows else "Пользователей пока нет.")
        text += "\n\nДля блокировки: /ban ID\nДля разблокировки: /unban ID"
        await q.edit_message_text(text, reply_markup=admin_menu())
    elif data == "adm:broadcasthelp":
        await q.edit_message_text("Рассылка:\n/broadcast текст сообщения\nПосле команды бот попросит подтверждение.", reply_markup=admin_menu())
    elif data == "adm:broadcastcancel":
        context.application.bot_data.pop("broadcast_pending", None)
        await q.edit_message_text("Рассылка отменена.", reply_markup=admin_menu())
    elif data == "adm:broadcastconfirm":
        message = context.application.bot_data.pop("broadcast_pending", None)
        if not message:
            await q.edit_message_text("Нет подготовленной рассылки.", reply_markup=admin_menu()); return
        with db() as c:
            ids = [r["user_id"] for r in c.execute("SELECT user_id FROM users WHERE banned=0").fetchall()]
        sent = 0
        for target in ids:
            try:
                await context.bot.send_message(target, message)
                sent += 1
                await asyncio.sleep(0.04)
            except Exception: pass
        await q.edit_message_text(f"Рассылка завершена: {sent} из {len(ids)}.", reply_markup=admin_menu())
    elif data == "adm:menu":
        await q.edit_message_text("⚙️ Панель администратора", reply_markup=admin_menu())

def main():
    if not TOKEN:
        raise RuntimeError("Set BOT_TOKEN in Render environment variables.")
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("health", health))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("addproduct", addproduct))
    app.add_handler(CommandHandler("setstock", setstock))
    app.add_handler(CommandHandler("setprice", setprice))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(button))
    log.info("VGRAM shop bot starting")
    app.run_polling(drop_pending_updates=False)

if __name__ == "__main__":
    main()
