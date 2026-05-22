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

## Comandos iniciais

```bash
python -m talent_intel_crm.worker
```

Para disparos controlados:

```bash
python -m talent_intel_crm.runner smoke
python -m talent_intel_crm.runner tenant-onboarding --tenant-id acme --company-name "Acme RH"
python -m talent_intel_crm.runner candidate-lifecycle --tenant-id acme --candidate-id cand-001 --name "Jane Doe" --email jane@example.com --channels email linkedin
python -m talent_intel_crm.runner candidate-step --step outreach --tenant-id acme --candidate-id cand-001 --name "Jane Doe" --email jane@example.com --linkedin-url https://www.linkedin.com/in/jane-doe --channels email linkedin --stage qualified
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
