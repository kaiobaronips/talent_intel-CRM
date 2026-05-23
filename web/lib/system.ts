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
