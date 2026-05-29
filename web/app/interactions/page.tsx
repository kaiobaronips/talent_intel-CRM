import Link from 'next/link';
import { ContextPanel } from '@/components/ContextPanel';
import { DataTable } from '@/components/DataTable';
import { InteractionStatusForms } from '@/components/InteractionStatusForms';
import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getInteractions, getTenantMetrics } from '@/lib/api';
import { resolveActiveTenantId } from '@/lib/session';
import type { Interaction } from '@/lib/types';

export const dynamic = 'force-dynamic';

export default async function InteractionsPage() {
  const { tenantId, principal, authOptions } = await resolveActiveTenantId();
  const [interactionsResult, metricsResult] = await Promise.all([getInteractions(tenantId, 50, authOptions), getTenantMetrics(tenantId, authOptions)]);
  const interactions = interactionsResult.data.items;
  const linkedin = interactions.filter((interaction) => interaction.channel === 'linkedin').length;
  const email = interactions.filter((interaction) => interaction.channel === 'email').length;
  const backlogTotal = metricsResult.data.channel_backlog.reduce((sum, item) => sum + item.pending, 0);

  return (
    <Shell offline={interactionsResult.offline || metricsResult.offline} title="Contatos com candidatos" subtitle="Veja quais mensagens estão pendentes por canal e acompanhe a próxima ação planejada para cada candidato.">
      <section className="stagger grid gap-4 md:grid-cols-3">
        <MetricCard label="Contatos pendentes" value={backlogTotal} accent="amber" />
        <MetricCard label="LinkedIn" value={linkedin} detail="abordagens" accent="blue" />
        <MetricCard label="E-mail" value={email} detail="abordagens" accent="green" />
      </section>

      <ContextPanel tenantId={tenantId} principal={principal.data} offline={interactionsResult.offline || metricsResult.offline || principal.offline} />

      <DataTable<Interaction>
        eyebrow="Cadência"
        title="Abordagens planejadas"
        rows={interactions}
        columns={[
          { key: 'candidate', label: 'Candidato', render: (row) => <Link href={`/candidates/${row.candidate_id}`} className="font-black text-stone-950 underline decoration-amber-400 decoration-2 underline-offset-4">{row.candidate_name ?? row.candidate_id}</Link> },
          { key: 'channel', label: 'Canal', render: (row) => <StatusBadge value={row.channel} /> },
          { key: 'interaction', label: 'Situação', render: (row) => <StatusBadge value={row.interaction_status} /> },
          { key: 'next', label: 'Próxima ação', render: (row) => <StatusBadge value={row.next_action} /> },
          { key: 'sent', label: 'Mensagem', render: (row) => row.message_sent ?? '-' },
          { key: 'response', label: 'Resposta', render: (row) => row.response_received ?? '-' },
          { key: 'actions', label: 'Ações', render: (row) => <InteractionStatusForms interaction={row} tenantId={tenantId} /> },
        ]}
      />
    </Shell>
  );
}
