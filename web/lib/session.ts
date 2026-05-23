import { apiGetRaw, getDefaultTenantId } from './api';

export type Principal = {
  role: 'admin' | 'tenant' | string;
  tenant_id: string;
  api_key_id: string;
  is_admin: boolean;
};

export async function getPrincipal() {
  return apiGetRaw<Principal>('/v1/me', {
    role: 'admin',
    tenant_id: '',
    api_key_id: '',
    is_admin: true,
  });
}

export async function resolveActiveTenantId() {
  const principal = await getPrincipal();
  const tenantId = principal.data.tenant_id || getDefaultTenantId();
  return { tenantId, principal };
}
