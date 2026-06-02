import Link from 'next/link';
import { ApolloCandidateSearchForm, CandidateCreateForm } from '@/components/ActionForms';
import { CandidateTalentCards } from '@/components/CandidateTalentCards';
import { ContextPanel } from '@/components/ContextPanel';
import { DataTable } from '@/components/DataTable';
import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getCandidates, getTenant } from '@/lib/api';
import { formatScore } from '@/lib/format';
import { resolveActiveTenantId } from '@/lib/session';
import type { Candidate } from '@/lib/types';

export const dynamic = 'force-dynamic';

export default async function CandidatesPage() {
  const { tenantId, principal, authOptions } = await resolveActiveTenantId();
  const [tenantResult, candidatesResult] = await Promise.all([getTenant(tenantId, authOptions), getCandidates(tenantId, 50, authOptions)]);
  const candidates = candidatesResult.data.items;
  const candidatesTotal = candidatesResult.data.pagination.total;
  const withEmail = candidates.filter((candidate) => Boolean(candidate.email)).length;
  const withLinkedIn = candidates.filter((candidate) => Boolean(candidate.linkedin_url)).length;
  const highPriority = candidates.filter((candidate) => (candidate.classification ?? '').toLowerCase() === 'a' || (candidate.score_overall ?? 0) >= 80).length;

  return (
    <Shell
      offline={tenantResult.offline || candidatesResult.offline}
      title="Central de candidatos"
      subtitle={`Base de talentos da empresa ${tenantResult.data.company_name}. Use esta tela para comparar perfis, priorizar abordagens e abrir a análise completa de cada candidato.`}
    >
      <section className="stagger grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Total na base" value={candidatesTotal} detail="candidatos monitorados" accent="ink" />
        <MetricCard label="Alta prioridade" value={highPriority} detail="para abordagem" accent="amber" />
        <MetricCard label="Com e-mail" value={withEmail} accent="green" />
        <MetricCard label="Com LinkedIn" value={withLinkedIn} accent="blue" />
      </section>

      <ContextPanel tenantId={tenantId} principal={principal.data} offline={tenantResult.offline || candidatesResult.offline || principal.offline} />

      <CandidateTalentCards candidates={candidates} />

      <ApolloCandidateSearchForm tenantId={tenantId} />

      <CandidateCreateForm tenantId={tenantId} />

      <DataTable<Candidate>
        eyebrow="Registro completo"
        title="Tabela da base de candidatos"
        rows={candidates}
        columns={[
          { key: 'name', label: 'Nome', render: (row) => <Link href={`/candidates/${row.id}`} className="font-black text-stone-950 underline decoration-amber-400 decoration-2 underline-offset-4">{row.name}</Link> },
          { key: 'location', label: 'Local', render: (row) => [row.city, row.state].filter(Boolean).join(' / ') || 'Não informado' },
          { key: 'email', label: 'E-mail', render: (row) => row.email ?? '-' },
          { key: 'linkedin', label: 'LinkedIn', render: (row) => (row.linkedin_url ? 'Disponível' : '-') },
          { key: 'role', label: 'Cargo', render: (row) => row.current_role ?? '-' },
          { key: 'company', label: 'Empresa', render: (row) => row.current_company ?? '-' },
          { key: 'seniority', label: 'Senioridade', render: (row) => row.seniority ?? '-' },
          { key: 'score', label: 'Aderência', render: (row) => formatScore(row.score_overall) },
          { key: 'classification', label: 'Prioridade', render: (row) => <StatusBadge value={row.classification} /> },
        ]}
      />
    </Shell>
  );
}
