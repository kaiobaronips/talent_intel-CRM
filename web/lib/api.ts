import { defaultTenantId, fallbackApiKeys, fallbackAuditEvents, fallbackCandidate, fallbackCandidateInteractions, fallbackCandidates, fallbackInteractions, fallbackMemberships, fallbackMetrics, fallbackTenant, fallbackTenants, fallbackWorkflowRuns } from './fallbacks';
import type { ApiKey, ApiResult, AuditEvent, Candidate, Interaction, InteractionStatus, Paginated, Tenant, TenantMembership, TenantMetrics, WorkflowRun } from './types';

const apiBaseUrl = process.env.NEXT_PUBLIC_TICRM_API_URL ?? 'http://localhost:8000';
const apiKey = process.env.TICRM_API_KEY;

type ApiEnvelope<T> = {
  success?: boolean;
  data?: T;
  detail?: string;
  error?: unknown;
};

type ApiMutationResult<T> = {
  ok: boolean;
  status: number;
  data?: T;
  message: string;
};

type ApiKeysPayload = {
  tenant_id: string;
  items: ApiKey[];
};

type MembershipsPayload = {
  tenant_id: string;
  items: TenantMembership[];
};

type CandidateInteractionsPayload = {
  candidate_id: string;
  items: Interaction[];
};

type ApiAuthOptions = {
  bearerToken?: string;
  apiKeyFallback?: boolean;
};

function authHeaders(options: ApiAuthOptions = {}): Record<string, string> {
  const headers: Record<string, string> = { Accept: 'application/json' };

  if (options.bearerToken) {
    headers.Authorization = `Bearer ${options.bearerToken}`;
  } else if (apiKey && options.apiKeyFallback !== false) {
    headers['X-API-Key'] = apiKey;
  }

  return headers;
}

export async function apiGetRaw<T>(path: string, fallback: T, options: ApiAuthOptions = {}): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      headers: authHeaders(options),
      cache: 'no-store',
    });

    if (!response.ok) {
      const payload = (await response.json().catch(() => ({}))) as ApiEnvelope<T>;
      return {
        data: fallback,
        offline: true,
        status: response.status,
        message: payload.detail ?? `O serviço retornou erro HTTP ${response.status}`,
      };
    }

    const payload = (await response.json()) as ApiEnvelope<T> | T;
    const data = isEnvelope(payload) ? payload.data : payload;

    if (data === undefined || data === null) {
      return { data: fallback, offline: true, status: response.status, message: 'O serviço retornou uma resposta vazia.' };
    }

    return { data: data as T, offline: false, status: response.status };
  } catch (error) {
    return {
      data: fallback,
      offline: true,
      status: 0,
      message: error instanceof Error ? error.message : 'Falha desconhecida ao chamar o serviço.',
    };
  }
}

export async function apiMutation<T>(path: string, method: 'POST' | 'DELETE', body?: unknown, options: ApiAuthOptions = {}): Promise<ApiMutationResult<T>> {
  try {
    const headers = authHeaders(options);
    headers['Content-Type'] = 'application/json';

    const response = await fetch(`${apiBaseUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: 'no-store',
    });
    const payload = (await response.json().catch(() => ({}))) as ApiEnvelope<T>;

    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        message: payload.detail ?? `O serviço retornou erro HTTP ${response.status}`,
      };
    }

    return {
      ok: true,
      status: response.status,
      data: payload.data,
      message: 'Operação concluída.',
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      message: error instanceof Error ? error.message : 'Falha desconhecida ao chamar o serviço.',
    };
  }
}

function isEnvelope<T>(payload: ApiEnvelope<T> | T): payload is ApiEnvelope<T> {
  return typeof payload === 'object' && payload !== null && 'data' in payload;
}

export function getDefaultTenantId(): string {
  return defaultTenantId;
}

export async function getTenants(limit = 20, options: ApiAuthOptions = {}): Promise<ApiResult<Paginated<Tenant>>> {
  return apiGetRaw<Paginated<Tenant>>(`/v1/tenants?page=1&limit=${limit}`, fallbackTenants, options);
}

export async function getTenant(tenantId = defaultTenantId, options: ApiAuthOptions = {}): Promise<ApiResult<Tenant>> {
  return apiGetRaw<Tenant>(`/v1/tenants/${tenantId}`, fallbackTenant, options);
}

export async function getWorkflowRuns(tenantId = defaultTenantId, limit = 20, options: ApiAuthOptions = {}): Promise<ApiResult<Paginated<WorkflowRun>>> {
  return apiGetRaw<Paginated<WorkflowRun>>(`/v1/tenants/${tenantId}/workflow-runs?page=1&limit=${limit}`, fallbackWorkflowRuns, options);
}

export async function getAuditEvents(tenantId = defaultTenantId, limit = 20, options: ApiAuthOptions = {}): Promise<ApiResult<Paginated<AuditEvent>>> {
  return apiGetRaw<Paginated<AuditEvent>>(`/v1/tenants/${tenantId}/audit-events?page=1&limit=${limit}`, fallbackAuditEvents, options);
}

export async function getTenantMetrics(tenantId = defaultTenantId, options: ApiAuthOptions = {}): Promise<ApiResult<TenantMetrics>> {
  return apiGetRaw<TenantMetrics>(`/v1/tenants/${tenantId}/metrics`, fallbackMetrics, options);
}

export async function getCandidates(tenantId = defaultTenantId, limit = 20, options: ApiAuthOptions = {}): Promise<ApiResult<Paginated<Candidate>>> {
  return apiGetRaw<Paginated<Candidate>>(`/v1/tenants/${tenantId}/candidates?page=1&limit=${limit}`, fallbackCandidates, options);
}

export async function getCandidate(candidateId: string, options: ApiAuthOptions = {}): Promise<ApiResult<Candidate>> {
  return apiGetRaw<Candidate>(`/v1/candidates/${candidateId}`, fallbackCandidate, options);
}

export async function getInteractions(tenantId = defaultTenantId, limit = 20, options: ApiAuthOptions = {}): Promise<ApiResult<Paginated<Interaction>>> {
  return apiGetRaw<Paginated<Interaction>>(`/v1/tenants/${tenantId}/interactions?page=1&limit=${limit}`, fallbackInteractions, options);
}

export async function getCandidateInteractions(candidateId: string, options: ApiAuthOptions = {}): Promise<ApiResult<Interaction[]>> {
  const result = await apiGetRaw<CandidateInteractionsPayload>(`/v1/candidates/${candidateId}/interactions`, fallbackCandidateInteractions, options);
  return { data: result.data.items, offline: result.offline, status: result.status, message: result.message };
}

export async function updateInteractionStatus(
  interactionId: string,
  status: InteractionStatus,
  responseReceived = '',
  options: ApiAuthOptions = {},
): Promise<ApiMutationResult<{ interaction: Interaction }>> {
  return apiMutation<{ interaction: Interaction }>(`/v1/interactions/${interactionId}/status`, 'POST', {
    status,
    response_received: responseReceived,
  }, options);
}

export async function reviewInteractionMessage(
  interactionId: string,
  status: 'draft' | 'pending' | 'approved',
  messageSent: string,
  decisionNote = '',
  subject = '',
  options: ApiAuthOptions = {},
): Promise<ApiMutationResult<{ interaction: Interaction }>> {
  return apiMutation<{ interaction: Interaction }>(`/v1/interactions/${interactionId}/review`, 'POST', {
    status,
    message_sent: messageSent,
    subject,
    decision_note: decisionNote,
  }, options);
}

export async function prepareCandidateEmailFollowUp(
  candidateId: string,
  options: ApiAuthOptions = {},
): Promise<ApiMutationResult<{ interaction: Interaction; already_prepared: boolean }>> {
  return apiMutation<{ interaction: Interaction; already_prepared: boolean }>(`/v1/candidates/${candidateId}/email-follow-up`, 'POST', {}, options);
}

export async function prepareCandidateLinkedInFollowUp(
  candidateId: string,
  options: ApiAuthOptions = {},
): Promise<ApiMutationResult<{ interaction: Interaction; already_prepared: boolean }>> {
  return apiMutation<{ interaction: Interaction; already_prepared: boolean }>(`/v1/candidates/${candidateId}/linkedin-follow-up`, 'POST', {}, options);
}

export async function updateCandidateDecision(
  candidateId: string,
  decision: 'active' | 'paused' | 'discarded',
  decisionNote = '',
  options: ApiAuthOptions = {},
): Promise<ApiMutationResult<{ candidate: Candidate }>> {
  return apiMutation<{ candidate: Candidate }>(`/v1/candidates/${candidateId}/decision`, 'POST', {
    decision,
    decision_note: decisionNote,
  }, options);
}

export async function updateTenantPreferences(
  tenantId: string,
  payload: Record<string, unknown>,
  options: ApiAuthOptions = {},
): Promise<ApiMutationResult<{ tenant: Tenant }>> {
  return apiMutation<{ tenant: Tenant }>(`/v1/tenants/${tenantId}/preferences`, 'POST', payload, options);
}

export async function updateTenantMessageTemplates(
  tenantId: string,
  payload: Record<string, unknown>,
  options: ApiAuthOptions = {},
): Promise<ApiMutationResult<{ tenant: Tenant }>> {
  return apiMutation<{ tenant: Tenant }>(`/v1/tenants/${tenantId}/message-templates`, 'POST', payload, options);
}

export async function getMemberships(tenantId = defaultTenantId, options: ApiAuthOptions = {}): Promise<ApiResult<TenantMembership[]>> {
  const result = await apiGetRaw<MembershipsPayload>(`/v1/tenants/${tenantId}/memberships`, { tenant_id: tenantId, items: fallbackMemberships }, options);
  return { data: result.data.items, offline: result.offline, status: result.status, message: result.message };
}

export async function getApiKeys(tenantId = defaultTenantId, options: ApiAuthOptions = {}): Promise<ApiResult<ApiKey[]>> {
  const result = await apiGetRaw<ApiKeysPayload>(`/v1/tenants/${tenantId}/api-keys`, { tenant_id: tenantId, items: fallbackApiKeys }, options);
  return { data: result.data.items, offline: result.offline, status: result.status, message: result.message };
}
