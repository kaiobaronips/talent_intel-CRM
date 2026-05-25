import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import { oauthVerifierCookieName, refreshCookieName, sessionCookieName } from '@/lib/session';
import { authErrorMessage, requireSupabaseAuthConfig, type SupabaseTokenPayload } from '@/lib/supabase-auth';

export const dynamic = 'force-dynamic';

function buildSetCookie(name: string, value: string, maxAge: number, secure: boolean): string {
  const parts = [`${name}=${value}`, 'Path=/', `Max-Age=${maxAge}`, 'HttpOnly', 'SameSite=Lax'];
  if (secure) parts.push('Secure');
  return parts.join('; ');
}

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

  let tokenResponse: globalThis.Response;
  try {
    tokenResponse = await fetch(`${authConfig.config.url}/auth/v1/token?grant_type=pkce`, {
      method: 'POST',
      headers: {
        apikey: authConfig.config.anonKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ auth_code: code, code_verifier: codeVerifier }),
      cache: 'no-store',
    });
  } catch (err) {
    console.error('[auth/callback] token exchange fetch failed:', err);
    return NextResponse.redirect(new URL('/login?error=token_exchange_failed', request.url));
  }

  const payload = (await tokenResponse.json().catch(() => ({}))) as SupabaseTokenPayload;
  if (!tokenResponse.ok || !payload.access_token) {
    const message = authErrorMessage(payload, 'oauth_failed');
    console.error('[auth/callback] token exchange rejected:', tokenResponse.status, message);
    return NextResponse.redirect(new URL(`/login?error=${encodeURIComponent(message)}`, request.url));
  }

  const secure = process.env.NODE_ENV === 'production';
  const accessToken = String(payload.access_token);
  const expiresIn = Number(payload.expires_in) || 3600;
  const redirectUrl = new URL('/', request.url).toString();

  const setCookies: [string, string][] = [
    ['Set-Cookie', buildSetCookie(sessionCookieName, accessToken, expiresIn, secure)],
  ];
  if (payload.refresh_token) {
    setCookies.push(['Set-Cookie', buildSetCookie(refreshCookieName, String(payload.refresh_token), 60 * 60 * 24 * 30, secure)]);
  }
  setCookies.push(['Set-Cookie', `${oauthVerifierCookieName}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax`]);

  return new Response(null, {
    status: 307,
    headers: [
      ['Location', redirectUrl],
      ...setCookies,
    ],
  });
}
