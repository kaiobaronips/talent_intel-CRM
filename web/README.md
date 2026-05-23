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
- `TICRM_API_KEY`: chave server-side usada pelo Next para chamar a API. Nunca use `NEXT_PUBLIC_` nessa chave.
- `NEXT_PUBLIC_DEFAULT_TENANT_ID`: tenant inicial exibido no dashboard.

## Telas iniciais

- `/`: Control Tower com metricas, candidatos recentes e fila por canal.
- `/tenants/[tenantId]`: detalhes do tenant, chaves, candidatos e interacoes.
- `/candidates`: base de candidatos pronta para cadencia.
- `/interactions`: fila operacional por LinkedIn e E-mail.

## Regra de seguranca

O app chama a API a partir de Server Components. A chave `TICRM_API_KEY` fica apenas no processo Next.js e nao e enviada ao browser.
