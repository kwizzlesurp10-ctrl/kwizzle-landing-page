from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

logger = logging.getLogger("pack_pipeline.instrumentation")


@dataclass
class RunMetrics:
    started_at: float = field(default_factory=time.perf_counter)
    duration_ms: int = 0
    llm_enabled: bool = False
    llm_model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    def finish(self) -> None:
        self.duration_ms = int((time.perf_counter() - self.started_at) * 1000)

    def record_llm_usage(
        self,
        *,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        self.llm_enabled = True
        self.llm_model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens

    def as_log_payload(self, *, run_id: str, niche: str) -> dict[str, object]:
        return {
            "event": "pack_pipeline_run",
            "run_id": run_id,
            "niche": niche,
            "duration_ms": self.duration_ms,
            "llm_enabled": self.llm_enabled,
            "llm_model": self.llm_model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@contextmanager
def timed_run(*, run_id: str, niche: str) -> Iterator[RunMetrics]:
    metrics = RunMetrics()
    try:
        yield metrics
    finally:
        metrics.finish()
        logger.info(json.dumps(metrics.as_log_payload(run_id=run_id, niche=niche)))
