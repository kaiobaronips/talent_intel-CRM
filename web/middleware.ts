import { NextResponse, type NextRequest } from 'next/server';

const canonicalHost = (() => {
  try {
    return new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'https://talent-intel-crm.vercel.app').host;
  } catch {
    return 'talent-intel-crm.vercel.app';
  }
})();

function isLocalHost(host: string): boolean {
  return host.startsWith('localhost') || host.startsWith('127.0.0.1');
}

export function middleware(request: NextRequest) {
  const url = request.nextUrl;
  const target = url.clone();
  const host = request.headers.get('host') ?? url.host;
  const hasOAuthCallbackParams = url.searchParams.has('code') || url.searchParams.has('error') || url.searchParams.has('error_description');

  if (url.pathname === '/' && hasOAuthCallbackParams) {
    target.pathname = '/auth/callback';
  }

  if (!isLocalHost(host) && host !== canonicalHost) {
    target.protocol = 'https';
    target.host = canonicalHost;
  }

  if (target.href !== url.href) {
    return NextResponse.redirect(target);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
