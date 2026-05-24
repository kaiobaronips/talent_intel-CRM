import Link from 'next/link';
import { CandidateCreateForm, TenantCreateForm } from '@/components/ActionForms';
import { ContextPanel } from '@/components/ContextPanel';
import { DataTable } from '@/components/DataTable';
import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getCandidates, getInteractions, getTenant, getTenantMetrics } from '@/lib/api';
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
      title="Painel de controle para recrutamento inteligente"
      subtitle="Uma visão operacional para empresas, candidatos, cadências por canal, backlog e execução dos fluxos Temporal."
    >
      <section className="stagger grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Empresa ativa" value={tenantResult.data.company_name} detail={tenantResult.data.tier ?? tenantResult.data.id} accent="ink" />
        <MetricCard label="Candidatos" value={candidatesResult.data.pagination.total} detail="base atual" accent="green" />
        <MetricCard label="Fila" value={backlogTotal} detail="e-mail + LinkedIn" accent="amber" />
        <MetricCard label="Execuções" value={workflowTotal} detail={`${metrics.workflow_runs.running ?? 0} em execução`} accent="blue" />
      </section>

      <ContextPanel tenantId={tenantId} principal={principal.data} offline={offline || principal.offline} />

      <section className="grid gap-6 xl:grid-cols-2">
        {principal.data.is_admin ? <TenantCreateForm /> : null}
        <CandidateCreateForm tenantId={tenantId} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <DataTable<Candidate>
          eyebrow="Pipeline"
          title="Candidatos recentes"
          rows={candidates}
          columns={[
            { key: 'name', label: 'Nome', render: (row) => row.name },
            { key: 'role', label: 'Cargo', render: (row) => row.current_role ?? 'Não informado' },
            { key: 'score', label: 'Pontuação', render: (row) => row.score_overall ?? '-' },
            { key: 'stage', label: 'Etapa', render: (row) => <StatusBadge value={row.stage} /> },
          ]}
        />

        <div className="rounded-[2rem] border border-stone-200 bg-stone-950 p-5 text-stone-50 shadow-[0_24px_70px_rgba(41,37,36,0.16)]">
          <p className="text-xs font-bold uppercase tracking-[0.24em] text-amber-200">Canais</p>
          <h2 className="mt-2 font-display text-3xl font-black tracking-[-0.05em]">Fila de contatos</h2>
          <div className="mt-6 space-y-3">
            {metrics.channel_backlog.map((item) => (
              <div key={item.channel} className="rounded-2xl border border-white/10 bg-white/8 p-4">
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
          <Link href="/interactions" className="mt-6 inline-flex rounded-full bg-amber-300 px-5 py-3 text-sm font-black text-stone-950 transition hover:bg-amber-200">
            Ver interações
          </Link>
        </div>
      </section>

      <DataTable<Interaction>
        eyebrow="Cadência"
        title="Interações em movimento"
        rows={interactions}
        columns={[
          { key: 'candidate', label: 'Candidato', render: (row) => row.candidate_name ?? row.candidate_id },
          { key: 'channel', label: 'Canal', render: (row) => <StatusBadge value={row.channel} /> },
          { key: 'status', label: 'Interação', render: (row) => <StatusBadge value={row.interaction_status} /> },
          { key: 'next', label: 'Próxima ação', render: (row) => row.next_action ?? '-' },
        ]}
      />
    </Shell>
  );
}
