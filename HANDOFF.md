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

### P1 — Acompanhamento obrigatório
1. **Membership de usuário Google**: a API Python aceita JWTs de usuários Google porque valida o JWT Supabase por `SUPABASE_JWT_SECRET`; porém o usuário precisa existir em `tenant_memberships`. O comportamento atual é rejeitar com `403 User is not linked to a tenant` quando não houver vínculo. Manter esse modelo ou decidir se haverá auto-criação controlada.

### P2 — Ajustes para produção
2. **`NEXT_PUBLIC_SITE_URL`**: Em produção (Vercel), alterar para a URL real do app.
3. **Variáveis de ambiente no Vercel**: Configurar `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` e `NEXT_PUBLIC_SITE_URL` no Vercel dashboard ou via `vercel env`.
4. **Redirect URL para domínio custom**: Se o app tiver domínio próprio (ex: `app.soreninvestimentos.com.br`), adicionar `https://<dominio>/auth/callback` tanto no Supabase Auth quanto no Google Console.

### P3 — Melhorias
5. **Refresh token**: O cookie de sessão atual usa `maxAge: expires_in` (~3600s). Considerar implementar refresh automático.

## Arquivos relevantes

| Arquivo | Propósito |
|---------|-----------|
| `web/app/auth/google/route.ts` | Inicia fluxo OAuth PKCE com Supabase |
| `web/app/auth/callback/route.ts` | Recebe callback, troca code por JWT, seta cookie |
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
