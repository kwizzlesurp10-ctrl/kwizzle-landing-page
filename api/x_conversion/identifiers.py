from __future__ import annotations

import hashlib
import re
from typing import Any

from api.x_conversion.result import Err, Ok, Result

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


def normalize_email(raw: str) -> Result[str, str]:
    candidate = raw.strip().lower()
    if not candidate or not _EMAIL_RE.match(candidate):
        return Err("invalid_email")
    return Ok(candidate)


def sha256_hex_normalized(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_email_identifier(raw_email: str) -> Result[dict[str, Any], str]:
    normalized = normalize_email(raw_email)
    if isinstance(normalized, Err):
        return normalized
    hashed = sha256_hex_normalized(normalized.value)
    return Ok({"hashed_email": hashed})


def normalize_phone_e164(raw: str, *, default_region: str = "US") -> Result[str, str]:
    stripped = raw.strip()
    if not stripped:
        return Err("invalid_phone")

    try:
        import phonenumbers
        from phonenumbers import NumberParseException, PhoneNumberFormat
    except ImportError as exc:
        raise RuntimeError("phonenumbers is required for phone normalization") from exc

    try:
        parsed = phonenumbers.parse(stripped, default_region if not stripped.startswith("+") else None)
    except NumberParseException:
        return Err("invalid_phone")

    if not phonenumbers.is_possible_number(parsed) or not phonenumbers.is_valid_number(parsed):
        return Err("invalid_phone")

    e164 = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
    if not _E164_RE.match(e164):
        return Err("invalid_phone")
    return Ok(e164)


def hash_phone_identifier(raw_phone: str, *, default_region: str = "US") -> Result[dict[str, Any], str]:
    normalized = normalize_phone_e164(raw_phone, default_region=default_region)
    if isinstance(normalized, Err):
        return normalized
    hashed = sha256_hex_normalized(normalized.value)
    return Ok({"hashed_phone_number": hashed})


def ip_user_agent_pair(ip_address: str, user_agent: str) -> Result[dict[str, Any], str]:
    ip = ip_address.strip()
    ua = user_agent.strip()
    if not ip or not ua:
        return Err("missing_ip_or_user_agent")
    return Ok({"ip_address": ip, "user_agent": ua})


def twclid_identifier(twclid: str) -> Result[dict[str, Any], str]:
    value = twclid.strip()
    if not value:
        return Err("missing_twclid")
    return Ok({"twclid": value})


def build_identifiers(
    *,
    twclid: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    default_phone_region: str = "US",
) -> Result[list[dict[str, Any]], str]:
    identifiers: list[dict[str, Any]] = []

    if twclid:
        tw = twclid_identifier(twclid)
        if isinstance(tw, Err):
            return tw
        identifiers.append(tw.value)

    if email:
        em = hash_email_identifier(email)
        if isinstance(em, Err):
            return em
        identifiers.append(em.value)

    if phone:
        ph = hash_phone_identifier(phone, default_region=default_phone_region)
        if isinstance(ph, Err):
            return ph
        identifiers.append(ph.value)

    if ip_address and user_agent:
        pair = ip_user_agent_pair(ip_address, user_agent)
        if isinstance(pair, Err):
            return pair
        identifiers.append(pair.value)

    if not identifiers:
        return Err("no_valid_identifiers")

    return Ok(identifiers)
