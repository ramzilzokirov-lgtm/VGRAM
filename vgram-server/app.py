import os
import hashlib
import hmac
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

DB_PATH = os.getenv("VGRAM_DB_PATH", "vgram.db")
ADMIN_KEY = os.getenv("VGRAM_ADMIN_KEY", "")
app = FastAPI(title="VGRAM Server Starter", version="0.2.0")
_bot_process = None


@contextmanager
def db() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def init_db():
    with db() as c:
        c.execute(
            "CREATE TABLE IF NOT EXISTS users (account_id TEXT PRIMARY KEY, vgram_id TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1)"
        )
        c.execute(
            "CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id TEXT NOT NULL, recipient_id TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient_id, id)")
        c.execute("""CREATE TABLE IF NOT EXISTS auth_credentials (
            username TEXT PRIMARY KEY,
            account_id TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            vgram_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS star_wallets (
            vgram_id TEXT PRIMARY KEY,
            balance INTEGER NOT NULL DEFAULT 0 CHECK(balance >= 0),
            updated_at TEXT NOT NULL
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS star_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vgram_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            reason TEXT NOT NULL,
            event_key TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        )""")
        c.execute(
            """CREATE TABLE IF NOT EXISTS user_badges (
                vgram_id TEXT NOT NULL,
                badge_code TEXT NOT NULL,
                label TEXT NOT NULL,
                issued_by TEXT NOT NULL,
                issued_at TEXT NOT NULL,
                PRIMARY KEY(vgram_id, badge_code)
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS nft_items (
                nft_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                price_minor INTEGER NOT NULL CHECK(price_minor >= 0),
                currency TEXT NOT NULL,
                max_quantity INTEGER NOT NULL CHECK(max_quantity >= 0),
                available_quantity INTEGER NOT NULL CHECK(
                    available_quantity >= 0 AND available_quantity <= max_quantity
                ),
                active INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            )"""
        )


@app.on_event("startup")
def startup():
    # The Telegram bot runs only in the dedicated vgram-shop-bot worker.
    # Do not start a second getUpdates poller from the HTTP API service.
    init_db()


def auth(key):
    if not ADMIN_KEY:
        raise HTTPException(503, "VGRAM_ADMIN_KEY is not configured")
    if not key or not secrets.compare_digest(key, ADMIN_KEY):
        raise HTTPException(401, "Unauthorized")


def award_signup_stars(c, vgram_id: str):
    # Idempotent: one registration bonus per VGRAM account, never on login.
    event_key = f"signup:{vgram_id}"
    cur = c.execute(
        "INSERT OR IGNORE INTO star_ledger(vgram_id,amount,reason,event_key,created_at) VALUES(?,?,?,?,?)",
        (vgram_id, 1000, "registration_bonus", event_key, now_iso()),
    )
    c.execute(
        "INSERT OR IGNORE INTO star_wallets(vgram_id,balance,updated_at) VALUES(?,0,?)",
        (vgram_id, now_iso()),
    )
    if cur.rowcount:
        c.execute(
            "UPDATE star_wallets SET balance=balance+1000,updated_at=? WHERE vgram_id=?",
            (now_iso(), vgram_id),
        )


def new_id(c):
    for _ in range(20):
        value = "VG-" + secrets.token_hex(4).upper()
        if not c.execute("SELECT 1 FROM users WHERE vgram_id=?", (value,)).fetchone():
            return value
    raise HTTPException(503, "Could not allocate ID; retry")


class UserIn(BaseModel):
    account_id: str = Field(min_length=1, max_length=128)


class AuthIn(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=10, max_length=128)


class ChatMessageIn(BaseModel):
    recipient_id: str = Field(min_length=1, max_length=32)
    body: str = Field(min_length=1, max_length=4000)


class MessageIn(BaseModel):
    sender_id: str = Field(min_length=1, max_length=32)
    recipient_id: str = Field(min_length=1, max_length=32)
    body: str = Field(min_length=1, max_length=4000)


class NFTItemIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=100)
    # Price is stored in the currency's smallest unit (e.g. cents for EUR).
    price_minor: int = Field(ge=0, le=100_000_000_000)
    currency: str = Field(min_length=1, max_length=12)
    # max_quantity is the verified supply/limit, not an arbitrary made-up stock.
    max_quantity: int = Field(ge=0, le=1_000_000_000)
    # available_quantity must represent currently sellable inventory.
    available_quantity: int = Field(ge=0, le=1_000_000_000)
    active: bool = True


@app.get("/health")
def health():
    return {"ok": True, "service": "vgram-server", "version": "0.3.0"}


def create_session(c, vgram_id: str):
    token = secrets.token_urlsafe(32)
    c.execute("INSERT INTO sessions(token,vgram_id,created_at) VALUES(?,?,?)",
              (token, vgram_id, now_iso()))
    return token


def require_session(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Please sign in")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(401, "Please sign in")
    with db() as c:
        row = c.execute(
            "SELECT s.vgram_id,u.active FROM sessions s JOIN users u ON u.vgram_id=s.vgram_id WHERE s.token=?",
            (token,),
        ).fetchone()
    if not row:
        raise HTTPException(401, "Session expired; sign in again")
    if not row["active"]:
        raise HTTPException(403, "Account inactive")
    return row["vgram_id"]


@app.post("/auth/register")
def register(data: AuthIn):
    username = data.username.lower()
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", data.password.encode("utf-8"), bytes.fromhex(salt), 200_000
    ).hex()
    with db() as c:
        if c.execute("SELECT 1 FROM auth_credentials WHERE username=?", (username,)).fetchone():
            raise HTTPException(409, "This username is already registered")
        vid = new_id(c)
        created = now_iso()
        c.execute("INSERT INTO users(account_id,vgram_id,created_at,active) VALUES(?,?,?,1)",
                  (username, vid, created))
        c.execute("INSERT INTO auth_credentials(username,account_id,password_hash,salt) VALUES(?,?,?,?)",
                  (username, username, password_hash, salt))
        token = create_session(c, vid)
        award_signup_stars(c, vid)
    return {"access_token": token, "token_type": "bearer", "vgram_id": vid, "bonus_stars": 1000}


@app.post("/auth/login")
def login(data: AuthIn):
    username = data.username.lower()
    with db() as c:
        row = c.execute(
            """SELECT a.password_hash,a.salt,u.vgram_id,u.active
               FROM auth_credentials a JOIN users u ON u.account_id=a.account_id
               WHERE a.username=?""", (username,)
        ).fetchone()
        if not row:
            raise HTTPException(401, "Incorrect username or password")
        candidate = hashlib.pbkdf2_hmac(
            "sha256", data.password.encode("utf-8"), bytes.fromhex(row["salt"]), 200_000
        ).hex()
        if not hmac.compare_digest(candidate, row["password_hash"]):
            raise HTTPException(401, "Incorrect username or password")
        if not row["active"]:
            raise HTTPException(403, "Account inactive")
        token = create_session(c, row["vgram_id"])
    return {"access_token": token, "token_type": "bearer", "vgram_id": row["vgram_id"]}



@app.get("/account/wallet")
def account_wallet(authorization: str | None = Header(default=None)):
    vgram_id = require_session(authorization)
    with db() as c:
        row = c.execute(
            "SELECT balance FROM star_wallets WHERE vgram_id=?", (vgram_id,)
        ).fetchone()
        if not row:
            return {"vgram_id": vgram_id, "balance": 0, "currency": "VGRAM_STARS"}
        history = c.execute(
            "SELECT amount,reason,created_at FROM star_ledger WHERE vgram_id=? ORDER BY id DESC LIMIT 50",
            (vgram_id,),
        ).fetchall()
        return {"vgram_id": vgram_id, "balance": row["balance"],
                "currency": "VGRAM_STARS", "transactions": [dict(x) for x in history]}


@app.post("/chat/send")
def chat_send(data: ChatMessageIn, authorization: str | None = Header(default=None)):
    sender_id = require_session(authorization)
    recipient_id = data.recipient_id.strip().upper()
    with db() as c:
        recipient = c.execute("SELECT active FROM users WHERE vgram_id=?", (recipient_id,)).fetchone()
        if not recipient:
            raise HTTPException(404, "Recipient VGRAM ID not found")
        if not recipient["active"]:
            raise HTTPException(403, "Recipient account inactive")
        cur = c.execute(
            "INSERT INTO messages(sender_id,recipient_id,body,created_at) VALUES(?,?,?,?)",
            (sender_id, recipient_id, data.body.strip(), now_iso()),
        )
        return {"message_id": cur.lastrowid, "status": "stored"}


@app.get("/chat/inbox")
def chat_inbox(limit: int = 50, authorization: str | None = Header(default=None)):
    recipient_id = require_session(authorization)
    if not 1 <= limit <= 100:
        raise HTTPException(400, "limit must be 1..100")
    with db() as c:
        rows = c.execute(
            "SELECT id,sender_id,recipient_id,body,created_at FROM messages WHERE recipient_id=? ORDER BY id DESC LIMIT ?",
            (recipient_id, limit),
        ).fetchall()
    return {"messages": [dict(row) for row in rows]}


@app.post("/admin/users")
def create_or_get_user(data: UserIn, x_vgram_admin_key: str | None = Header(default=None)):
    auth(x_vgram_admin_key)
    with db() as c:
        row = c.execute(
            "SELECT account_id,vgram_id,created_at,active FROM users WHERE account_id=?",
            (data.account_id,),
        ).fetchone()
        if row:
            return dict(row)
        vid, created = new_id(c), now_iso()
        c.execute(
            "INSERT INTO users(account_id,vgram_id,created_at,active) VALUES(?,?,?,1)",
            (data.account_id, vid, created),
        )
        return {"account_id": data.account_id, "vgram_id": vid, "created_at": created, "active": 1}


@app.get("/admin/users/{account_id}")
def get_user(account_id: str, x_vgram_admin_key: str | None = Header(default=None)):
    auth(x_vgram_admin_key)
    with db() as c:
        row = c.execute(
            "SELECT account_id,vgram_id,created_at,active FROM users WHERE account_id=?",
            (account_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "User not found")
        return dict(row)


@app.post("/messages")
def send_message(data: MessageIn, x_vgram_admin_key: str | None = Header(default=None)):
    # Admin-key protection is temporary; replace with authenticated per-user sessions before public use.
    auth(x_vgram_admin_key)
    with db() as c:
        s = c.execute("SELECT active FROM users WHERE vgram_id=?", (data.sender_id,)).fetchone()
        r = c.execute("SELECT active FROM users WHERE vgram_id=?", (data.recipient_id,)).fetchone()
        if not s or not r:
            raise HTTPException(404, "Sender or recipient not found")
        if not s["active"] or not r["active"]:
            raise HTTPException(403, "Account inactive")
        cur = c.execute(
            "INSERT INTO messages(sender_id,recipient_id,body,created_at) VALUES(?,?,?,?)",
            (data.sender_id, data.recipient_id, data.body, now_iso()),
        )
        return {"message_id": cur.lastrowid, "status": "stored"}


@app.get("/admin/messages/{vgram_id}")
def get_messages(vgram_id: str, limit: int = 50, x_vgram_admin_key: str | None = Header(default=None)):
    auth(x_vgram_admin_key)
    if not 1 <= limit <= 100:
        raise HTTPException(400, "limit must be 1..100")
    with db() as c:
        rows = c.execute(
            "SELECT id,sender_id,recipient_id,body,created_at FROM messages WHERE recipient_id=? ORDER BY id DESC LIMIT ?",
            (vgram_id, limit),
        ).fetchall()
        return {"messages": [dict(x) for x in rows]}


@app.post("/admin/users/{account_id}/deactivate")
def deactivate(account_id: str, x_vgram_admin_key: str | None = Header(default=None)):
    auth(x_vgram_admin_key)
    with db() as c:
        cur = c.execute("UPDATE users SET active=0 WHERE account_id=?", (account_id,))
        if not cur.rowcount:
            raise HTTPException(404, "User not found")
        return {"account_id": account_id, "active": False}


@app.get("/shop/nfts")
def list_nfts(limit: int = 50):
    """Public catalogue: only active items with verified available stock."""
    if not 1 <= limit <= 100:
        raise HTTPException(400, "limit must be 1..100")
    with db() as c:
        rows = c.execute(
            """SELECT nft_id,title,source,price_minor,currency,max_quantity,
                      available_quantity,active,updated_at
               FROM nft_items
               WHERE active=1 AND available_quantity>0
               ORDER BY updated_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return {"items": [dict(row) for row in rows]}


@app.get("/admin/nfts")
def admin_list_nfts(x_vgram_admin_key: str | None = Header(default=None)):
    """Admin inventory view. Requires VGRAM_ADMIN_KEY."""
    auth(x_vgram_admin_key)
    with db() as c:
        rows = c.execute(
            """SELECT nft_id,title,source,price_minor,currency,max_quantity,
                      available_quantity,active,updated_at
               FROM nft_items ORDER BY updated_at DESC"""
        ).fetchall()
        return {"items": [dict(row) for row in rows]}


@app.put("/admin/nfts/{nft_id}")
def upsert_nft(
    nft_id: str,
    data: NFTItemIn,
    x_vgram_admin_key: str | None = Header(default=None),
):
    """Create/update an NFT listing with explicit, validated stock quantities."""
    auth(x_vgram_admin_key)
    if not nft_id or len(nft_id) > 160:
        raise HTTPException(400, "nft_id must be 1..160 characters")
    if data.available_quantity > data.max_quantity:
        raise HTTPException(400, "available_quantity cannot exceed max_quantity")
    with db() as c:
        c.execute(
            """INSERT INTO nft_items
               (nft_id,title,source,price_minor,currency,max_quantity,
                available_quantity,active,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?)
               ON CONFLICT(nft_id) DO UPDATE SET
                 title=excluded.title,
                 source=excluded.source,
                 price_minor=excluded.price_minor,
                 currency=excluded.currency,
                 max_quantity=excluded.max_quantity,
                 available_quantity=excluded.available_quantity,
                 active=excluded.active,
                 updated_at=excluded.updated_at""",
            (
                nft_id,
                data.title,
                data.source,
                data.price_minor,
                data.currency,
                data.max_quantity,
                data.available_quantity,
                int(data.active),
                now_iso(),
            ),
        )
        row = c.execute(
            """SELECT nft_id,title,source,price_minor,currency,max_quantity,
                      available_quantity,active,updated_at
               FROM nft_items WHERE nft_id=?""",
            (nft_id,),
        ).fetchone()
        return dict(row)



class BadgeIn(BaseModel):
    label: str = Field(min_length=1, max_length=40)


@app.get("/users/{vgram_id}/badges")
def list_user_badges(vgram_id: str):
    """Public VGRAM badge list for profile display."""
    with db() as c:
        user = c.execute("SELECT vgram_id FROM users WHERE vgram_id=?", (vgram_id,)).fetchone()
        if not user:
            raise HTTPException(404, "User not found")
        rows = c.execute(
            "SELECT badge_code,label,issued_by,issued_at FROM user_badges WHERE vgram_id=? ORDER BY issued_at",
            (vgram_id,),
        ).fetchall()
        return {"vgram_id": vgram_id, "badges": [dict(row) for row in rows]}


@app.get("/users/telegram/{telegram_id}/badges")
def list_telegram_user_badges(telegram_id: str):
    """Read VGRAM badges linked by the owner to a Telegram numeric user ID."""
    if not telegram_id.isdigit() or len(telegram_id) > 20:
        raise HTTPException(400, "Invalid Telegram user ID")
    account_id = f"telegram:{telegram_id}"
    with db() as c:
        user = c.execute("SELECT vgram_id FROM users WHERE account_id=?", (account_id,)).fetchone()
        if not user:
            return {"telegram_id": telegram_id, "badges": []}
        rows = c.execute(
            "SELECT badge_code,label,issued_at FROM user_badges WHERE vgram_id=? ORDER BY issued_at",
            (user["vgram_id"],),
        ).fetchall()
        return {"telegram_id": telegram_id, "vgram_id": user["vgram_id"],
                "badges": [dict(row) for row in rows]}


@app.put("/admin/users/{vgram_id}/badges/{badge_code}")
def issue_user_badge(
    vgram_id: str,
    badge_code: str,
    data: BadgeIn,
    x_vgram_admin_key: str | None = Header(default=None),
):
    """Issue/replace a badge. Requires the private owner/admin key."""
    auth(x_vgram_admin_key)
    code = badge_code.strip().upper()
    allowed = {"TESTER", "OG", "FRIENDS", "TEAM", "DEVELOPER", "FOUNDER"}
    if code not in allowed:
        raise HTTPException(400, "Unsupported badge code")
    with db() as c:
        user = c.execute("SELECT vgram_id FROM users WHERE vgram_id=?", (vgram_id,)).fetchone()
        if not user:
            raise HTTPException(404, "User not found")
        c.execute(
            """INSERT INTO user_badges(vgram_id,badge_code,label,issued_by,issued_at)
               VALUES(?,?,?,?,?)
               ON CONFLICT(vgram_id,badge_code) DO UPDATE SET
                 label=excluded.label, issued_by=excluded.issued_by, issued_at=excluded.issued_at""",
            (vgram_id, code, data.label.strip(), "project-owner", now_iso()),
        )
        return {"ok": True, "vgram_id": vgram_id, "badge_code": code, "label": data.label.strip()}


@app.delete("/admin/users/{vgram_id}/badges/{badge_code}")
def revoke_user_badge(
    vgram_id: str,
    badge_code: str,
    x_vgram_admin_key: str | None = Header(default=None),
):
    """Revoke a badge using the private owner/admin key."""
    auth(x_vgram_admin_key)
    with db() as c:
        cur = c.execute(
            "DELETE FROM user_badges WHERE vgram_id=? AND badge_code=?",
            (vgram_id, badge_code.strip().upper()),
        )
        if not cur.rowcount:
            raise HTTPException(404, "Badge not found")
        return {"ok": True, "vgram_id": vgram_id, "badge_code": badge_code.strip().upper()}


@app.post("/admin/nfts/restore-stock")
def restore_nft_stock(x_vgram_admin_key: str | None = Header(default=None)):
    """Restore active listings to their configured max_quantity; never invent supply."""
    auth(x_vgram_admin_key)
    with db() as c:
        cur = c.execute(
            """UPDATE nft_items
               SET available_quantity=max_quantity, active=1, updated_at=?
               WHERE max_quantity > 0""",
            (now_iso(),),
        )
        count = cur.rowcount
        total = c.execute(
            "SELECT COALESCE(SUM(available_quantity),0) AS quantity FROM nft_items WHERE active=1"
        ).fetchone()["quantity"]
        return {"ok": True, "restored_listings": count, "available_quantity_total": total}

# VGRAM native account and private chat API.
from chat_api import router as chat_router
app.include_router(chat_router)
