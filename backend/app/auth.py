import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone

from app.config import get_settings


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"pbkdf2_sha256$120000${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = bytes.fromhex(digest_hex)
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(derived, expected)
    except (TypeError, ValueError):
        return False


def _urlsafe_b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _urlsafe_b64_decode(data: str) -> bytes:
    padded = data + "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8"))


def create_access_token(username: str) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.auth_token_ttl_minutes)
    payload = {"sub": username, "exp": int(expires_at.timestamp())}
    payload_bytes = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    signature = hmac.new(settings.auth_secret_key.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    return f"{_urlsafe_b64(payload_bytes)}.{_urlsafe_b64(signature)}"


def verify_access_token(token: str) -> str | None:
    settings = get_settings()
    try:
        payload_part, signature_part = token.split(".", 1)
        payload_bytes = _urlsafe_b64_decode(payload_part)
        provided_signature = _urlsafe_b64_decode(signature_part)
        expected_signature = hmac.new(settings.auth_secret_key.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
        if not hmac.compare_digest(provided_signature, expected_signature):
            return None

        payload = json.loads(payload_bytes.decode("utf-8"))
        expires_at = int(payload.get("exp", 0))
        subject = payload.get("sub")
        if not subject:
            return None
        if datetime.now(timezone.utc).timestamp() > expires_at:
            return None
        return str(subject)
    except (ValueError, json.JSONDecodeError, TypeError):
        return None
