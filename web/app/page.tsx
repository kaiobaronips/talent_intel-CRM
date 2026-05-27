import Link from 'next/link';
import { CandidateCreateForm, TenantCreateForm } from '@/components/ActionForms';
import { ContextPanel } from '@/components/ContextPanel';
import { DataTable } from '@/components/DataTable';
import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getCandidates, getInteractions, getTenant, getTenantMetrics } from '@/lib/api';
import { formatScore } from '@/lib/format';
import { resolveActiveTenantId } from '@/lib/session';
import type { Candidate, Interaction } from '@/lib/types';

export const dynamic = 'force-dynamic';

export default async function DashboardPage() {
  const { tenantId, principal, authOptions } = await resolveActiveTenantId();
  const [tenantResult, metricsResult, candidatesResult, interactionsResult] = await Promise.all([
    getTenant(tenantId, authOptions),
    getTenantMetrics(tenantId, authOptions),
    getCandidates(tenantId, 6, authOptions),
    getInteractions(tenantId, 6, authOptions),
  ]);

  const offline = tenantResult.offline || metricsResult.offline || candidatesResult.offline || interactionsResult.offline;
  const metrics = metricsResult.data;
  const candidates = candidatesResult.data.items;
  const interactions = interactionsResult.data.items;
  const workflowTotal = Object.values(metrics.workflow_runs).reduce<number>((sum, value) => sum + (typeof value === 'number' ? value : 0), 0);
  const backlogTotal = metrics.channel_backlog.reduce((sum, item) => sum + item.pending, 0);

  return (
    <Shell
      offline={offline}
      title="Visão geral do recrutamento"
      subtitle="Acompanhe quantos candidatos estão na base, quais contatos estão pendentes e se as automações de IA estão trabalhando."
    >
      <section className="stagger grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Empresa" value={tenantResult.data.company_name} detail={tenantResult.data.tier ?? tenantResult.data.id} accent="ink" />
        <MetricCard label="Candidatos na base" value={candidates.length} detail="talentos monitorados" accent="green" />
        <MetricCard label="Contatos pendentes" value={backlogTotal} detail="e-mail + LinkedIn" accent="amber" />
        <MetricCard label="Automações" value={workflowTotal} detail={`${metrics.workflow_runs.running ?? 0} em andamento`} accent="blue" />
      </section>

      <ContextPanel tenantId={tenantId} principal={principal.data} offline={offline || principal.offline} />

      <section className="grid gap-6 xl:grid-cols-2">
        {principal.data.is_admin ? <TenantCreateForm /> : null}
        <CandidateCreateForm tenantId={tenantId} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <DataTable<Candidate>
          eyebrow="Pipeline"
          title="Candidatos em acompanhamento"
          rows={candidates}
          columns={[
            { key: 'name', label: 'Nome', render: (row) => row.name },
            { key: 'role', label: 'Cargo', render: (row) => row.current_role ?? 'Não informado' },
            { key: 'score', label: 'Aderência', render: (row) => formatScore(row.score_overall) },
            { key: 'stage', label: 'Situação', render: (row) => <StatusBadge value={row.stage} /> },
          ]}
        />

        <div className="rounded-lg border border-stone-200 bg-stone-950 p-5 text-stone-50 shadow-sm">
          <p className="text-xs font-bold uppercase text-amber-200">Canais</p>
          <h2 className="mt-2 font-display text-3xl font-black">Contatos pendentes</h2>
          <div className="mt-6 space-y-3">
            {metrics.channel_backlog.map((item) => (
              <div key={item.channel} className="rounded-lg border border-white/10 bg-white/8 p-4">
                <div className="flex items-center justify-between">
                  <span className="font-bold capitalize">{item.channel === 'linkedin' ? 'LinkedIn' : 'E-mail'}</span>
                  <span className="font-monoish text-2xl font-black">{item.pending}</span>
                </div>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10">
                  <div className="h-full rounded-full bg-amber-300" style={{ width: `${Math.min(100, item.pending * 18)}%` }} />
                </div>
              </div>
            ))}
          </div>
          <Link href="/interactions" className="mt-6 inline-flex rounded-lg bg-amber-300 px-5 py-3 text-sm font-black text-stone-950 transition hover:bg-amber-200">
            Ver contatos
          </Link>
        </div>
      </section>

      <DataTable<Interaction>
        eyebrow="Cadência"
        title="Próximas abordagens"
        rows={interactions}
        columns={[
          { key: 'candidate', label: 'Candidato', render: (row) => row.candidate_name ?? row.candidate_id },
          { key: 'channel', label: 'Canal', render: (row) => <StatusBadge value={row.channel} /> },
          { key: 'status', label: 'Situação', render: (row) => <StatusBadge value={row.interaction_status} /> },
          { key: 'next', label: 'Próxima ação', render: (row) => row.next_action ?? '-' },
        ]}
      />
    </Shell>
  );
}
