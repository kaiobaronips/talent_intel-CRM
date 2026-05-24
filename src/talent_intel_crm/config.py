from dataclasses import dataclass, field
import os
from typing import Optional

from talent_intel_crm.support import load_local_env


load_local_env()


@dataclass(frozen=True)
class TemporalConfig:
    namespace: str = field(default_factory=lambda: os.getenv("TEMPORAL_NAMESPACE", "default"))
    task_queue: str = field(default_factory=lambda: os.getenv("TEMPORAL_TASK_QUEUE", "talent-intel-crm"))
    target_host: str = field(default_factory=lambda: os.getenv("TEMPORAL_TARGET_HOST", "localhost:7233"))
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("TEMPORAL_API_KEY") or None)
    use_tls: bool = field(default_factory=lambda: os.getenv("TEMPORAL_USE_TLS", "").lower() in {"1", "true", "yes"})
    identity: Optional[str] = field(default_factory=lambda: os.getenv("TEMPORAL_IDENTITY") or None)


@dataclass(frozen=True)
class APIConfig:
    admin_api_key: Optional[str] = field(default_factory=lambda: os.getenv("TICRM_ADMIN_API_KEY") or os.getenv("TICRM_API_KEY") or None)
    allow_insecure_development_auth: bool = field(default_factory=lambda: os.getenv("TICRM_ALLOW_INSECURE_DEV_AUTH", "false").lower() in {"1", "true", "yes"})
    auth_jwt_secret: Optional[str] = field(default_factory=lambda: os.getenv("TICRM_AUTH_JWT_SECRET") or os.getenv("SUPABASE_JWT_SECRET") or None)


@dataclass(frozen=True)
class NotionMirrorConfig:
    api_token: Optional[str] = field(default_factory=lambda: os.getenv("NOTION_MIRROR_API_TOKEN") or os.getenv("NOTION_API_TOKEN") or None)
    api_version: str = field(default_factory=lambda: os.getenv("NOTION_MIRROR_API_VERSION", "2026-03-11"))
    tenants_data_source_id: str = field(default_factory=lambda: os.getenv("NOTION_MIRROR_TENANTS_DATA_SOURCE_ID", ""))
    candidates_data_source_id: str = field(default_factory=lambda: os.getenv("NOTION_MIRROR_CANDIDATES_DATA_SOURCE_ID", ""))
    interactions_data_source_id: str = field(default_factory=lambda: os.getenv("NOTION_MIRROR_INTERACTIONS_DATA_SOURCE_ID", ""))
    workflow_runs_data_source_id: str = field(default_factory=lambda: os.getenv("NOTION_MIRROR_WORKFLOW_RUNS_DATA_SOURCE_ID", ""))
    audit_events_data_source_id: str = field(default_factory=lambda: os.getenv("NOTION_MIRROR_AUDIT_EVENTS_DATA_SOURCE_ID", ""))

    @property
    def enabled(self) -> bool:
        return bool(
            self.api_token
            and self.tenants_data_source_id
            and self.candidates_data_source_id
            and self.interactions_data_source_id
            and self.workflow_runs_data_source_id
            and self.audit_events_data_source_id
        )
