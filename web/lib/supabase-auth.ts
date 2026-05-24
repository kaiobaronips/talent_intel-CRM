import { cookies } from 'next/headers';
import { sessionCookieName } from './session';

export type SupabaseTokenPayload = {
  access_token?: string;
  expires_in?: number;
  error?: string;
  error_description?: string;
  msg?: string;
};

export function supabaseAuthConfig() {
  return {
    url: process.env.NEXT_PUBLIC_SUPABASE_URL?.replace(/\/$/, '') ?? '',
    anonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? '',
    siteUrl: process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, '') ?? '',
  };
}

export function requireSupabaseAuthConfig() {
  const config = supabaseAuthConfig();
  if (!config.url || !config.anonKey) {
    return { ok: false as const, message: 'Supabase Auth não está configurado na UI.', config };
  }
  return { ok: true as const, message: '', config };
}

export async function setSessionCookie(payload: SupabaseTokenPayload): Promise<boolean> {
  if (!payload.access_token) {
    return false;
  }

  const cookieStore = await cookies();
  cookieStore.set(sessionCookieName, payload.access_token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: payload.expires_in ?? 3600,
  });
  return true;
}

export function authErrorMessage(payload: SupabaseTokenPayload, fallback = 'Login não autorizado.'): string {
  return payload.error_description ?? payload.msg ?? payload.error ?? fallback;
}
