import crypto from 'node:crypto';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { oauthVerifierCookieName } from '@/lib/session';
import { requireSupabaseAuthConfig } from '@/lib/supabase-auth';

export const dynamic = 'force-dynamic';

function base64Url(buffer: Buffer): string {
  return buffer.toString('base64').replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
}

export async function GET(request: Request) {
  const authConfig = requireSupabaseAuthConfig();
  if (!authConfig.ok) {
    redirect('/login?error=auth_config');
  }

  const verifier = base64Url(crypto.randomBytes(64));
  const challenge = base64Url(crypto.createHash('sha256').update(verifier).digest());
  const origin = authConfig.config.siteUrl || new URL(request.url).origin;
  const redirectTo = new URL('/auth/callback', origin);
  const supabaseUrl = new URL(`${authConfig.config.url}/auth/v1/authorize`);
  supabaseUrl.searchParams.set('provider', 'google');
  supabaseUrl.searchParams.set('redirect_to', redirectTo.toString());
  supabaseUrl.searchParams.set('code_challenge', challenge);
  supabaseUrl.searchParams.set('code_challenge_method', 's256');

  const cookieStore = await cookies();
  cookieStore.set(oauthVerifierCookieName, verifier, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: 600,
  });

  redirect(supabaseUrl.toString());
}
