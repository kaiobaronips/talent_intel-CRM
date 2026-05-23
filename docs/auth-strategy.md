# Auth Strategy

## Estado atual

A API ja suporta dois escopos por `X-API-Key`:

- `admin`: opera todos os tenants e cria/rotaciona chaves.
- `tenant`: restrita ao tenant dono da chave.

A UI Next.js usa `TICRM_API_KEY` server-side e consulta `GET /v1/me` para descobrir o contexto atual.

## Proxima evolucao SaaS

Para comercializacao, o login humano deve ficar separado das API keys operacionais.

Recomendacao pragmatica:

1. Usar Supabase Auth para usuario/sessao.
2. Criar tabela `tenant_memberships` com `tenant_id`, `user_id`, `role`.
3. A UI usa sessao humana para resolver tenant e role.
4. A API continua aceitando API keys para automacoes e integracoes server-to-server.
5. Server Actions da UI chamam a API com uma chave interna por ambiente, mas validam a permissao da sessao antes de executar.

## Roles

- `owner`: billing, API keys, membros, tenants.
- `admin`: candidatos, cadencias, auditoria, API keys do tenant.
- `recruiter`: candidatos e interacoes.
- `viewer`: leitura de dashboard, auditoria e metricas.

## Regras

- Usuario humano nunca recebe `TICRM_ADMIN_API_KEY` no browser.
- API key de tenant nunca acessa outro tenant.
- Admin global deve ser usado apenas por backend/control plane.
- Toda acao mutavel deve gerar audit event.

## Gates para implementar login

- Escolher provedor: Supabase Auth recomendado por ja existir Supabase Postgres.
- Criar schema `tenant_memberships`.
- Adicionar middleware Next.js para proteger rotas.
- Adicionar BFF/route handlers ou Server Actions com validacao de sessao.
- Remover `NEXT_PUBLIC_DEFAULT_TENANT_ID` como mecanismo principal para usuarios humanos.
