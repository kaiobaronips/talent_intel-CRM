import { DataTable } from '@/components/DataTable';
import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getCandidates, getDefaultTenantId, getTenant } from '@/lib/api';
import type { Candidate } from '@/lib/types';

export const dynamic = 'force-dynamic';

export default async function CandidatesPage() {
  const tenantId = getDefaultTenantId();
  const [tenantResult, candidatesResult] = await Promise.all([getTenant(tenantId), getCandidates(tenantId, 50)]);
  const candidates = candidatesResult.data.items;
  const withEmail = candidates.filter((candidate) => Boolean(candidate.email)).length;
  const withLinkedIn = candidates.filter((candidate) => Boolean(candidate.linkedin_url)).length;

  return (
    <Shell
      offline={tenantResult.offline || candidatesResult.offline}
      title="Candidatos"
      subtitle={`Base operacional do tenant ${tenantResult.data.company_name}. Score qualifica, mas nao bloqueia contato.`}
    >
      <section className="stagger grid gap-4 md:grid-cols-3">
        <MetricCard label="Total" value={candidatesResult.data.pagination.total} accent="ink" />
        <MetricCard label="Com e-mail" value={withEmail} accent="green" />
        <MetricCard label="Com LinkedIn" value={withLinkedIn} accent="blue" />
      </section>

      <DataTable<Candidate>
        eyebrow="Talentos"
        title="Base limpa para cadencia"
        rows={candidates}
        columns={[
          { key: 'name', label: 'Nome', render: (row) => row.name },
          { key: 'location', label: 'Local', render: (row) => [row.city, row.state].filter(Boolean).join(' / ') || 'Nao informado' },
          { key: 'email', label: 'Email', render: (row) => row.email ?? '-' },
          { key: 'linkedin', label: 'LinkedIn', render: (row) => (row.linkedin_url ? 'Disponivel' : '-') },
          { key: 'role', label: 'Cargo', render: (row) => row.current_role ?? '-' },
          { key: 'score', label: 'Score', render: (row) => row.score_overall ?? '-' },
          { key: 'classification', label: 'Classe', render: (row) => <StatusBadge value={row.classification} /> },
        ]}
      />
    </Shell>
  );
}
