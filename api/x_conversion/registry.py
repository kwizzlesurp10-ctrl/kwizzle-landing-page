from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger("x_conversion.registry")

PIXEL_ID = "q8lud"


@dataclass(frozen=True, slots=True)
class ConversionEventRegistry:
    """Maps internal hook keys to X Ads event_id values (tw-q8lud-…)."""

    events: dict[str, str] = field(default_factory=dict)

    def event_id_for(self, hook_key: str) -> str | None:
        return self.events.get(hook_key)

    def is_configured(self, hook_key: str) -> bool:
        event_id = self.event_id_for(hook_key)
        return bool(event_id and event_id.startswith(f"tw-{PIXEL_ID}-"))


# Server hook points documented for production wiring (no guessed X event IDs).
DOCUMENTED_SERVER_HOOKS: tuple[str, ...] = (
    "pack_created",  # POST /api/packs success — agent/API flow; enable only with real event_id
)


def load_conversion_event_registry() -> ConversionEventRegistry:
    raw = os.environ.get("X_CONVERSION_EVENTS", "").strip()
    if not raw:
        return ConversionEventRegistry()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("x_conversion_invalid_events_json")
        return ConversionEventRegistry()

    if not isinstance(parsed, dict):
        logger.warning("x_conversion_events_not_object")
        return ConversionEventRegistry()

    events: dict[str, str] = {}
    for key, event_id in parsed.items():
        if not isinstance(key, str) or not isinstance(event_id, str):
            continue
        if not event_id.startswith(f"tw-{PIXEL_ID}-"):
            logger.warning("x_conversion_skip_event_id hook=%s", key)
            continue
        events[key] = event_id

    return ConversionEventRegistry(events=events)
