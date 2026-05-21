from dataclasses import dataclass
import os
from typing import Optional


@dataclass(frozen=True)
class TemporalConfig:
    namespace: str = os.getenv("TEMPORAL_NAMESPACE", "default")
    task_queue: str = os.getenv("TEMPORAL_TASK_QUEUE", "talent-intel-crm")
    target_host: str = os.getenv("TEMPORAL_TARGET_HOST", "localhost:7233")
    api_key: Optional[str] = os.getenv("TEMPORAL_API_KEY") or None
    use_tls: bool = os.getenv("TEMPORAL_USE_TLS", "").lower() in {"1", "true", "yes"}
    identity: Optional[str] = os.getenv("TEMPORAL_IDENTITY") or None
