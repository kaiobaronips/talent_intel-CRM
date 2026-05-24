# Handoff — Talent Intel CRM — 2026-05-24

## Projeto

- **Repo**: `https://github.com/kaiobaronips/talent_intel-CRM.git`
- **Branch**: `clean-main` (pushed)
- **Diretório**: `/Users/kaiobp/Talent-Intel-CRM`
- **Stack**: Next.js 16 (App Router, Turbopack) + Python backend + Supabase Auth + PostgreSQL (Supabase)
- **Supabase Project Ref**: `hkqdndpxpmkedauqewzk`

## O que foi feito nesta sessão

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

### P1 — Obrigatório para login Google funcionar end-to-end
1. **Google Cloud Console**: Confirmar que a **Authorized redirect URI** inclui:
   ```
   https://hkqdndpxpmkedauqewzk.supabase.co/auth/v1/callback
   ```
   Sem isso, Google retorna `redirect_uri_mismatch` após o usuário escolher a conta.

2. **Testar login completo**: Após configurar a redirect URI no Google, refazer o teste end-to-end — clicar "Entrar com Google", escolher conta, verificar que retorna ao dashboard autenticado.

3. **Tratamento de usuário Google no backend**: Verificar se o backend (API Python) aceita JWTs de usuários Google (provider `google` no `auth.users`). O JWT é o mesmo formato Supabase, mas o usuário pode não ter `tenant_memberships` — decidir se auto-cria ou rejeita.

### P2 — Ajustes para produção
4. **`NEXT_PUBLIC_SITE_URL`**: Em produção (Vercel), alterar de `http://localhost:3003` para a URL real do app.
5. **Variáveis de ambiente no Vercel**: Configurar `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` e `NEXT_PUBLIC_SITE_URL` no Vercel dashboard ou via `vercel env`.
6. **Redirect URL para domínio custom**: Se o app tiver domínio próprio (ex: `app.soreninvestimentos.com.br`), adicionar `https://<dominio>/auth/callback` tanto no Supabase Auth quanto no Google Console.

### P3 — Melhorias
7. **Refresh token**: O cookie de sessão atual usa `maxAge: expires_in` (~3600s). Considerar implementar refresh automático.
8. **Logout**: Verificar se existe rota de logout que limpa cookie + revoga sessão no Supabase.

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
