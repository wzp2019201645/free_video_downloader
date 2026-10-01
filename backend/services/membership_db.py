"""SQLite persistence for accounts, membership, and processed Stripe events."""

from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from pathlib import Path

import billing_config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS memberships (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    stripe_customer_id TEXT UNIQUE,
    stripe_subscription_id TEXT UNIQUE,
    status TEXT NOT NULL,
    price_id TEXT NOT NULL DEFAULT '',
    current_period_end INTEGER,
    cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS stripe_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    processed_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS checkout_sessions (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    idempotency_key TEXT NOT NULL,
    session_id TEXT,
    updated_at INTEGER NOT NULL
);
"""


def _row(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


class MembershipDB:
    def __init__(self, path: Path | None = None):
        self.path = Path(path or billing_config.DB_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(_SCHEMA)
                conn.commit()
            finally:
                conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def create_user(self, email: str, password_hash: str) -> dict:
        user_id = uuid.uuid4().hex
        now = int(time.time())
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                    (user_id, email, password_hash, now),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError("该邮箱已注册") from exc
            finally:
                conn.close()
        user = self.get_user_by_id(user_id)
        if user is None:
            raise RuntimeError("注册后读取用户失败")
        return user

    def get_user_by_id(self, user_id: str) -> dict | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                return _row(row)
            finally:
                conn.close()

    def get_user_by_email(self, email: str) -> dict | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
                return _row(row)
            finally:
                conn.close()

    def get_membership(self, user_id: str) -> dict | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM memberships WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                return _row(row)
            finally:
                conn.close()

    def get_membership_by_customer(self, customer_id: str | None) -> dict | None:
        if not customer_id:
            return None
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM memberships WHERE stripe_customer_id = ?",
                    (customer_id,),
                ).fetchone()
                return _row(row)
            finally:
                conn.close()

    def get_membership_by_subscription(self, subscription_id: str | None) -> dict | None:
        if not subscription_id:
            return None
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM memberships WHERE stripe_subscription_id = ?",
                    (subscription_id,),
                ).fetchone()
                return _row(row)
            finally:
                conn.close()

    def set_customer_id(self, user_id: str, customer_id: str) -> None:
        now = int(time.time())
        with self._lock:
            conn = self._connect()
            try:
                existing = conn.execute(
                    "SELECT user_id FROM memberships WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                if existing:
                    conn.execute(
                        "UPDATE memberships SET stripe_customer_id = ?, updated_at = ? WHERE user_id = ?",
                        (customer_id, now, user_id),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO memberships (
                            user_id, stripe_customer_id, stripe_subscription_id, status,
                            price_id, current_period_end, cancel_at_period_end, updated_at
                        ) VALUES (?, ?, NULL, 'none', '', NULL, 0, ?)
                        """,
                        (user_id, customer_id, now),
                    )
                conn.commit()
            finally:
                conn.close()

    def upsert_membership(
        self,
        user_id: str,
        *,
        customer_id: str | None,
        subscription_id: str | None,
        status: str,
        price_id: str,
        period_end: int | None,
        cancel_at_period_end: bool,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        own = conn is None
        if own:
            self._lock.acquire()
            conn = self._connect()
        assert conn is not None
        try:
            conn.execute(
                """
                INSERT INTO memberships (
                    user_id, stripe_customer_id, stripe_subscription_id, status, price_id,
                    current_period_end, cancel_at_period_end, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    stripe_customer_id = COALESCE(excluded.stripe_customer_id, memberships.stripe_customer_id),
                    stripe_subscription_id = COALESCE(excluded.stripe_subscription_id, memberships.stripe_subscription_id),
                    status = excluded.status,
                    price_id = excluded.price_id,
                    current_period_end = excluded.current_period_end,
                    cancel_at_period_end = excluded.cancel_at_period_end,
                    updated_at = excluded.updated_at
                """,
                (
                    user_id,
                    customer_id or None,
                    subscription_id or None,
                    status,
                    price_id,
                    period_end,
                    1 if cancel_at_period_end else 0,
                    int(time.time()),
                ),
            )
            if own:
                conn.commit()
        finally:
            if own:
                conn.close()
                self._lock.release()

    def get_checkout(self, user_id: str) -> dict | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM checkout_sessions WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                return _row(row)
            finally:
                conn.close()

    def save_checkout(self, user_id: str, idempotency_key: str, session_id: str | None) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO checkout_sessions (user_id, idempotency_key, session_id, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        idempotency_key = excluded.idempotency_key,
                        session_id = excluded.session_id,
                        updated_at = excluded.updated_at
                    """,
                    (user_id, idempotency_key, session_id, int(time.time())),
                )
                conn.commit()
            finally:
                conn.close()

    def process_once(self, event_id: str, event_type: str, mutation) -> bool:
        """Apply mutation and record the event id in one transaction.

        A repeated Stripe delivery sees the event id and does nothing.
        A crash before commit leaves no event id, so Stripe can retry.
        """
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                exists = conn.execute(
                    "SELECT 1 FROM stripe_events WHERE event_id = ?",
                    (event_id,),
                ).fetchone()
                if exists:
                    conn.rollback()
                    return False
                if mutation:
                    mutation(conn)
                conn.execute(
                    "INSERT INTO stripe_events (event_id, event_type, processed_at) VALUES (?, ?, ?)",
                    (event_id, event_type, int(time.time())),
                )
                conn.commit()
                return True
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def apply_now(self, mutation) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                mutation(conn)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()


_db: MembershipDB | None = None


def get_db() -> MembershipDB:
    global _db
    if _db is None:
        _db = MembershipDB()
    return _db
