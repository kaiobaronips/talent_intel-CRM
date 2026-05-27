import { ApiKeyCreateForm, ApiKeyLifecycleForm, CandidateCreateForm } from '@/components/ActionForms';
import { DataTable } from '@/components/DataTable';
import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getApiKeys, getCandidates, getInteractions, getTenant, getTenantMetrics } from '@/lib/api';
import { formatScore } from '@/lib/format';
import { getSessionToken, requireAuthenticatedPrincipal } from '@/lib/session';
import type { ApiKey, Candidate, Interaction } from '@/lib/types';

export const dynamic = 'force-dynamic';

type TenantPageProps = {
  params: Promise<{ tenantId: string }>;
};

export default async function TenantPage({ params }: TenantPageProps) {
  const { tenantId } = await params;
  await requireAuthenticatedPrincipal();
  const token = await getSessionToken();
  const authOptions = token ? { bearerToken: token, apiKeyFallback: false } : { apiKeyFallback: false };
  const [tenantResult, metricsResult, candidatesResult, interactionsResult, keysResult] = await Promise.all([
    getTenant(tenantId, authOptions),
    getTenantMetrics(tenantId, authOptions),
    getCandidates(tenantId, 8, authOptions),
    getInteractions(tenantId, 8, authOptions),
    getApiKeys(tenantId, authOptions),
  ]);

  const offline = tenantResult.offline || metricsResult.offline || candidatesResult.offline || interactionsResult.offline || keysResult.offline;
  const tenant = tenantResult.data;
  const backlogTotal = metricsResult.data.channel_backlog.reduce((sum, item) => sum + item.pending, 0);

  return (
    <Shell offline={offline} title={tenant.company_name} subtitle={`Painel da empresa com candidatos, contatos planejados e integrações ativas.`}>
      <section className="stagger grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Status" value={tenant.status ?? 'ativo'} accent="green" />
        <MetricCard label="Candidatos" value={candidatesResult.data.items.length} detail="em acompanhamento" accent="blue" />
        <MetricCard label="Contatos pendentes" value={backlogTotal} detail="por canal" accent="amber" />
        <MetricCard label="Integrações" value={keysResult.data.length} detail="chaves ativas ou cadastradas" accent="ink" />
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <CandidateCreateForm tenantId={tenantId} />
        <ApiKeyCreateForm tenantId={tenantId} />
      </section>

      <ApiKeyLifecycleForm tenantId={tenantId} />

      <DataTable<ApiKey>
        eyebrow="Segurança"
        title="Chaves de integração"
        rows={keysResult.data}
        columns={[
          { key: 'name', label: 'Nome', render: (row) => row.name },
          { key: 'status', label: 'Status', render: (row) => <StatusBadge value={row.status} /> },
          { key: 'last_used', label: 'Último uso', render: (row) => row.last_used_at ?? 'Nunca' },
          { key: 'expires', label: 'Expira', render: (row) => row.expires_at ?? 'Sem expiração' },
        ]}
      />

      <section className="grid gap-6 xl:grid-cols-2">
        <DataTable<Candidate>
          eyebrow="Empresa"
          title="Candidatos"
          rows={candidatesResult.data.items}
          columns={[
            { key: 'name', label: 'Nome', render: (row) => row.name },
            { key: 'role', label: 'Cargo', render: (row) => row.current_role ?? '-' },
            { key: 'score', label: 'Aderência', render: (row) => formatScore(row.score_overall) },
            { key: 'classification', label: 'Prioridade', render: (row) => <StatusBadge value={row.classification} /> },
            { key: 'stage', label: 'Situação', render: (row) => <StatusBadge value={row.stage} /> },
          ]}
        />

        <DataTable<Interaction>
          eyebrow="Empresa"
          title="Contatos"
          rows={interactionsResult.data.items}
          columns={[
            { key: 'candidate', label: 'Candidato', render: (row) => row.candidate_name ?? row.candidate_id },
            { key: 'channel', label: 'Canal', render: (row) => <StatusBadge value={row.channel} /> },
            { key: 'next', label: 'Próxima', render: (row) => row.next_action ?? '-' },
          ]}
        />
      </section>
    </Shell>
  );
}
