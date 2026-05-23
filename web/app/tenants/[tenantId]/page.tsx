import { ApiKeyCreateForm, ApiKeyLifecycleForm, CandidateCreateForm } from '@/components/ActionForms';
import { DataTable } from '@/components/DataTable';
import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getApiKeys, getCandidates, getInteractions, getTenant, getTenantMetrics } from '@/lib/api';
import type { ApiKey, Candidate, Interaction } from '@/lib/types';

export const dynamic = 'force-dynamic';

type TenantPageProps = {
  params: Promise<{ tenantId: string }>;
};

export default async function TenantPage({ params }: TenantPageProps) {
  const { tenantId } = await params;
  const [tenantResult, metricsResult, candidatesResult, interactionsResult, keysResult] = await Promise.all([
    getTenant(tenantId),
    getTenantMetrics(tenantId),
    getCandidates(tenantId, 8),
    getInteractions(tenantId, 8),
    getApiKeys(tenantId),
  ]);

  const offline = tenantResult.offline || metricsResult.offline || candidatesResult.offline || interactionsResult.offline || keysResult.offline;
  const tenant = tenantResult.data;
  const backlogTotal = metricsResult.data.channel_backlog.reduce((sum, item) => sum + item.pending, 0);

  return (
    <Shell offline={offline} title={tenant.company_name} subtitle={`Tenant ${tenant.id} | ${tenant.timezone ?? 'timezone nao definida'} | plano ${tenant.tier ?? 'nao definido'}`}>
      <section className="stagger grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Status" value={tenant.status ?? 'ativo'} accent="green" />
        <MetricCard label="Candidatos" value={candidatesResult.data.pagination.total} detail="total paginado" accent="blue" />
        <MetricCard label="Backlog" value={backlogTotal} detail="pendencias por canal" accent="amber" />
        <MetricCard label="API keys" value={keysResult.data.length} detail="credenciais tenant" accent="ink" />
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <CandidateCreateForm tenantId={tenantId} />
        <ApiKeyCreateForm tenantId={tenantId} />
      </section>

      <ApiKeyLifecycleForm tenantId={tenantId} />

      <DataTable<ApiKey>
        eyebrow="Seguranca"
        title="Chaves de API do tenant"
        rows={keysResult.data}
        columns={[
          { key: 'name', label: 'Nome', render: (row) => row.name },
          { key: 'status', label: 'Status', render: (row) => <StatusBadge value={row.status} /> },
          { key: 'last_used', label: 'Ultimo uso', render: (row) => row.last_used_at ?? 'Nunca' },
          { key: 'expires', label: 'Expira', render: (row) => row.expires_at ?? 'Sem expiracao' },
        ]}
      />

      <section className="grid gap-6 xl:grid-cols-2">
        <DataTable<Candidate>
          eyebrow="Tenant"
          title="Candidatos"
          rows={candidatesResult.data.items}
          columns={[
            { key: 'name', label: 'Nome', render: (row) => row.name },
            { key: 'classification', label: 'Classe', render: (row) => <StatusBadge value={row.classification} /> },
            { key: 'stage', label: 'Stage', render: (row) => <StatusBadge value={row.stage} /> },
          ]}
        />

        <DataTable<Interaction>
          eyebrow="Tenant"
          title="Interacoes"
          rows={interactionsResult.data.items}
          columns={[
            { key: 'candidate', label: 'Candidato', render: (row) => row.candidate_name ?? row.candidate_id },
            { key: 'channel', label: 'Canal', render: (row) => <StatusBadge value={row.channel} /> },
            { key: 'next', label: 'Proxima', render: (row) => row.next_action ?? '-' },
          ]}
        />
      </section>
    </Shell>
  );
}
