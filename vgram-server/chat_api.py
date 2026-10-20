import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()
DB_PATH = os.getenv("VGRAM_DB_PATH", "vgram.db")


def db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_schema():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            account_id TEXT PRIMARY KEY, vgram_id TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
            username TEXT, password_hash TEXT NOT NULL DEFAULT ''
        )""")
        for sql in (
            "ALTER TABLE users ADD COLUMN username TEXT",
            "ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''",
        ):
            try:
                c.execute(sql)
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_vgram_username ON users(username)")
        c.execute("""CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY, vgram_id TEXT NOT NULL,
            created_at TEXT NOT NULL, expires_at TEXT NOT NULL
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id TEXT NOT NULL,
            recipient_id TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_vgram_messages_recipient ON messages(recipient_id,id)")


def make_id(c):
    for _ in range(30):
        vid = "VG-" + secrets.token_hex(4).upper()
        if not c.execute("SELECT 1 FROM users WHERE vgram_id=?", (vid,)).fetchone():
            return vid
    raise HTTPException(503, "Could not allocate VGRAM ID; retry")


def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
    return salt.hex() + ":" + digest.hex()


def verify_password(password, stored):
    try:
        salt, digest = stored.split(":", 1)
        candidate = hash_password(password, bytes.fromhex(salt)).split(":", 1)[1]
        return hmac.compare_digest(candidate, digest)
    except (ValueError, TypeError):
        return False


def require_user(authorization):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer token required")
    token = authorization[7:].strip()
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with db() as c:
        row = c.execute("""SELECT u.username,u.vgram_id,u.active,s.expires_at
            FROM sessions s JOIN users u ON u.vgram_id=s.vgram_id
            WHERE s.token_hash=?""", (token_hash,)).fetchone()
        if not row:
            raise HTTPException(401, "Invalid session")
        if row["expires_at"] <= now():
            c.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))
            raise HTTPException(401, "Session expired")
        if not row["active"]:
            raise HTTPException(403, "Account inactive")
        return dict(row)


def new_session(c, vgram_id):
    token = secrets.token_urlsafe(48)
    expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(timespec="seconds")
    c.execute("INSERT INTO sessions(token_hash,vgram_id,created_at,expires_at) VALUES(?,?,?,?)",
              (hashlib.sha256(token.encode()).hexdigest(), vgram_id, now(), expires))
    return token, expires


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=10, max_length=256)


class LoginIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=256)


class SendIn(BaseModel):
    recipient_id: str = Field(min_length=10, max_length=32)
    body: str = Field(min_length=1, max_length=4000)


@router.post("/auth/register")
def register(data: RegisterIn):
    ensure_schema()
    username = data.username.lower()
    with db() as c:
        if c.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            raise HTTPException(409, "Username already taken")
        vid, created = make_id(c), now()
        try:
            c.execute("""INSERT INTO users(account_id,vgram_id,created_at,active,username,password_hash)
                         VALUES(?,?,?,1,?,?)""",
                      (username, vid, created, username, hash_password(data.password)))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Username already taken")
        token, expires = new_session(c, vid)
        return {"username": username, "vgram_id": vid, "access_token": token,
                "token_type": "Bearer", "expires_at": expires}


@router.post("/auth/login")
def login(data: LoginIn):
    ensure_schema()
    with db() as c:
        row = c.execute("SELECT username,vgram_id,password_hash,active FROM users WHERE username=?",
                        (data.username.lower(),)).fetchone()
        if not row or not verify_password(data.password, row["password_hash"]):
            raise HTTPException(401, "Incorrect username or password")
        if not row["active"]:
            raise HTTPException(403, "Account inactive")
        token, expires = new_session(c, row["vgram_id"])
        return {"username": row["username"], "vgram_id": row["vgram_id"],
                "access_token": token, "token_type": "Bearer", "expires_at": expires}


@router.get("/account/me")
def me(authorization: str | None = Header(default=None)):
    ensure_schema()
    user = require_user(authorization)
    return {"username": user["username"], "vgram_id": user["vgram_id"],
            "active": bool(user["active"]), "expires_at": user["expires_at"]}


@router.post("/auth/logout")
def logout(authorization: str | None = Header(default=None)):
    ensure_schema()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer token required")
    token_hash = hashlib.sha256(authorization[7:].strip().encode()).hexdigest()
    with db() as c:
        c.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))
    return {"ok": True}


@router.post("/chat/send")
def send(data: SendIn, authorization: str | None = Header(default=None)):
    ensure_schema()
    user = require_user(authorization)
    with db() as c:
        recipient = c.execute("SELECT active FROM users WHERE vgram_id=?", (data.recipient_id,)).fetchone()
        if not recipient:
            raise HTTPException(404, "Recipient not found")
        if not recipient["active"]:
            raise HTTPException(403, "Recipient account inactive")
        cur = c.execute("INSERT INTO messages(sender_id,recipient_id,body,created_at) VALUES(?,?,?,?)",
                        (user["vgram_id"], data.recipient_id, data.body, now()))
        return {"message_id": cur.lastrowid, "status": "stored"}


@router.get("/chat/inbox")
def inbox(after_id: int = 0, limit: int = 50,
          authorization: str | None = Header(default=None)):
    ensure_schema()
    user = require_user(authorization)
    if after_id < 0 or not 1 <= limit <= 100:
        raise HTTPException(400, "after_id must be >=0 and limit must be 1..100")
    with db() as c:
        rows = c.execute("""SELECT id,sender_id,recipient_id,body,created_at FROM messages
            WHERE recipient_id=? AND id>? ORDER BY id ASC LIMIT ?""",
            (user["vgram_id"], after_id, limit)).fetchall()
    return {"messages": [dict(row) for row in rows]}


@router.get("/chat/with/{other_id}")
def conversation(other_id: str, before_id: int | None = None, limit: int = 50,
                 authorization: str | None = Header(default=None)):
    ensure_schema()
    user = require_user(authorization)
    if not 1 <= limit <= 100:
        raise HTTPException(400, "limit must be 1..100")
    with db() as c:
        if not c.execute("SELECT 1 FROM users WHERE vgram_id=? AND active=1", (other_id,)).fetchone():
            raise HTTPException(404, "User not found")
        before = before_id if before_id is not None else 9223372036854775807
        rows = c.execute("""SELECT id,sender_id,recipient_id,body,created_at FROM messages
            WHERE id<? AND ((sender_id=? AND recipient_id=?) OR (sender_id=? AND recipient_id=?))
            ORDER BY id DESC LIMIT ?""",
            (before, user["vgram_id"], other_id, other_id, user["vgram_id"], limit)).fetchall()
    return {"messages": [dict(row) for row in reversed(rows)]}


@router.get("/users/{vgram_id}")
def find_user(vgram_id: str, authorization: str | None = Header(default=None)):
    ensure_schema()
    require_user(authorization)
    with db() as c:
        row = c.execute("SELECT username,vgram_id FROM users WHERE vgram_id=? AND active=1",
                        (vgram_id,)).fetchone()
    if not row:
        raise HTTPException(404, "User not found")
    return dict(row)
