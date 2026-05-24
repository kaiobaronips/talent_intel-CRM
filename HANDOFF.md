# Handoff — Talent Intel CRM — 2026-05-24

## Projeto

- **Repo**: `https://github.com/kaiobaronips/talent_intel-CRM.git`
- **Branch**: `clean-main` (pushed)
- **Diretório**: `/Users/kaiobp/Talent-Intel-CRM`
- **Stack**: Next.js 16 (App Router, Turbopack) + Python backend + Supabase Auth + PostgreSQL (Supabase)
- **Supabase Project Ref**: `hkqdndpxpmkedauqewzk`

## O que foi feito nesta sessão

### Continuação Codex
1. Confirmado que o repositório está na branch `clean-main` e sem mudanças pendentes antes do ajuste.
2. Registrado o estado informado pelo operador: Google OAuth já configurado no Supabase/Google Console e login com Gmail funcionando na plataforma.
3. Logout ajustado para chamar `POST /auth/v1/logout` no Supabase antes de limpar o cookie local `ticrm_session`.
   - Se a revogação remota falhar, o cookie local ainda é removido e o usuário volta para `/login`.
4. Validações executadas após o ajuste:
   - `cd web && npm run typecheck` — OK
   - `cd web && npm run lint` — OK
   - `cd web && npm run build` — OK
   - `/Users/kaiobp/SOREN/.venv/bin/python -m pytest -q` — OK (25 testes)
   - `/Users/kaiobp/SOREN/.venv/bin/ruff check .` — OK

### Fechamento full-auto Codex
1. Membership por e-mail implementado:
   - `/members` usa e-mail como campo principal.
   - A API resolve `auth.users.email` para `user_id` e grava `tenant_memberships`.
   - Usuario autenticado sem membership recebe mensagem clara no `/login`.
2. Refresh de sessao implementado:
   - Login e callback OAuth armazenam access token e refresh token em cookies `httpOnly`.
   - `/auth/refresh` renova access token via Supabase quando a API retorna `401`.
   - Logout revoga sessao Supabase e limpa cookies de access/refresh.
3. Readiness de producao reforcado:
   - `make prod-readiness` tambem checa `NEXT_PUBLIC_SITE_URL` e formatos HTTPS de URLs publicas.
   - `make prepare-web-env` escreve `NEXT_PUBLIC_SITE_URL` no `web/.env.local`.

### Google OAuth ativado no Supabase Auth
1. Token `SUPABASE_ACCESS_TOKEN` atualizado no `.env` (o anterior era inválido).
   - Novo token armazenado em `.env` (não versionar).
2. Google Provider ativado via dashboard Supabase + confirmado via Management API.
   - `external_google_enabled: true`
   - Client ID: `279437903562-ogpa391csfq8e219k75pcv03u98ld0uf.apps.googleusercontent.com`
   - Client Secret configurado no Supabase.
3. Redirect URLs configuradas no Supabase Auth:
   - `http://localhost:3000/auth/callback`
   - `https://tallent-intelligence-crm-dashboard.vercel.app/auth/callback`
4. Criado `web/.env.local` (gitignored) com:
   - `NEXT_PUBLIC_SUPABASE_URL=https://hkqdndpxpmkedauqewzk.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key do projeto>`
   - `NEXT_PUBLIC_SITE_URL=http://localhost:3003`
5. Testado via Playwright: botão "Entrar com Google" redireciona corretamente para `accounts.google.com` com parâmetros OAuth corretos.

### Validações aprovadas
- `npm run typecheck` — OK
- `npm run lint` — OK
- `npm run build` — OK (todas rotas compilam)
- `pytest` (25 testes) — OK
- `ruff check .` — OK

## Pendências para próxima sessão

### P1 — Externo/deploy
1. **Vercel env**: Confirmar no dashboard Vercel `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_SITE_URL`, `NEXT_PUBLIC_TICRM_API_URL` e variaveis server-side da UI/API.
2. **Dominio custom**: Se o app tiver dominio proprio (ex: `app.soreninvestimentos.com.br`), adicionar `https://<dominio>/auth/callback` tanto no Supabase Auth quanto no Google Console.
3. **Smoke em producao**: apos deploy, testar login Google, `/members` por e-mail, logout e refresh apos expiracao/401.

## Arquivos relevantes

| Arquivo | Propósito |
|---------|-----------|
| `web/app/auth/google/route.ts` | Inicia fluxo OAuth PKCE com Supabase |
| `web/app/auth/callback/route.ts` | Recebe callback, troca code por JWT, seta cookie |
| `web/app/auth/refresh/route.ts` | Renova access token com refresh token Supabase |
| `web/lib/supabase-auth.ts` | Config helpers (`requireSupabaseAuthConfig`) |
| `web/lib/session.ts` | Cookie names, `getSessionToken()` |
| `web/components/LoginForm.tsx` | UI com botão Google + form email/senha |
| `web/app/login/page.tsx` | Página de login |
| `scripts/activate_supabase_google_provider.py` | Script para ativar provider via Management API |
| `.env` | Secrets backend (SUPABASE_ACCESS_TOKEN, GOOGLE_OAUTH_*, etc.) |
| `web/.env.local` | Secrets frontend Next.js (gitignored) |

## Contexto técnico

- Fluxo OAuth usa PKCE (code_challenge/code_verifier) — o verifier é armazenado em cookie httpOnly temporário.
- O Supabase atua como intermediário: app → Supabase authorize → Google → Supabase callback → app callback.
- A sessão no app é um JWT Supabase em cookie httpOnly (`talent-intel-session`).
- A API Python valida o JWT com `SUPABASE_JWT_SECRET`.
- Porta 3000 e 3001 estão ocupadas pelo projeto Theracorp no momento.
