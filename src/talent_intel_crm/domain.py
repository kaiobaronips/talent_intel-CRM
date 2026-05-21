from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CandidateChannel(str, Enum):
    EMAIL = "email"
    LINKEDIN = "linkedin"


class CandidateStage(str, Enum):
    INGESTED = "ingested"
    ENRICHED = "enriched"
    QUALIFIED = "qualified"
    READY_TO_CONTACT = "ready_to_contact"
    CONTACTED = "contacted"
    FOLLOW_UP = "follow_up"
    CLOSED = "closed"


class TenantTier(str, Enum):
    STARTER = "starter"
    GROWTH = "growth"
    SCALE = "scale"


@dataclass(slots=True)
class TenantEnvelope:
    tenant_id: str
    company_name: str
    tier: TenantTier = TenantTier.STARTER
    primary_domain: str = ""
    timezone: str = "America/Sao_Paulo"


@dataclass(slots=True)
class CandidateEnvelope:
    candidate_id: str
    tenant_id: str = "default"
    name: str
    city: str = ""
    email: str = ""
    linkedin_url: str = ""
    stage: CandidateStage = CandidateStage.INGESTED
    channels: list[CandidateChannel] = field(default_factory=list)
    source_page_id: Optional[str] = None


@dataclass(slots=True)
class InteractionEnvelope:
    tenant_id: str
    candidate_id: str
    channel: CandidateChannel
    message_id: str = ""
    thread_id: str = ""
    status: str = "pending"
