# Talent Intel CRM Web

Console SaaS em Next.js para operar o Talent Intel CRM sem expor credenciais no navegador.

## Rodar localmente

```bash
cd web
cp .env.example .env.local
npm install
npm run dev
```

Acesse `http://localhost:3000`.

## Variaveis

- `NEXT_PUBLIC_TICRM_API_URL`: URL publica da API FastAPI. Exemplo: `http://localhost:8000`.
- `TICRM_API_KEY`: chave server-side para smoke/admin interno. Páginas autenticadas usam o Bearer token Supabase do usuário, não essa chave como fallback.
- `NEXT_PUBLIC_DEFAULT_TENANT_ID`: tenant inicial exibido no dashboard.
- `NEXT_PUBLIC_SUPABASE_URL`: URL publica do projeto Supabase para login humano.
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: anon key publica do Supabase para o fluxo OAuth.
- `NEXT_PUBLIC_SITE_URL`: base URL publica da UI; usada no callback do OAuth.

## Telas iniciais

- `/`: Control Tower com metricas, candidatos recentes e fila por canal.
- `/tenants/[tenantId]`: detalhes do tenant, chaves, candidatos e interacoes.
- `/candidates`: base de candidatos pronta para cadencia.
- `/interactions`: fila operacional por LinkedIn e E-mail.

## Regra de seguranca

O app chama a API a partir de Server Components. A chave `TICRM_API_KEY` fica apenas no processo Next.js e nao e enviada ao browser. Fluxos humanos autenticados devem usar o Bearer token Supabase e autorização por `tenant_memberships`.

## Acoes operacionais

A UI ja possui Server Actions para:

- criar tenant e iniciar onboarding Temporal;
- adicionar candidato e iniciar `CandidateLifecycleWorkflow`;
- criar API key de tenant, exibindo a chave crua uma unica vez;
- revogar API key;
- rotacionar API key.

As acoes autenticadas usam o Bearer token Supabase do usuário logado. Se a API, Temporal ou a autorização por tenant falhar, o formulario retorna o erro da API sem quebrar a pagina.
Login humano via Google exige `/auth/callback` cadastrado no Supabase Auth e as URLs publicas acima configuradas na UI.

## System readiness

A rota `/system` valida conexao com:

- `/health`: API e configuracao Temporal;
- `/ready`: Postgres/Supabase.

Use o runbook em `docs/runbooks/web-local-e2e.md` para teste ponta a ponta local.
