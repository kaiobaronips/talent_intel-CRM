# Talent Intel CRM

Base do projeto com uma camada de orquestracao em Temporal.

## Estrutura

- `scripts/`: utilitarios legados e automacoes pontuais
- `src/talent_intel_crm/`: nova camada de dominio, atividades, workflows e worker
- `docs/`: arquitetura e plano do SaaS
- `RAW/`: lotes, handoffs e artefatos operacionais

## Objetivo da migracao

Separar a logica de negocio da execucao.

- `Temporal` passa a controlar estado, retries, timeout e continuidade
- `Activities` executam IO externo: Supabase Postgres, Gmail, LinkedIn e webhooks
- `Workflows` orquestram a jornada do candidato sem depender de automacao fraca

## Fluxo alvo

1. Ingestao do candidato
2. Enriquecimento
3. Qualificacao
4. Roteamento por canal
5. Disparo de mensagens
6. Follow-up com retry duravel
7. Registro de auditoria

## Arquitetura SaaS

Veja o blueprint completo em `docs/saas-architecture.md` e a camada Temporal em `docs/temporal-architecture.md`.
Veja a separacao de processos em `docs/deployment.md`.

## Comandos iniciais

```bash
python -m talent_intel_crm.worker
```

Para expor a API HTTP:

```bash
uvicorn talent_intel_crm.api:app --host 0.0.0.0 --port 8000
```

Para disparos controlados:

```bash
python -m talent_intel_crm.runner smoke
python -m talent_intel_crm.runner tenant-onboarding --tenant-id acme --company-name "Acme RH"
python -m talent_intel_crm.runner candidate-lifecycle --tenant-id acme --candidate-id cand-001 --name "Jane Doe" --email jane@example.com --channels email linkedin
python -m talent_intel_crm.runner candidate-step --step outreach --tenant-id acme --candidate-id cand-001 --name "Jane Doe" --email jane@example.com --linkedin-url https://www.linkedin.com/in/jane-doe --channels email linkedin --stage qualified
python -m talent_intel_crm.runner candidate-step --step follow-up --tenant-id acme --candidate-id cand-001 --name "Jane Doe" --email jane@example.com --linkedin-url https://www.linkedin.com/in/jane-doe --channels email linkedin --stage contacted --follow-up-delay-seconds 0 0
```

O worker ja roda com uma camada de persistencia em Postgres; o proximo passo e apontar `SUPABASE_DB_URL`, os canais reais de envio e, opcionalmente, o espelhamento visual no Notion.

## Temporal Cloud

Para apontar o worker para Temporal Cloud:

```bash
export TEMPORAL_TARGET_HOST="seu-namespace.temporal.cloud:7233"
export TEMPORAL_NAMESPACE="seu-namespace"
export TEMPORAL_API_KEY="..."
export TEMPORAL_TASK_QUEUE="talent-intel-crm"
python -m talent_intel_crm.worker
```

O worker e o runner carregam `.env` do diretorio em que o comando e executado antes de ler as configuracoes. Use `.env.example` como modelo para manter a chave Temporal, o DSN Supabase e o token do Notion fora do Git.

Se o `TEMPORAL_API_KEY` estiver definido, o SDK habilita TLS automaticamente.

## Activities de produção

As activities usam `Supabase Postgres` como persistencia principal e webhooks opcionais por ambiente para canais externos:

- `SUPABASE_DB_URL`
- `EMAIL_SEND_WEBHOOK_URL`
- `LINKEDIN_SEND_WEBHOOK_URL`
- `NOTION_MIRROR_API_TOKEN`
- `NOTION_MIRROR_TENANTS_DATA_SOURCE_ID`
- `NOTION_MIRROR_CANDIDATES_DATA_SOURCE_ID`
- `NOTION_MIRROR_INTERACTIONS_DATA_SOURCE_ID`
- `NOTION_MIRROR_WORKFLOW_RUNS_DATA_SOURCE_ID`
- `NOTION_MIRROR_AUDIT_EVENTS_DATA_SOURCE_ID`

Se os endpoints de canal nao estiverem configurados, a activity roda em `dry-run` e retorna o payload que seria enviado. Isso permite validar o fluxo Temporal sem acoplar credenciais antes da hora.

## Cadencia

`CandidateFollowUpWorkflow` usa timers duraveis do Temporal. A cadencia padrao abre follow-ups em D+5 e D+7; o runner aceita `--follow-up-delay-seconds` apenas para validacoes controladas com atrasos curtos.

## Idempotencia

Interacoes criadas pelos workflows carregam uma chave estavel por candidato, canal e etapa da cadencia. O Postgres aplica unicidade por tenant para que retries de activity ou replays nao dupliquem a mesma interacao operacional.

## API HTTP

`POST /v1/tenants` dispara o onboarding do tenant e `POST /v1/candidates` dispara o lifecycle do candidato. As rotas retornam `202` com `workflow_id` e `run_id`; o progresso continua no Temporal e na persistencia. A rota de candidato exige que o tenant ja exista na persistencia.

Rotas de leitura:

- `GET /v1/tenants/{tenant_id}`
- `GET /v1/tenants/{tenant_id}/candidates?page=1&limit=20`
- `GET /v1/tenants/{tenant_id}/interactions?page=1&limit=20`
- `GET /v1/tenants/{tenant_id}/metrics`
- `GET /v1/candidates/{candidate_id}`
- `GET /v1/candidates/{candidate_id}/interactions`
- `POST /v1/tenants/{tenant_id}/api-keys` using the admin key
- `GET /v1/tenants/{tenant_id}/api-keys` using the admin key
- `DELETE /v1/tenants/{tenant_id}/api-keys/{api_key_id}` using the admin key
- `POST /v1/tenants/{tenant_id}/api-keys/{api_key_id}/rotate` using the admin key

Defina `TICRM_ADMIN_API_KEY` e `TICRM_ALLOW_INSECURE_DEV_AUTH=false` para exigir `X-API-Key` nas rotas operacionais de producao. `GET /health` fica aberto para probes do servico. Chaves de tenant emitidas pela API ficam restritas ao tenant dono.

## Processos de deploy

API e worker rodam como servicos separados a partir da mesma base de codigo:

```bash
docker compose -f deploy/compose.yml up --build
```

Escale o worker separadamente da API conforme backlog e latencia das activities.

Migrations versionadas:

```bash
ticrm-migrate status
ticrm-migrate apply
```

## Notion Mirror

O espelhamento no Notion e opcional e lateral:

- `Supabase Postgres` segue como source of truth
- `Temporal` segue como motor de execucao
- `Notion` recebe projecoes para operacao humana

Quando as variaveis `NOTION_MIRROR_*` estiverem preenchidas, as activities de persistencia passam a sincronizar:

- `Tenants`
- `Candidates`
- `Interactions`
- `Workflow Runs`
- `Audit Events`

## Web SaaS UI

A UI comercial fica em `web/` e roda como app Next.js separado da API/worker Python.

```bash
cd web
cp .env.example .env.local
npm install
npm run dev
```

Configurar em `web/.env.local`:

- `NEXT_PUBLIC_TICRM_API_URL=http://localhost:8000`
- `TICRM_API_KEY=<admin-ou-tenant-api-key>`
- `NEXT_PUBLIC_DEFAULT_TENANT_ID=api-controlled-003`

A chave da API e usada apenas server-side pelo Next.js.

## Local Validation Commands

- `make validate`: roda testes Python, Ruff, typecheck/lint/build da UI.
- `make prepare-web-env`: cria `web/.env.local` a partir de variaveis de ambiente sem imprimir segredo.
- `make smoke-api`: valida `/health`, `/ready`, tenant, metricas, candidatos e interacoes contra a API local.

## Access Context

A API expoe `GET /v1/me` para a UI identificar se a chave atual e `admin` ou `tenant-scoped`.

- Chave admin: a UI usa `NEXT_PUBLIC_DEFAULT_TENANT_ID` como tenant ativo ate existir login/seletor multi-tenant completo.
- Chave de tenant: a UI resolve automaticamente o tenant pelo escopo da chave e evita depender de tenant fixo.

## Operational Audit

A API expoe `GET /v1/tenants/{tenant_id}/audit-events` e a UI possui `/audit` para visualizar eventos recentes por tenant. Use essa tela para investigar execucoes de workflow, eventos de lifecycle e acoes automaticas antes de operar em producao.
