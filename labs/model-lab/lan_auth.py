"""Invite-only LAN authentication for Haven Model Lab.

Stdlib-only. Passwords use scrypt with per-user salts. Session/invite tokens are
stored only as SHA-256 digests. This module does not send email or use a cloud
identity provider.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path

USERNAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,31}$")
ROLES = {"admin", "member"}
SESSION_SECONDS = 7 * 24 * 60 * 60
INVITE_SECONDS = 24 * 60 * 60
SCRYPT_N = 2 ** 14
SCRYPT_R = 8
SCRYPT_P = 2
SCRYPT_MAXMEM = 64 * 1024 * 1024


def _digest_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _password_hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=32,
        maxmem=SCRYPT_MAXMEM,
    )


def _validate_username(username: str) -> tuple[str, str]:
    if not isinstance(username, str):
        raise ValueError("Username required.")
    username = username.strip()
    if not USERNAME_RE.fullmatch(username):
        raise ValueError("Username must be 3–32 characters using letters, numbers, dot, underscore or hyphen.")
    return username, username.casefold()


def _validate_password(password: str) -> str:
    if not isinstance(password, str) or not 12 <= len(password) <= 256:
        raise ValueError("Password must be 12–256 characters.")
    return password


class AuthStore:
    def __init__(self, data_dir: Path):
        self.path = Path(data_dir).resolve() / "auth.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self._init()
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=5000")
        return db

    def _init(self):
        with self.lock, self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    username_key TEXT NOT NULL UNIQUE,
                    role TEXT NOT NULL CHECK(role IN ('admin','member')),
                    salt BLOB NOT NULL,
                    password_hash BLOB NOT NULL,
                    created_at REAL NOT NULL,
                    disabled INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS invites(
                    token_hash TEXT PRIMARY KEY,
                    role TEXT NOT NULL CHECK(role IN ('admin','member')),
                    created_by INTEGER NOT NULL REFERENCES users(id),
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    used_at REAL,
                    used_by INTEGER REFERENCES users(id)
                );
                CREATE TABLE IF NOT EXISTS sessions(
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    csrf TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS sessions_user_idx ON sessions(user_id);
                """
            )

    def setup_required(self) -> bool:
        with self.lock, self._connect() as db:
            return db.execute("SELECT 1 FROM users LIMIT 1").fetchone() is None

    def _public_user(self, row) -> dict:
        return {
            "id": int(row["id"]),
            "username": row["username"],
            "role": row["role"],
            "disabled": bool(row["disabled"]),
            "created_at": float(row["created_at"]),
        }

    def create_owner(self, username: str, password: str) -> dict:
        username, key = _validate_username(username)
        password = _validate_password(password)
        salt = secrets.token_bytes(16)
        digest = _password_hash(password, salt)
        now = time.time()
        with self.lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
                raise ValueError("Owner setup is already complete.")
            cur = db.execute(
                "INSERT INTO users(username,username_key,role,salt,password_hash,created_at) VALUES(?,?,?,?,?,?)",
                (username, key, "admin", salt, digest, now),
            )
            row = db.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
            db.commit()
            return self._public_user(row)

    def authenticate(self, username: str, password: str) -> dict | None:
        try:
            _, key = _validate_username(username)
            password = _validate_password(password)
        except ValueError:
            return None
        with self.lock, self._connect() as db:
            row = db.execute("SELECT * FROM users WHERE username_key=?", (key,)).fetchone()
        if not row or row["disabled"]:
            # Keep roughly the same password-work shape for unknown users.
            _password_hash(password, b"\0" * 16)
            return None
        candidate = _password_hash(password, bytes(row["salt"]))
        if not hmac.compare_digest(candidate, bytes(row["password_hash"])):
            return None
        return self._public_user(row)

    def create_session(self, user_id: int) -> tuple[str, str]:
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        now = time.time()
        with self.lock, self._connect() as db:
            db.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
            db.execute(
                "INSERT INTO sessions(token_hash,user_id,csrf,created_at,expires_at) VALUES(?,?,?,?,?)",
                (_digest_token(token), int(user_id), csrf, now, now + SESSION_SECONDS),
            )
        return token, csrf

    def session(self, token: str) -> dict | None:
        if not isinstance(token, str) or not token:
            return None
        now = time.time()
        with self.lock, self._connect() as db:
            row = db.execute(
                """SELECT u.*, s.csrf, s.expires_at
                   FROM sessions s JOIN users u ON u.id=s.user_id
                   WHERE s.token_hash=?""",
                (_digest_token(token),),
            ).fetchone()
            if not row or row["disabled"] or row["expires_at"] <= now:
                if row:
                    db.execute("DELETE FROM sessions WHERE token_hash=?", (_digest_token(token),))
                return None
            user = self._public_user(row)
            user["csrf"] = row["csrf"]
            return user

    def logout(self, token: str) -> None:
        if not token:
            return
        with self.lock, self._connect() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (_digest_token(token),))

    def create_invite(self, admin_id: int, role: str = "member", ttl_seconds: int = INVITE_SECONDS) -> str:
        if role not in ROLES:
            raise ValueError("Invalid invite role.")
        ttl_seconds = max(300, min(int(ttl_seconds), 7 * 24 * 60 * 60))
        token = secrets.token_urlsafe(32)
        now = time.time()
        with self.lock, self._connect() as db:
            actor = db.execute("SELECT role,disabled FROM users WHERE id=?", (int(admin_id),)).fetchone()
            if not actor or actor["disabled"] or actor["role"] != "admin":
                raise PermissionError("Administrator access required.")
            db.execute(
                "INSERT INTO invites(token_hash,role,created_by,created_at,expires_at) VALUES(?,?,?,?,?)",
                (_digest_token(token), role, int(admin_id), now, now + ttl_seconds),
            )
        return token

    def accept_invite(self, token: str, username: str, password: str) -> dict:
        if not isinstance(token, str) or len(token) < 20:
            raise ValueError("Invalid or expired invite.")
        username, key = _validate_username(username)
        password = _validate_password(password)
        salt = secrets.token_bytes(16)
        digest = _password_hash(password, salt)
        now = time.time()
        token_hash = _digest_token(token)
        with self.lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            invite = db.execute(
                "SELECT * FROM invites WHERE token_hash=? AND used_at IS NULL AND expires_at>?",
                (token_hash, now),
            ).fetchone()
            if not invite:
                raise ValueError("Invalid or expired invite.")
            try:
                cur = db.execute(
                    "INSERT INTO users(username,username_key,role,salt,password_hash,created_at) VALUES(?,?,?,?,?,?)",
                    (username, key, invite["role"], salt, digest, now),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("That username is already in use.") from exc
            db.execute(
                "UPDATE invites SET used_at=?,used_by=? WHERE token_hash=? AND used_at IS NULL",
                (now, cur.lastrowid, token_hash),
            )
            row = db.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
            db.commit()
            return self._public_user(row)

    def list_users(self, admin_id: int) -> list[dict]:
        with self.lock, self._connect() as db:
            actor = db.execute("SELECT role,disabled FROM users WHERE id=?", (int(admin_id),)).fetchone()
            if not actor or actor["disabled"] or actor["role"] != "admin":
                raise PermissionError("Administrator access required.")
            rows = db.execute("SELECT * FROM users ORDER BY id").fetchall()
            return [self._public_user(row) for row in rows]

    def set_disabled(self, admin_id: int, user_id: int, disabled: bool) -> dict:
        admin_id, user_id = int(admin_id), int(user_id)
        if admin_id == user_id and disabled:
            raise ValueError("You cannot disable your own account.")
        with self.lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            actor = db.execute("SELECT role,disabled FROM users WHERE id=?", (admin_id,)).fetchone()
            target = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if not actor or actor["disabled"] or actor["role"] != "admin":
                raise PermissionError("Administrator access required.")
            if not target:
                raise ValueError("Unknown user.")
            if disabled and target["role"] == "admin":
                count = db.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND disabled=0").fetchone()[0]
                if count <= 1:
                    raise ValueError("At least one enabled administrator must remain.")
            db.execute("UPDATE users SET disabled=? WHERE id=?", (1 if disabled else 0, user_id))
            if disabled:
                db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
            row = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            db.commit()
            return self._public_user(row)
