import { cookies } from 'next/headers';
import { refreshCookieName, sessionCookieName } from './session';

export type SupabaseTokenPayload = {
  access_token?: string;
  refresh_token?: string;
  expires_in?: number;
  error?: string;
  error_description?: string;
  msg?: string;
};

export function supabaseAuthConfig() {
  return {
    url: (process.env.NEXT_PUBLIC_SUPABASE_URL ?? '').trim().replace(/\/$/, ''),
    anonKey: (process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? '').trim(),
    siteUrl: (process.env.NEXT_PUBLIC_SITE_URL ?? '').trim().replace(/\/$/, ''),
  };
}

export function requireSupabaseAuthConfig() {
  const config = supabaseAuthConfig();
  if (!config.url || !config.anonKey) {
    return { ok: false as const, message: 'Supabase Auth não está configurado na UI.', config };
  }
  return { ok: true as const, message: '', config };
}

export function authCookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    sameSite: 'lax' as const,
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge,
  };
}

export async function setSessionCookie(payload: SupabaseTokenPayload): Promise<boolean> {
  if (!payload.access_token) {
    return false;
  }

  const cookieStore = await cookies();
  cookieStore.set(sessionCookieName, payload.access_token, authCookieOptions(payload.expires_in ?? 3600));
  if (payload.refresh_token) {
    cookieStore.set(refreshCookieName, payload.refresh_token, authCookieOptions(60 * 60 * 24 * 30));
  }
  return true;
}

export async function revokeSupabaseSession(accessToken: string): Promise<void> {
  const authConfig = requireSupabaseAuthConfig();
  if (!accessToken || !authConfig.ok) {
    return;
  }

  await fetch(`${authConfig.config.url}/auth/v1/logout`, {
    method: 'POST',
    headers: {
      apikey: authConfig.config.anonKey,
      Authorization: `Bearer ${accessToken}`,
    },
    cache: 'no-store',
  }).catch(() => undefined);
}

export function authErrorMessage(payload: SupabaseTokenPayload, fallback = 'Login não autorizado.'): string {
  return payload.error_description ?? payload.msg ?? payload.error ?? fallback;
}
