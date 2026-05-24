# Web Local E2E Runbook

Objetivo: validar a UI SaaS contra a API real antes de operar candidatos reais.

## 1. API

Em um terminal:

```bash
cd /Users/kaiobp/Talent-Intel-CRM
source /Users/kaiobp/SOREN/.venv/bin/activate
export TICRM_ADMIN_API_KEY=<admin-key>
export TICRM_ALLOW_INSECURE_DEV_AUTH=false
export SUPABASE_DB_URL=<supabase-postgres-url>
export SUPABASE_JWT_SECRET=<supabase-jwt-secret>
export TEMPORAL_TARGET_HOST=<temporal-host>
export TEMPORAL_NAMESPACE=<temporal-namespace>
export TEMPORAL_API_KEY=<temporal-api-key>
export TEMPORAL_USE_TLS=true
uvicorn talent_intel_crm.api:app --host 127.0.0.1 --port 8000
```

Validar:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

## 2. UI

Em outro terminal:

```bash
cd /Users/kaiobp/Talent-Intel-CRM/web
cp .env.local.example .env.local
# editar TICRM_API_KEY, NEXT_PUBLIC_DEFAULT_TENANT_ID, NEXT_PUBLIC_SUPABASE_URL e NEXT_PUBLIC_SUPABASE_ANON_KEY
# para Google OAuth local, definir tambem NEXT_PUBLIC_SITE_URL=http://localhost:3000
npm run dev
```

Acessar:

- `http://localhost:3000/system`: API, Postgres e Temporal devem aparecer prontos.
- `http://localhost:3000/`: dashboard e formularios operacionais.
- `http://localhost:3000/tenants/<tenant-id>`: tenant, chaves, candidatos e interacoes.

## 2.1. Login humano

Antes de testar `/login`, o usuario precisa existir no Supabase Auth e estar vinculado ao tenant:

```bash
export TICRM_BOOTSTRAP_TENANT_ID=api-controlled-003
export TICRM_BOOTSTRAP_USER_EMAIL=<email-do-usuario>
export TICRM_BOOTSTRAP_ROLE=owner
make bootstrap-tenant-member
```

Se voce ja tiver o `user_id` do Supabase Auth, use `TICRM_BOOTSTRAP_USER_ID` no lugar do e-mail.
Para criar o usuario automaticamente, informe tambem `SUPABASE_SERVICE_ROLE_KEY` e `TICRM_BOOTSTRAP_USER_PASSWORD`.

Acessar:

- `http://localhost:3000/login`

No Supabase Auth, habilite o provider Google e cadastre estas URLs de redirecionamento:

- `http://localhost:3000/auth/callback`
- `https://<dominio-do-app>/auth/callback`

Para ativar o provider por script:

```bash
export SUPABASE_PROJECT_REF=<project-ref>
export SUPABASE_ACCESS_TOKEN=<supabase-management-token>
export GOOGLE_OAUTH_CLIENT_ID=<google-client-id>
export GOOGLE_OAUTH_CLIENT_SECRET=<google-client-secret>
make activate-google-provider
```

## 3. Teste controlado

1. Criar ou selecionar tenant controlado.
2. Criar API key de tenant e copiar a chave crua imediatamente.
3. Adicionar candidato teste com e-mail ou LinkedIn.
4. Confirmar que o candidato aparece em `/candidates`.
5. Confirmar que interacoes aparecem em `/interactions`.
6. Confirmar no backend que o workflow foi iniciado.

## Gates de aceite

- `/system` mostra API online.
- `/ready` mostra `postgres=true`.
- Criar candidato pela UI retorna sucesso.
- Candidato aparece na lista paginada.
- Build de producao passa com `npm run build`.

## 4. Automacao local

Preparar `web/.env.local` sem imprimir segredo:

```bash
export TICRM_ADMIN_API_KEY=<admin-key>
export TICRM_API_URL=http://127.0.0.1:8000
export TICRM_SMOKE_TENANT_ID=api-controlled-003
make prepare-web-env
```

Rodar smoke da API:

```bash
make smoke-api
```

Rodar validacao completa de codigo:

```bash
make validate
```
