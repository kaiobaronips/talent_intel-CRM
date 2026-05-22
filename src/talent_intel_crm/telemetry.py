from __future__ import annotations

import logging
import time
from typing import Any, Callable, TypeVar


logger = logging.getLogger("talent_intel_crm.metrics")
T = TypeVar("T")


def emit_metric(name: str, **fields: Any) -> None:
    logger.info(name, extra={"metric": name, **fields})


def measure(name: str, fn: Callable[[], T], **fields: Any) -> T:
    started_at = time.perf_counter()
    try:
        result = fn()
    except Exception as exc:
        emit_metric(
            name,
            outcome="failure",
            error_type=type(exc).__name__,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
            **fields,
        )
        raise
    emit_metric(
        name,
        outcome="success",
        duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
        **fields,
    )
    return result
