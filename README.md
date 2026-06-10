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
- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL` default: `Talent Intel CRM <onboarding@resend.dev>`
- `RESEND_REPLY_TO_EMAIL`
- `LINKEDIN_SEND_WEBHOOK_URL`
- `EXPANDI_REVERSED_WEBHOOK_URL` URL de reversed webhook da campanha Connector no Expandi; o CRM envia `profile_link` com a URL do LinkedIn e os campos de auditoria da cadencia
- `EXPANDI_API_KEY` opcional, enviada como `Authorization: Bearer` e `X-API-Key`
- `EXPANDI_API_SECRET` opcional, enviada como `X-API-Secret` e `X-Expandi-API-Secret`
- `EXPANDI_CAMPAIGN_ID` opcional, incluída no payload do webhook
- `EXPANDI_STATUS_WEBHOOK_SECRET` segredo opcional para o callback `POST /v1/providers/expandi/status`; envie o valor no header `X-Expandi-Webhook-Secret`
- `EXPANDI_LINKEDIN_ACCOUNT_ID` opcional para filtrar o polling de status por conta LinkedIn no Expandi
- `EXPANDI_STATUS_POLL_URL` opcional para sobrescrever a URL consultada por `POST /v1/tenants/{tenant_id}/providers/expandi/poll`; aceita `{campaign_id}` e `{limit}`
- `LINKEDIN_SEARCH_WEBHOOK_URL`
- `APOLLO_API_KEY`
- `CANDIDATE_ENRICHMENT_WEBHOOK_URL`
- `CANDIDATE_CLASSIFICATION_WEBHOOK_URL`
- `OUTREACH_TEMPLATE_WEBHOOK_URL`
- `LLM_PROVIDER` opcional: `openai` ou `openrouter`
- `OPENAI_API_KEY`
- `OPENAI_MODEL` default: `gpt-4.1-mini`
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL` default: `deepseek/deepseek-v4-flash`
- `HUNTER_API_KEY`
- `NOTION_MIRROR_API_TOKEN`
- `NOTION_MIRROR_TENANTS_DATA_SOURCE_ID`
- `NOTION_MIRROR_CANDIDATES_DATA_SOURCE_ID`
- `NOTION_MIRROR_INTERACTIONS_DATA_SOURCE_ID`
- `NOTION_MIRROR_WORKFLOW_RUNS_DATA_SOURCE_ID`
- `NOTION_MIRROR_AUDIT_EVENTS_DATA_SOURCE_ID`

Se os endpoints de canal ou agentes nao estiverem configurados, a activity roda em `dry-run` e retorna o payload que seria enviado. Isso permite validar o fluxo Temporal sem acoplar credenciais antes da hora.

O lifecycle do candidato ja chama agentes operacionais em sequencia:

1. enriquecimento de perfil
2. classificacao de fit
3. renderizacao de mensagem por canal
4. envio por email e/ou LinkedIn

Os webhooks podem ser conectados a provedores reais de sourcing, enriquecimento, LLM ou automacao de canal mantendo o mesmo contrato de workflow.
Quando `OPENAI_API_KEY` ou `OPENROUTER_API_KEY` estiverem configuradas, as activities de classificacao e renderizacao de mensagem usam LLM diretamente antes de recorrer aos webhooks/dry-run. A ordem padrao e OpenAI primeiro e OpenRouter depois, mas `LLM_PROVIDER=openrouter` prioriza o OpenRouter com `deepseek/deepseek-v4-flash`. A IA gera score, classificacao, justificativa, resumo e copy inicial; o envio continua bloqueado por aprovacao humana na UI.

A rota `POST /v1/tenants/{tenant_id}/sourcing/apollo/search` consulta Apollo.io quando `APOLLO_API_KEY` esta configurada. Ela cria workflows de candidato para perfis com e-mail ou LinkedIn retornados pela Apollo; quando a chave nao existe, retorna uma mensagem clara de configuracao pendente sem criar candidatos.

A rota `POST /v1/tenants/{tenant_id}/sourcing/apollo/enrich` usa o `apollo_person_id` salvo na busca para completar nome, LinkedIn, empresa e dominio antes da chamada ao Hunter. Se a Apollo devolver e-mail ou LinkedIn, o lifecycle dos agentes pode iniciar diretamente; se devolver apenas nome e dominio, o candidato fica pronto para Hunter.

A rota `POST /v1/tenants/{tenant_id}/enrichment/hunter/run` consulta Hunter.io quando `HUNTER_API_KEY` esta configurada. Ela encontra e-mails profissionais para candidatos pendentes de contato e inicia o lifecycle dos agentes apenas quando existe canal valido. Candidatos sem nome completo, dominio da empresa ou LinkedIn ficam marcados como pendentes de dados.

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

Bootstrap do primeiro membro SaaS:

```bash
export TICRM_BOOTSTRAP_TENANT_ID=api-controlled-003
export TICRM_BOOTSTRAP_USER_EMAIL=<email-do-usuario-supabase-auth>
export TICRM_BOOTSTRAP_ROLE=owner
make bootstrap-tenant-member
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
- `NEXT_PUBLIC_SITE_URL=http://localhost:3000`
- `TICRM_API_KEY=<admin-ou-tenant-api-key>` para modo server-to-server/dev
- `NEXT_PUBLIC_SUPABASE_URL=<supabase-url>` para login humano
- `NEXT_PUBLIC_SUPABASE_ANON_KEY=<supabase-anon-key>` para login humano
- `NEXT_PUBLIC_DEFAULT_TENANT_ID=api-controlled-003`

A chave da API e usada apenas server-side pelo Next.js. Em modo SaaS, o login humano grava cookies httpOnly de sessao/refresh e a UI chama a API com `Authorization: Bearer`.
Para login Google, o Supabase Auth deve ter o provider Google ativo e o redirect `/auth/callback` cadastrado.

Ativar Google OAuth via Management API:

```bash
export SUPABASE_PROJECT_REF=<project-ref>
export SUPABASE_ACCESS_TOKEN=<supabase-management-token>
export GOOGLE_OAUTH_CLIENT_ID=<google-client-id>
export GOOGLE_OAUTH_CLIENT_SECRET=<google-client-secret>
make activate-google-provider
```

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

## Production Readiness Check

Antes de deploy/staging, rode:

```bash
make prod-readiness
```

O comando valida variaveis obrigatorias sem imprimir valores sensiveis, bloqueia producao com `TICRM_ALLOW_INSECURE_DEV_AUTH=true` e checa URLs publicas de Supabase/site.

## Auth Roadmap

A estrategia de login SaaS esta documentada em `docs/auth-strategy.md`. O projeto mantem API keys para automacoes server-to-server e usa Supabase Auth + `tenant_memberships` para login humano por tenant. A API valida o JWT com `SUPABASE_JWT_SECRET`.

## Tenant Memberships

A API possui CRUD inicial para memberships de tenant:

- `GET /v1/tenants/{tenant_id}/memberships`
- `POST /v1/tenants/{tenant_id}/memberships`
- `DELETE /v1/tenants/{tenant_id}/memberships/{membership_id}`

A UI possui `/members` para gerenciar membros. O formulario aceita e-mail como caminho principal: a API resolve o usuario em `auth.users` e grava `tenant_memberships`. A remocao pode ser feita diretamente pela linha do membro cadastrado. Esses registros definem a empresa e o papel usados pelo login humano SaaS.

As mutacoes operacionais relevantes geram audit events em `audit_events`, incluindo criacao/remoção de memberships, criacao/revogacao/rotacao de chaves de API e solicitacao de onboarding/candidato.

## Workflow Runs

A API expoe `GET /v1/tenants/{tenant_id}/workflow-runs` e a UI possui `/workflows` para observar execucoes Temporal por tenant.

## Tenant Administration

A API expoe `GET /v1/tenants` para admins e a UI possui `/tenants` com listagem multiempresa e link para cada tenant.
