import { apiGetRaw } from './api';

export type HealthStatus = {
  service?: string;
  temporal_namespace?: string;
  temporal_target_host?: string;
};

export type ReadinessStatus = {
  service?: string;
  postgres?: boolean;
};

export type ConnectorStatusItem = {
  key: string;
  name: string;
  configured: boolean;
  status: 'active' | 'pending' | 'degraded' | 'offline' | string;
  summary: string;
  last_result: string;
  next_action: string;
  metrics: Record<string, unknown>;
};

export type ConnectorStatusPayload = {
  tenant_id: string;
  items: ConnectorStatusItem[];
};

export async function getHealthStatus() {
  return apiGetRaw<HealthStatus>('/health', {
    service: 'talent-intel-crm-api',
    temporal_namespace: 'unknown',
    temporal_target_host: 'unknown',
  });
}

export async function getReadinessStatus() {
  return apiGetRaw<ReadinessStatus>('/ready', {
    service: 'talent-intel-crm-api',
    postgres: false,
  });
}

export async function getConnectorStatus(tenantId: string, options = {}) {
  return apiGetRaw<ConnectorStatusPayload>(`/v1/tenants/${tenantId}/connector-status`, {
    tenant_id: tenantId,
    items: [],
  }, options);
}
