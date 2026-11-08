from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from api.x_conversion.client import XConversionClient
from api.x_conversion.registry import ConversionEventRegistry, load_conversion_event_registry
from api.x_conversion.result import Err, Ok, Result

logger = logging.getLogger("x_conversion.reporting")


async def report_server_conversion(
    hook_key: str,
    *,
    conversion_id: str,
    registry: ConversionEventRegistry | None = None,
    client: XConversionClient | None = None,
    conversion_time: datetime | None = None,
    event_source_url: str | None = None,
    twclid: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Result[dict[str, Any] | None, str]:
    """
    Report a server-side conversion when hook_key is configured with a real X event_id
    and X_PIXEL_TOKEN is set. Otherwise returns Ok(None) without calling the X API.
    """
    reg = registry or load_conversion_event_registry()
    event_id = reg.event_id_for(hook_key)
    if not event_id:
        logger.debug("x_conversion_skipped_unconfigured hook=%s", hook_key)
        return Ok(None)

    sender = client or XConversionClient()
    if not sender.token_configured():
        logger.info("x_conversion_skipped_missing_token hook=%s", hook_key)
        return Err("missing_pixel_token")

    return await sender.send_conversion(
        event_id=event_id,
        conversion_id=conversion_id,
        conversion_time=conversion_time,
        event_source_url=event_source_url,
        twclid=twclid,
        email=email,
        phone=phone,
        ip_address=ip_address,
        user_agent=user_agent,
    )
