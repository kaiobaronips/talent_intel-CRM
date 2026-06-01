import Link from 'next/link';
import { CandidateJourney } from '@/components/CandidateJourney';
import { DataTable } from '@/components/DataTable';
import { InteractionContactCards } from '@/components/InteractionContactCards';
import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getCandidate, getCandidateInteractions } from '@/lib/api';
import { formatDateTime, formatScore } from '@/lib/format';
import { resolveActiveTenantId } from '@/lib/session';
import type { Interaction } from '@/lib/types';

export const dynamic = 'force-dynamic';

type CandidateDetailPageProps = {
  params: Promise<{ candidateId: string }>;
};

function cleanValue(value?: string | number | null) {
  return value === null || value === undefined || value === '' ? 'Não informado' : value;
}

function channelLabel(channel: string) {
  return channel === 'linkedin' ? 'LinkedIn' : channel === 'email' ? 'E-mail' : channel;
}

export default async function CandidateDetailPage({ params }: CandidateDetailPageProps) {
  const { candidateId } = await params;
  const { tenantId, authOptions } = await resolveActiveTenantId();
  const [candidateResult, interactionsResult] = await Promise.all([
    getCandidate(candidateId, authOptions),
    getCandidateInteractions(candidateId, authOptions),
  ]);

  const candidate = candidateResult.data;
  const interactions = interactionsResult.data;
  const availableChannels = [
    candidate.email ? 'E-mail' : null,
    candidate.linkedin_url ? 'LinkedIn' : null,
  ].filter(Boolean);
  const pendingContacts = interactions.filter((interaction) => (interaction.status ?? interaction.interaction_status ?? '').toLowerCase() === 'pending').length;

  return (
    <Shell
      offline={candidateResult.offline || interactionsResult.offline}
      title={candidate.name}
      subtitle="Veja por que este candidato foi priorizado, quais canais estão disponíveis e quais contatos os agentes prepararam."
    >
      <div>
        <Link href="/candidates" className="inline-flex rounded-lg border border-stone-200 bg-white px-4 py-2 text-sm font-bold text-stone-700 transition hover:bg-stone-50">
          Voltar para candidatos
        </Link>
      </div>

      <section className="stagger grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Aderência ao perfil" value={formatScore(candidate.score_overall)} detail="nota dos agentes" accent="green" />
        <MetricCard label="Prioridade" value={candidate.classification ?? 'Sem classe'} detail="para abordagem" accent="amber" />
        <MetricCard label="Situação" value={candidate.stage ?? 'Sem etapa'} detail="no funil" accent="blue" />
        <MetricCard label="Contatos pendentes" value={pendingContacts} detail={availableChannels.join(' + ') || 'sem canal'} accent="ink" />
      </section>

      <CandidateJourney candidate={candidate} interactions={interactions} />

      <section className="grid gap-6 xl:grid-cols-[1fr_0.85fr]">
        <article className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-bold uppercase text-amber-700">Perfil profissional</p>
          <h2 className="mt-2 font-display text-2xl font-black text-stone-950">Resumo do candidato</h2>
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            <div className="rounded-lg bg-stone-50 p-4">
              <p className="text-xs font-bold uppercase text-stone-500">Cargo atual</p>
              <p className="mt-2 font-bold text-stone-950">{cleanValue(candidate.current_role)}</p>
            </div>
            <div className="rounded-lg bg-stone-50 p-4">
              <p className="text-xs font-bold uppercase text-stone-500">Empresa atual</p>
              <p className="mt-2 font-bold text-stone-950">{cleanValue(candidate.current_company)}</p>
            </div>
            <div className="rounded-lg bg-stone-50 p-4">
              <p className="text-xs font-bold uppercase text-stone-500">Localização</p>
              <p className="mt-2 font-bold text-stone-950">{[candidate.city, candidate.state].filter(Boolean).join(' / ') || 'Não informado'}</p>
            </div>
            <div className="rounded-lg bg-stone-50 p-4">
              <p className="text-xs font-bold uppercase text-stone-500">Senioridade</p>
              <p className="mt-2 font-bold text-stone-950">{cleanValue(candidate.seniority)}</p>
            </div>
          </div>
          <div className="mt-3 rounded-lg bg-stone-50 p-4">
            <p className="text-xs font-bold uppercase text-stone-500">Leitura dos agentes</p>
            <p className="mt-2 font-medium leading-7 text-stone-700">{cleanValue(candidate.profile_summary)}</p>
          </div>
          <div className="mt-3 rounded-lg bg-stone-50 p-4">
            <p className="text-xs font-bold uppercase text-stone-500">Por que recebeu esta prioridade</p>
            <p className="mt-2 font-medium leading-7 text-stone-700">{cleanValue(candidate.classification_reason)}</p>
          </div>
          <div className="mt-3 rounded-lg bg-stone-50 p-4">
            <p className="text-xs font-bold uppercase text-stone-500">Recomendação de abordagem</p>
            <p className="mt-2 font-medium leading-7 text-stone-700">{cleanValue(candidate.recommended_action)}</p>
          </div>
        </article>

        <article className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-bold uppercase text-amber-700">Canais de contato</p>
          <h2 className="mt-2 font-display text-2xl font-black text-stone-950">Como abordar</h2>
          <div className="mt-5 space-y-3">
            <div className="rounded-lg bg-stone-50 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="font-bold text-stone-950">E-mail</p>
                <StatusBadge value={candidate.email ? 'active' : undefined} label={candidate.email ? 'Disponível' : 'Não informado'} />
              </div>
              <p className="mt-2 break-all text-sm font-medium text-stone-600">{cleanValue(candidate.email)}</p>
            </div>
            <div className="rounded-lg bg-stone-50 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="font-bold text-stone-950">LinkedIn</p>
                <StatusBadge value={candidate.linkedin_url ? 'active' : undefined} label={candidate.linkedin_url ? 'Disponível' : 'Não informado'} />
              </div>
              <p className="mt-2 break-all text-sm font-medium text-stone-600">{cleanValue(candidate.linkedin_url)}</p>
            </div>
          </div>
        </article>
      </section>

      <InteractionContactCards interactions={interactions} tenantId={tenantId} />

      <DataTable<Interaction>
        eyebrow="Registro operacional"
        title="Histórico completo de contatos"
        rows={interactions}
        emptyLabel="Nenhum contato preparado para este candidato."
        columns={[
          { key: 'channel', label: 'Canal', render: (row) => <StatusBadge value={row.channel} label={channelLabel(row.channel)} /> },
          { key: 'status', label: 'Situação', render: (row) => <StatusBadge value={row.status ?? row.interaction_status} /> },
          { key: 'type', label: 'Tipo', render: (row) => cleanValue(row.message_type) },
          { key: 'next', label: 'Próxima ação', render: (row) => cleanValue(row.next_action) },
          { key: 'message', label: 'Mensagem preparada', render: (row) => cleanValue(row.message_sent) },
          { key: 'created', label: 'Criado em', render: (row) => formatDateTime(row.created_at) },
        ]}
      />
    </Shell>
  );
}
