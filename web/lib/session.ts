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
export const refreshCookieName = 'ticrm_refresh';
export const oauthVerifierCookieName = 'ticrm_oauth_verifier';

export async function getSessionToken(): Promise<string> {
  const cookieStore = await cookies();
  return cookieStore.get(sessionCookieName)?.value ?? '';
}

export async function getPrincipal() {
  const bearerToken = await getSessionToken();
  return apiGetRaw<Principal>('/v1/me', {
    role: '',
    tenant_id: '',
    api_key_id: '',
    is_admin: false,
    auth_method: 'fallback',
  }, bearerToken ? { bearerToken, apiKeyFallback: false } : { apiKeyFallback: false });
}

export async function requireAuthenticatedPrincipal() {
  const token = await getSessionToken();
  if (!token) {
    redirect('/login');
  }

  const principal = await getPrincipal();
  if (principal.offline) {
    if (principal.status === 403) {
      redirect('/login?error=Seu%20login%20foi%20autenticado%2C%20mas%20ainda%20nao%20esta%20vinculado%20a%20uma%20empresa.');
    }
    if (principal.status === 401) {
      redirect('/login?error=Sessao%20expirada.%20Entre%20novamente.');
    }
    redirect('/login');
  }
  return principal;
}

export async function resolveActiveTenantId() {
  const principal = await requireAuthenticatedPrincipal();
  const tenantId = principal.data.tenant_id || getDefaultTenantId();
  const token = await getSessionToken();
  return { tenantId, principal, authOptions: token ? { bearerToken: token, apiKeyFallback: false } : { apiKeyFallback: false } };
}
