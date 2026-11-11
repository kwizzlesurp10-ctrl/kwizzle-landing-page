from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from api.x_conversion.identifiers import build_identifiers
from api.x_conversion.registry import PIXEL_ID
from api.x_conversion.result import Err, Ok, Result

logger = logging.getLogger("x_conversion.client")

X_CONVERSIONS_URL = f"https://ads-api.x.com/12/measurement/conversions/{PIXEL_ID}"


class ConversionDeliveryError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class XConversionClient:
    def __init__(
        self,
        *,
        pixel_token: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._pixel_token = pixel_token if pixel_token is not None else os.environ.get("X_PIXEL_TOKEN")
        self._http_client = http_client

    def token_configured(self) -> bool:
        token = (self._pixel_token or "").strip()
        return bool(token)

    async def send_conversion(
        self,
        *,
        event_id: str,
        conversion_id: str,
        conversion_time: datetime | None = None,
        event_source_url: str | None = None,
        twclid: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Result[dict[str, Any], str]:
        token = (self._pixel_token or "").strip()
        if not token:
            return Err("missing_pixel_token")

        if not event_id.startswith(f"tw-{PIXEL_ID}-"):
            return Err("invalid_event_id")

        built = build_identifiers(
            twclid=twclid,
            email=email,
            phone=phone,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if isinstance(built, Err):
            return built

        when = conversion_time or datetime.now(timezone.utc)
        conversion_time_iso = when.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )

        conversion: dict[str, Any] = {
            "conversion_time": conversion_time_iso,
            "event_id": event_id,
            "conversion_id": conversion_id,
            "identifiers": built.value,
        }
        if event_source_url:
            conversion["event_source_url"] = event_source_url

        body = {"conversions": [conversion]}
        headers = {
            "X-Pixel-Token": token,
            "Content-Type": "application/json",
        }

        own_client = self._http_client is None
        client = self._http_client or httpx.AsyncClient(timeout=10.0)
        try:
            response = await client.post(X_CONVERSIONS_URL, json=body, headers=headers)
        except httpx.HTTPError:
            logger.exception("x_conversion_http_error event_id=%s", event_id)
            return Err("http_error")
        finally:
            if own_client:
                await client.aclose()

        if response.status_code >= 400:
            logger.warning(
                "x_conversion_api_error status=%s event_id=%s",
                response.status_code,
                event_id,
            )
            return Err(f"api_error_{response.status_code}")

        try:
            payload = response.json()
        except ValueError:
            payload = {"status_code": response.status_code, "body": response.text[:500]}

        return Ok(payload)
