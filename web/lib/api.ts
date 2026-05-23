import { defaultTenantId, fallbackApiKeys, fallbackCandidates, fallbackInteractions, fallbackMetrics, fallbackTenant } from './fallbacks';
import type { ApiKey, ApiResult, Candidate, Interaction, Paginated, Tenant, TenantMetrics } from './types';

const apiBaseUrl = process.env.NEXT_PUBLIC_TICRM_API_URL ?? 'http://localhost:8000';
const apiKey = process.env.TICRM_API_KEY;

type ApiEnvelope<T> = {
  success?: boolean;
  data?: T;
  error?: unknown;
};

async function apiGet<T>(path: string, fallback: T): Promise<ApiResult<T>> {
  const headers: HeadersInit = { Accept: 'application/json' };

  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }

  try {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      headers,
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

function isEnvelope<T>(payload: ApiEnvelope<T> | T): payload is ApiEnvelope<T> {
  return typeof payload === 'object' && payload !== null && 'data' in payload;
}

export function getDefaultTenantId(): string {
  return defaultTenantId;
}

export async function getTenant(tenantId = defaultTenantId): Promise<ApiResult<Tenant>> {
  return apiGet<Tenant>(`/v1/tenants/${tenantId}`, fallbackTenant);
}

export async function getTenantMetrics(tenantId = defaultTenantId): Promise<ApiResult<TenantMetrics>> {
  return apiGet<TenantMetrics>(`/v1/tenants/${tenantId}/metrics`, fallbackMetrics);
}

export async function getCandidates(tenantId = defaultTenantId, limit = 20): Promise<ApiResult<Paginated<Candidate>>> {
  return apiGet<Paginated<Candidate>>(`/v1/tenants/${tenantId}/candidates?page=1&limit=${limit}`, fallbackCandidates);
}

export async function getInteractions(tenantId = defaultTenantId, limit = 20): Promise<ApiResult<Paginated<Interaction>>> {
  return apiGet<Paginated<Interaction>>(`/v1/tenants/${tenantId}/interactions?page=1&limit=${limit}`, fallbackInteractions);
}

export async function getApiKeys(tenantId = defaultTenantId): Promise<ApiResult<ApiKey[]>> {
  return apiGet<ApiKey[]>(`/v1/tenants/${tenantId}/api-keys`, fallbackApiKeys);
}
