export type Tenant = {
  id: string;
  company_name: string;
  slug?: string;
  tier?: string;
  timezone?: string;
  status?: string;
  metadata_json?: TenantMetadata;
  metadata?: TenantMetadata;
  created_at?: string;
};

export type TenantMetadata = {
  ideal_profile?: {
    target_roles?: string;
    seniority?: string;
    locations?: string;
    keywords?: string;
    allowed_channels?: string[];
    outreach_tone?: string;
  };
  mvp_limits?: {
    daily_contact_limit?: number;
    max_attempts_per_candidate?: number;
    follow_up_interval_days?: number;
    require_manual_approval?: boolean;
    linkedin_enabled?: boolean;
    email_enabled?: boolean;
  };
  message_templates?: {
    email_initial_subject?: string;
    email_initial_body?: string;
    email_follow_up_1_subject?: string;
    email_follow_up_1_body?: string;
    email_follow_up_2_subject?: string;
    email_follow_up_2_body?: string;
    email_follow_up_3_subject?: string;
    email_follow_up_3_body?: string;
    linkedin_connection_note?: string;
    linkedin_initial_message?: string;
    linkedin_follow_up_message?: string;
    response_follow_up_message?: string;
  };
  [key: string]: unknown;
};

export type Candidate = {
  id: string;
  tenant_id?: string;
  name: string;
  email?: string | null;
  phone?: string | null;
  linkedin_url?: string | null;
  city?: string | null;
  state?: string | null;
  current_role?: string | null;
  current_company?: string | null;
  target_profile?: string | null;
  seniority?: string | null;
  classification?: string | null;
  classification_reason?: string | null;
  profile_summary?: string | null;
  recommended_action?: string | null;
  manual_decision?: string | null;
  manual_decision_note?: string | null;
  score_overall?: number | null;
  stage?: string | null;
  created_at?: string;
};

export type Interaction = {
  id: string;
  tenant_id?: string;
  candidate_id: string;
  candidate_name?: string | null;
  channel: 'email' | 'linkedin' | string;
  message_type?: string | null;
  status?: string | null;
  interaction_status?: string | null;
  next_action?: string | null;
  message_sent?: string | null;
  response_received?: string | null;
  manual_approval_status?: string | null;
  manual_decision_note?: string | null;
  email_sent_to?: string | null;
  email_subject?: string | null;
  provider_message_id?: string | null;
  provider_thread_id?: string | null;
  linkedin_provider?: string | null;
  provider_executed?: boolean | null;
  cadence_step?: string | null;
  scheduled_after_days?: number | null;
  payload_json?: Record<string, unknown> | null;
  scheduled_at?: string | null;
  sent_at?: string | null;
  created_at?: string;
};

export type InteractionStatus = 'draft' | 'pending' | 'approved' | 'sent' | 'replied' | 'closed' | 'paused' | 'discarded';

export type ApiKey = {
  id: string;
  name: string;
  status?: string;
  created_at?: string;
  last_used_at?: string | null;
  expires_at?: string | null;
};

export type Pagination = {
  page: number;
  limit: number;
  total: number;
  pages: number;
};

export type Paginated<T> = {
  items: T[];
  pagination: Pagination;
};

export type WorkflowRuns = {
  completed?: number;
  running?: number;
  failed?: number;
  canceled?: number;
  total?: number;
  [key: string]: number | undefined;
};

export type InteractionCount = {
  channel: string;
  status: string;
  total: number;
};

export type ChannelBacklog = {
  channel: string;
  pending: number;
};

export type TenantMetrics = {
  workflow_runs: WorkflowRuns;
  interaction_counts: InteractionCount[];
  channel_backlog: ChannelBacklog[];
};

export type ApiResult<T> = {
  data: T;
  offline: boolean;
  status?: number;
  message?: string;
};

export type AuditEvent = {
  id: string;
  tenant_id?: string;
  candidate_id?: string | null;
  event_type: string;
  actor_type?: string;
  actor_id?: string;
  payload_json?: Record<string, unknown>;
  created_at?: string;
};

export type TenantMembership = {
  id: string;
  tenant_id?: string;
  user_id: string;
  email?: string;
  role: 'owner' | 'admin' | 'recruiter' | 'viewer' | string;
  created_at?: string;
  updated_at?: string;
};

export type WorkflowRun = {
  id: string;
  tenant_id?: string;
  candidate_id?: string | null;
  workflow_name: string;
  workflow_id: string;
  run_id: string;
  status: string;
  started_at?: string;
  finished_at?: string | null;
};
