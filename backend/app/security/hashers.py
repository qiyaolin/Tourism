import hashlib
import hmac
import re

import bcrypt

from app.core.config import get_settings

CN_PHONE_REGEX = re.compile(r"^1[3-9]\d{9}$")


def normalize_phone(phone: str) -> str:
    normalized = re.sub(r"\D", "", phone.strip())
    if normalized.startswith("86") and len(normalized) == 13:
        normalized = normalized[2:]
    return normalized


def validate_phone(phone: str) -> bool:
    return bool(CN_PHONE_REGEX.fullmatch(phone))


def build_phone_lookup_hash(normalized_phone: str) -> str:
    secret = get_settings().phone_lookup_secret.encode("utf-8")
    return hmac.new(secret, normalized_phone.encode("utf-8"), hashlib.sha256).hexdigest()


def bcrypt_hash(raw_value: str) -> str:
    hashed = bcrypt.hashpw(raw_value.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def bcrypt_verify(raw_value: str, hashed_value: str) -> bool:
    return bcrypt.checkpw(raw_value.encode("utf-8"), hashed_value.encode("utf-8"))

