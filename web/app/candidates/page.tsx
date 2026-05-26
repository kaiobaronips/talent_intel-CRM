import { CandidateCreateForm } from '@/components/ActionForms';
import { ContextPanel } from '@/components/ContextPanel';
import { DataTable } from '@/components/DataTable';
import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getCandidates, getTenant } from '@/lib/api';
import { resolveActiveTenantId } from '@/lib/session';
import type { Candidate } from '@/lib/types';

export const dynamic = 'force-dynamic';

export default async function CandidatesPage() {
  const { tenantId, principal, authOptions } = await resolveActiveTenantId();
  const [tenantResult, candidatesResult] = await Promise.all([getTenant(tenantId, authOptions), getCandidates(tenantId, 50, authOptions)]);
  const candidates = candidatesResult.data.items;
  const withEmail = candidates.filter((candidate) => Boolean(candidate.email)).length;
  const withLinkedIn = candidates.filter((candidate) => Boolean(candidate.linkedin_url)).length;

  return (
    <Shell
      offline={tenantResult.offline || candidatesResult.offline}
      title="Candidatos"
      subtitle={`Base operacional da empresa ${tenantResult.data.company_name}. O score qualifica, mas não bloqueia contato.`}
    >
      <section className="stagger grid gap-4 md:grid-cols-3">
        <MetricCard label="Total" value={candidatesResult.data.pagination.total} accent="ink" />
        <MetricCard label="Com e-mail" value={withEmail} accent="green" />
        <MetricCard label="Com LinkedIn" value={withLinkedIn} accent="blue" />
      </section>

      <ContextPanel tenantId={tenantId} principal={principal.data} offline={tenantResult.offline || candidatesResult.offline || principal.offline} />

      <CandidateCreateForm tenantId={tenantId} />

      <DataTable<Candidate>
        eyebrow="Talentos"
        title="Base limpa para cadência"
        rows={candidates}
        columns={[
          { key: 'name', label: 'Nome', render: (row) => row.name },
          { key: 'location', label: 'Local', render: (row) => [row.city, row.state].filter(Boolean).join(' / ') || 'Não informado' },
          { key: 'email', label: 'E-mail', render: (row) => row.email ?? '-' },
          { key: 'linkedin', label: 'LinkedIn', render: (row) => (row.linkedin_url ? 'Disponível' : '-') },
          { key: 'role', label: 'Cargo', render: (row) => row.current_role ?? '-' },
          { key: 'company', label: 'Empresa', render: (row) => row.current_company ?? '-' },
          { key: 'seniority', label: 'Senioridade', render: (row) => row.seniority ?? '-' },
          { key: 'score', label: 'Pontuação', render: (row) => row.score_overall ?? '-' },
          { key: 'classification', label: 'Classificação', render: (row) => <StatusBadge value={row.classification} /> },
        ]}
      />
    </Shell>
  );
}
