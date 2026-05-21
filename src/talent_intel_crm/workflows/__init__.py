"""Temporal workflows for Talent Intel CRM."""

from .candidate_lifecycle import CandidateLifecycleWorkflow
from .closure import CandidateClosureWorkflow
from .enrichment import CandidateEnrichmentWorkflow
from .follow_up import CandidateFollowUpWorkflow
from .ingest import CandidateIngestWorkflow
from .outreach import CandidateOutreachWorkflow
from .qualification import CandidateQualificationWorkflow
from .tenant_onboarding import TenantOnboardingWorkflow

__all__ = [
    "CandidateLifecycleWorkflow",
    "CandidateClosureWorkflow",
    "CandidateEnrichmentWorkflow",
    "CandidateFollowUpWorkflow",
    "CandidateIngestWorkflow",
    "CandidateOutreachWorkflow",
    "CandidateQualificationWorkflow",
    "TenantOnboardingWorkflow",
]
