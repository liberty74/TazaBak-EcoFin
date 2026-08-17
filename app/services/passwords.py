"""Password hashing helpers for local account sign-in.

Hashes use PBKDF2-HMAC-SHA256 with a unique random salt. Passwords are never
stored or logged in plaintext.
"""

from __future__ import annotations

import base64
import hashlib
import secrets


_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _ITERATIONS
    )
    return "$".join(
        (
            _ALGORITHM,
            str(_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        )
    )


def verify_password(password: str, encoded_hash: str | None) -> bool:
    if not encoded_hash:
        return False
    try:
        algorithm, iterations, encoded_salt, encoded_digest = encoded_hash.split("$", 3)
        if algorithm != _ALGORITHM:
            return False
        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected = base64.urlsafe_b64decode(encoded_digest.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations)
        )
        return secrets.compare_digest(actual, expected)
    except (ValueError, UnicodeError):
        return False
