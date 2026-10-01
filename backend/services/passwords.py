"""Password hashing with stdlib scrypt. The hash is never sent to the browser."""

from __future__ import annotations

import hashlib
import hmac
import secrets

_N = 2**14
_R = 8
_P = 1
_DKLEN = 32
_MAXMEM = 64 * 1024 * 1024


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_N,
        r=_R,
        p=_P,
        dklen=_DKLEN,
        maxmem=_MAXMEM,
    )
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt_hex, digest_hex = stored.split("$")
        if algo != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(bytes.fromhex(digest_hex)),
            maxmem=_MAXMEM,
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


# Used when the email does not exist, so login timing does not reveal that.
DUMMY_PASSWORD_HASH = hash_password("not-a-real-user-password")
