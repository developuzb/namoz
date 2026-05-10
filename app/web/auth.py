"""Telegram WebApp initData validatsiyasi.

Telegram WebApp har request'da `initData` query parametrini yuboradi —
bu HMAC-SHA256 imzo bilan tasdiqlangan ma'lumotlar. Validatsiya bot token
yordamida o'tkaziladi.

https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any
from urllib.parse import parse_qsl

from app.core.logger import logger


def parse_init_data(init_data_raw: str) -> dict[str, Any]:
    """`initData` query string'ni parse qiladi va dict qaytaradi."""
    parsed = dict(parse_qsl(init_data_raw, keep_blank_values=True))
    # user fieldi JSON string
    if "user" in parsed:
        try:
            parsed["user"] = json.loads(parsed["user"])
        except json.JSONDecodeError:
            pass
    return parsed


def validate_init_data(init_data_raw: str, bot_token: str) -> dict[str, Any] | None:
    """
    initData imzosini tekshiradi.

    Args:
        init_data_raw: WebApp dan kelgan `initData` query string
        bot_token: BOT_TOKEN

    Returns:
        Parse qilingan dict (validation o'tdi) yoki None (imzo noto'g'ri).
    """
    if not init_data_raw:
        return None

    # 1. Hash'ni alohida olib qolamiz
    pairs = dict(parse_qsl(init_data_raw, keep_blank_values=True))
    if "hash" not in pairs:
        return None
    received_hash = pairs.pop("hash")

    # 2. data_check_string yasaladi (alfabit tartibida key=value, \n bilan)
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))

    # 3. HMAC key: HMAC-SHA256(bot_token, "WebAppData")
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode(), hashlib.sha256,
    ).digest()

    # 4. Hash hisoblanadi
    calculated = hmac.new(
        secret_key, data_check.encode(), hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated, received_hash):
        logger.warning("WebApp initData: imzo noto'g'ri")
        return None

    # 5. Tasdiqlangan ma'lumotlar
    if "user" in pairs:
        try:
            pairs["user"] = json.loads(pairs["user"])
        except json.JSONDecodeError:
            pass
    return pairs


def extract_user_id(init_data_raw: str, bot_token: str) -> int | None:
    """initData'dan tasdiqlangan user_id ni olish."""
    data = validate_init_data(init_data_raw, bot_token)
    if data is None:
        return None
    user = data.get("user")
    if isinstance(user, dict):
        uid = user.get("id")
        if isinstance(uid, int):
            return uid
    return None


__all__ = ["extract_user_id", "parse_init_data", "validate_init_data"]
