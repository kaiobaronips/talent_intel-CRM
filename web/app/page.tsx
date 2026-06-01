import Link from 'next/link';
import { CandidateCreateForm, TenantCreateForm } from '@/components/ActionForms';
import { ContextPanel } from '@/components/ContextPanel';
import { DataTable } from '@/components/DataTable';
import { InteractionContactCards } from '@/components/InteractionContactCards';
import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getCandidates, getInteractions, getTenant, getTenantMetrics } from '@/lib/api';
import { formatScore, formatStatus } from '@/lib/format';
import { resolveActiveTenantId } from '@/lib/session';
import type { Candidate, Interaction } from '@/lib/types';

export const dynamic = 'force-dynamic';

function interactionStatus(interaction: Interaction) {
  return (interaction.status ?? interaction.interaction_status ?? 'pending').toLowerCase();
}

function channelLabel(channel: string) {
  return channel === 'linkedin' ? 'LinkedIn' : channel === 'email' ? 'E-mail' : channel;
}

function candidatePriority(candidate: Candidate) {
  const score = candidate.score_overall ?? 0;
  const classification = (candidate.classification ?? '').toLowerCase();
  if (classification === 'a' || score >= 80) return 'Alta prioridade';
  if (classification === 'b' || score >= 60) return 'Boa aderência';
  return 'Acompanhar';
}

export default async function DashboardPage() {
  const { tenantId, principal, authOptions } = await resolveActiveTenantId();
  const [tenantResult, metricsResult, candidatesResult, interactionsResult] = await Promise.all([
    getTenant(tenantId, authOptions),
    getTenantMetrics(tenantId, authOptions),
    getCandidates(tenantId, 12, authOptions),
    getInteractions(tenantId, 12, authOptions),
  ]);

  const offline = tenantResult.offline || metricsResult.offline || candidatesResult.offline || interactionsResult.offline;
  const metrics = metricsResult.data;
  const candidates = candidatesResult.data.items;
  const interactions = interactionsResult.data.items;
  const candidatesTotal = candidatesResult.data.pagination.total;
  const workflowCompleted = metrics.workflow_runs.completed ?? metrics.workflow_runs.total ?? 0;
  const backlogTotal = metrics.channel_backlog.reduce((sum, item) => sum + item.pending, 0);
  const repliedContacts = interactions.filter((interaction) => ['replied', 'closed'].includes(interactionStatus(interaction))).length;
  const priorityCandidates = [...candidates]
    .sort((a, b) => (b.score_overall ?? 0) - (a.score_overall ?? 0))
    .slice(0, 4);
  const pendingInteractions = interactions.filter((interaction) => interactionStatus(interaction) === 'pending').slice(0, 4);
  const nextAction =
    pendingInteractions[0]
      ? `Enviar abordagem para ${pendingInteractions[0].candidate_name ?? pendingInteractions[0].candidate_id} via ${channelLabel(pendingInteractions[0].channel)}.`
      : repliedContacts > 0
        ? 'Revisar respostas recebidas e definir a próxima conversa com o candidato.'
        : candidatesTotal > 0
          ? 'Cadastrar ou revisar novos candidatos para gerar mais abordagens.'
          : 'Cadastrar o primeiro candidato para iniciar o ciclo dos agentes.';

  return (
    <Shell
      offline={offline}
      title="Painel executivo de recrutamento"
      subtitle="Entenda rapidamente o tamanho da base, o que precisa de ação agora e se os agentes de IA estão prontos para continuar o trabalho."
    >
      <section className="stagger grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Empresa" value={tenantResult.data.company_name} detail={tenantResult.data.tier ?? tenantResult.data.id} accent="ink" />
        <MetricCard label="Candidatos na base" value={candidatesTotal} detail="talentos monitorados" accent="green" />
        <MetricCard label="Contatos pendentes" value={backlogTotal} detail="e-mail + LinkedIn" accent="amber" />
        <MetricCard label="Automações concluídas" value={workflowCompleted} detail={`${metrics.workflow_runs.running ?? 0} em andamento`} accent="blue" />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <article className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-bold uppercase text-amber-700">O que fazer agora</p>
          <h2 className="mt-2 font-display text-3xl font-black text-stone-950">{nextAction}</h2>
          <div className="mt-5 grid gap-3 md:grid-cols-3">
            <div className="rounded-lg bg-stone-50 p-4">
              <p className="text-xs font-bold uppercase text-stone-500">Pronto para contato</p>
              <p className="mt-2 font-display text-3xl font-black text-stone-950">{backlogTotal}</p>
            </div>
            <div className="rounded-lg bg-stone-50 p-4">
              <p className="text-xs font-bold uppercase text-stone-500">Respostas registradas</p>
              <p className="mt-2 font-display text-3xl font-black text-stone-950">{repliedContacts}</p>
            </div>
            <div className="rounded-lg bg-stone-50 p-4">
              <p className="text-xs font-bold uppercase text-stone-500">Status da operação</p>
              <p className="mt-2 text-base font-black text-stone-950">{offline ? 'Atenção na conexão' : 'Operação conectada'}</p>
            </div>
          </div>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link href="/interactions" className="rounded-lg bg-stone-950 px-5 py-3 text-sm font-black text-white transition hover:bg-stone-800">
              Ver contatos pendentes
            </Link>
            <Link href="/candidates" className="rounded-lg border border-stone-200 bg-white px-5 py-3 text-sm font-black text-stone-800 transition hover:bg-stone-50">
              Ver base de candidatos
            </Link>
          </div>
        </article>

        <article className="rounded-lg border border-stone-200 bg-stone-950 p-5 text-stone-50 shadow-sm">
          <p className="text-xs font-bold uppercase text-amber-200">Saúde do MVP</p>
          <h2 className="mt-2 font-display text-3xl font-black">Sistema pronto para uso</h2>
          <div className="mt-5 grid gap-3">
            <div className="flex items-center justify-between gap-4 rounded-lg border border-white/10 bg-white/8 p-4">
              <span className="font-bold">API e banco de dados</span>
              <StatusBadge value={offline ? 'offline' : 'connected'} />
            </div>
            <div className="flex items-center justify-between gap-4 rounded-lg border border-white/10 bg-white/8 p-4">
              <span className="font-bold">Agentes e automações</span>
              <StatusBadge value={(metrics.workflow_runs.failed ?? 0) > 0 ? 'failed' : 'completed'} />
            </div>
            <div className="flex items-center justify-between gap-4 rounded-lg border border-white/10 bg-white/8 p-4">
              <span className="font-bold">Login e permissões</span>
              <StatusBadge value={principal.offline ? 'offline' : 'active'} />
            </div>
          </div>
        </article>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <ContextPanel tenantId={tenantId} principal={principal.data} offline={offline || principal.offline} />
        <CandidateCreateForm tenantId={tenantId} />
      </section>
      {principal.data.is_admin ? <TenantCreateForm /> : null}

      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <DataTable<Candidate>
          eyebrow="Prioridade"
          title="Candidatos que merecem atenção"
          rows={priorityCandidates}
          columns={[
            { key: 'name', label: 'Nome', render: (row) => <Link href={`/candidates/${row.id}`} className="font-black text-stone-950 underline decoration-amber-400 decoration-2 underline-offset-4">{row.name}</Link> },
            { key: 'role', label: 'Cargo', render: (row) => row.current_role ?? 'Não informado' },
            { key: 'score', label: 'Aderência', render: (row) => formatScore(row.score_overall) },
            { key: 'priority', label: 'Prioridade', render: (row) => candidatePriority(row) },
          ]}
        />

        <div className="rounded-lg border border-stone-200 bg-stone-950 p-5 text-stone-50 shadow-sm">
          <p className="text-xs font-bold uppercase text-amber-200">Canais</p>
          <h2 className="mt-2 font-display text-3xl font-black">Contatos pendentes</h2>
          <div className="mt-6 space-y-3">
            {metrics.channel_backlog.map((item) => (
              <div key={item.channel} className="rounded-lg border border-white/10 bg-white/8 p-4">
                <div className="flex items-center justify-between">
                  <span className="font-bold">{channelLabel(item.channel)}</span>
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

      <InteractionContactCards interactions={pendingInteractions} tenantId={tenantId} showCandidateLink />

      <DataTable<Interaction>
        eyebrow="Registro recente"
        title="Últimas abordagens preparadas"
        rows={interactions}
        columns={[
          { key: 'candidate', label: 'Candidato', render: (row) => <Link href={`/candidates/${row.candidate_id}`} className="font-black text-stone-950 underline decoration-amber-400 decoration-2 underline-offset-4">{row.candidate_name ?? row.candidate_id}</Link> },
          { key: 'channel', label: 'Canal', render: (row) => <StatusBadge value={row.channel} /> },
          { key: 'status', label: 'Situação', render: (row) => <StatusBadge value={row.status ?? row.interaction_status} /> },
          { key: 'next', label: 'Próxima ação', render: (row) => formatStatus(row.next_action) },
        ]}
      />
    </Shell>
  );
}
