import os
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
    init_db()


def auth(key):
    if not ADMIN_KEY:
        raise HTTPException(503, "VGRAM_ADMIN_KEY is not configured")
    if not key or not secrets.compare_digest(key, ADMIN_KEY):
        raise HTTPException(401, "Unauthorized")


def new_id(c):
    for _ in range(20):
        value = "VG-" + secrets.token_hex(4).upper()
        if not c.execute("SELECT 1 FROM users WHERE vgram_id=?", (value,)).fetchone():
            return value
    raise HTTPException(503, "Could not allocate ID; retry")


class UserIn(BaseModel):
    account_id: str = Field(min_length=1, max_length=128)


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
    return {"ok": True, "service": "vgram-server", "version": "0.2.0"}


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


# VGRAM native account and private chat API.
from chat_api import router as chat_router
app.include_router(chat_router)
