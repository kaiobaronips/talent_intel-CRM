import { defaultTenantId, fallbackApiKeys, fallbackCandidates, fallbackInteractions, fallbackMetrics, fallbackTenant } from './fallbacks';
import type { ApiKey, ApiResult, Candidate, Interaction, Paginated, Tenant, TenantMetrics } from './types';

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

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = { Accept: 'application/json' };

  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }

  return headers;
}

export async function apiGetRaw<T>(path: string, fallback: T): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      headers: authHeaders(),
      cache: 'no-store',
    });

    if (!response.ok) {
      return { data: fallback, offline: true };
    }

    const payload = (await response.json()) as ApiEnvelope<T> | T;
    const data = isEnvelope(payload) ? payload.data : payload;

    if (data === undefined || data === null) {
      return { data: fallback, offline: true };
    }

    return { data: data as T, offline: false };
  } catch {
    return { data: fallback, offline: true };
  }
}

export async function apiMutation<T>(path: string, method: 'POST' | 'DELETE', body?: unknown): Promise<ApiMutationResult<T>> {
  try {
    const headers = authHeaders();
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
        message: payload.detail ?? `API retornou HTTP ${response.status}`,
      };
    }

    return {
      ok: true,
      status: response.status,
      data: payload.data,
      message: 'Operacao concluida.',
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      message: error instanceof Error ? error.message : 'Falha desconhecida ao chamar API.',
    };
  }
}

function isEnvelope<T>(payload: ApiEnvelope<T> | T): payload is ApiEnvelope<T> {
  return typeof payload === 'object' && payload !== null && 'data' in payload;
}

export function getDefaultTenantId(): string {
  return defaultTenantId;
}

export async function getTenant(tenantId = defaultTenantId): Promise<ApiResult<Tenant>> {
  return apiGetRaw<Tenant>(`/v1/tenants/${tenantId}`, fallbackTenant);
}

export async function getTenantMetrics(tenantId = defaultTenantId): Promise<ApiResult<TenantMetrics>> {
  return apiGetRaw<TenantMetrics>(`/v1/tenants/${tenantId}/metrics`, fallbackMetrics);
}

export async function getCandidates(tenantId = defaultTenantId, limit = 20): Promise<ApiResult<Paginated<Candidate>>> {
  return apiGetRaw<Paginated<Candidate>>(`/v1/tenants/${tenantId}/candidates?page=1&limit=${limit}`, fallbackCandidates);
}

export async function getInteractions(tenantId = defaultTenantId, limit = 20): Promise<ApiResult<Paginated<Interaction>>> {
  return apiGetRaw<Paginated<Interaction>>(`/v1/tenants/${tenantId}/interactions?page=1&limit=${limit}`, fallbackInteractions);
}

export async function getApiKeys(tenantId = defaultTenantId): Promise<ApiResult<ApiKey[]>> {
  const result = await apiGetRaw<ApiKeysPayload>(`/v1/tenants/${tenantId}/api-keys`, { tenant_id: tenantId, items: fallbackApiKeys });
  return { data: result.data.items, offline: result.offline };
}
