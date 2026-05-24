import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { apiGetRaw, getDefaultTenantId } from './api';

export type Principal = {
  role: 'admin' | 'tenant' | string;
  tenant_id: string;
  api_key_id: string;
  is_admin: boolean;
  user_id?: string;
  email?: string;
  auth_method?: string;
};

export const sessionCookieName = 'ticrm_session';

export async function getSessionToken(): Promise<string> {
  const cookieStore = await cookies();
  return cookieStore.get(sessionCookieName)?.value ?? '';
}

export async function getPrincipal() {
  const bearerToken = await getSessionToken();
  return apiGetRaw<Principal>('/v1/me', {
    role: 'admin',
    tenant_id: '',
    api_key_id: '',
    is_admin: true,
    auth_method: 'fallback',
  }, bearerToken ? { bearerToken } : {});
}

export async function requireAuthenticatedPrincipal() {
  const token = await getSessionToken();
  if (!token && !process.env.TICRM_API_KEY) {
    redirect('/login');
  }

  const principal = await getPrincipal();
  if (principal.offline && !process.env.TICRM_API_KEY) {
    redirect('/login');
  }
  return principal;
}

export async function resolveActiveTenantId() {
  const principal = await requireAuthenticatedPrincipal();
  const tenantId = principal.data.tenant_id || getDefaultTenantId();
  const token = await getSessionToken();
  return { tenantId, principal, authOptions: token ? { bearerToken: token } : {} };
}
