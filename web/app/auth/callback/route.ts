import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import { oauthVerifierCookieName, refreshCookieName, sessionCookieName } from '@/lib/session';
import { authCookieOptions, authErrorMessage, requireSupabaseAuthConfig, type SupabaseTokenPayload } from '@/lib/supabase-auth';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get('code');
  const error = url.searchParams.get('error_description') ?? url.searchParams.get('error');

  if (error) {
    return NextResponse.redirect(new URL(`/login?error=${encodeURIComponent(error)}`, request.url));
  }

  if (!code) {
    return NextResponse.redirect(new URL('/login?error=missing_code', request.url));
  }

  const authConfig = requireSupabaseAuthConfig();
  if (!authConfig.ok) {
    return NextResponse.redirect(new URL('/login?error=auth_config', request.url));
  }

  const cookieStore = await cookies();
  const codeVerifier = cookieStore.get(oauthVerifierCookieName)?.value ?? '';
  if (!codeVerifier) {
    return NextResponse.redirect(new URL('/login?error=missing_verifier', request.url));
  }

  const response = await fetch(`${authConfig.config.url}/auth/v1/token?grant_type=pkce`, {
    method: 'POST',
    headers: {
      apikey: authConfig.config.anonKey,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ auth_code: code, code_verifier: codeVerifier }),
    cache: 'no-store',
  });

  const payload = (await response.json().catch(() => ({}))) as SupabaseTokenPayload;
  if (!response.ok || !payload.access_token) {
    const message = authErrorMessage(payload, 'oauth_failed');
    return NextResponse.redirect(new URL(`/login?error=${encodeURIComponent(message)}`, request.url));
  }

  const redirectResponse = NextResponse.redirect(new URL('/', request.url));
  redirectResponse.cookies.set(sessionCookieName, payload.access_token, authCookieOptions(payload.expires_in ?? 3600));
  if (payload.refresh_token) {
    redirectResponse.cookies.set(refreshCookieName, payload.refresh_token, authCookieOptions(60 * 60 * 24 * 30));
  }
  redirectResponse.cookies.delete(oauthVerifierCookieName);
  return redirectResponse;
}
