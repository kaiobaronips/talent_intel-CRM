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
# editar TICRM_API_KEY e NEXT_PUBLIC_DEFAULT_TENANT_ID
npm run dev
```

Acessar:

- `http://localhost:3000/system`: API, Postgres e Temporal devem aparecer prontos.
- `http://localhost:3000/`: dashboard e formularios operacionais.
- `http://localhost:3000/tenants/<tenant-id>`: tenant, chaves, candidatos e interacoes.

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
