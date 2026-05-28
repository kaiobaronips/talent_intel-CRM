export type Tenant = {
  id: string;
  company_name: string;
  slug?: string;
  tier?: string;
  timezone?: string;
  status?: string;
  created_at?: string;
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
  payload_json?: Record<string, unknown> | null;
  scheduled_at?: string | null;
  sent_at?: string | null;
  created_at?: string;
};

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
