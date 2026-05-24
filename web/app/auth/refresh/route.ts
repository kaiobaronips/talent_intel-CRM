import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import { refreshCookieName, sessionCookieName } from '@/lib/session';
import { authCookieOptions, authErrorMessage, requireSupabaseAuthConfig, type SupabaseTokenPayload } from '@/lib/supabase-auth';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get(refreshCookieName)?.value ?? '';
  const authConfig = requireSupabaseAuthConfig();

  if (!refreshToken || !authConfig.ok) {
    const response = NextResponse.redirect(new URL('/login?error=Sessao%20expirada.%20Entre%20novamente.', request.url));
    response.cookies.delete(sessionCookieName);
    response.cookies.delete(refreshCookieName);
    return response;
  }

  const response = await fetch(`${authConfig.config.url}/auth/v1/token?grant_type=refresh_token`, {
    method: 'POST',
    headers: {
      apikey: authConfig.config.anonKey,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
    cache: 'no-store',
  });

  const payload = (await response.json().catch(() => ({}))) as SupabaseTokenPayload;
  if (!response.ok || !payload.access_token) {
    const message = authErrorMessage(payload, 'Sessao expirada. Entre novamente.');
    const redirectResponse = NextResponse.redirect(new URL(`/login?error=${encodeURIComponent(message)}`, request.url));
    redirectResponse.cookies.delete(sessionCookieName);
    redirectResponse.cookies.delete(refreshCookieName);
    return redirectResponse;
  }

  const redirectResponse = NextResponse.redirect(new URL('/', request.url));
  redirectResponse.cookies.set(sessionCookieName, payload.access_token, authCookieOptions(payload.expires_in ?? 3600));
  if (payload.refresh_token) {
    redirectResponse.cookies.set(refreshCookieName, payload.refresh_token, authCookieOptions(60 * 60 * 24 * 30));
  }
  return redirectResponse;
}
