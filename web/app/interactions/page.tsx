import { ContextPanel } from '@/components/ContextPanel';
import { DataTable } from '@/components/DataTable';
import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getInteractions, getTenantMetrics } from '@/lib/api';
import { resolveActiveTenantId } from '@/lib/session';
import type { Interaction } from '@/lib/types';

export const dynamic = 'force-dynamic';

export default async function InteractionsPage() {
  const { tenantId, principal } = await resolveActiveTenantId();
  const [interactionsResult, metricsResult] = await Promise.all([getInteractions(tenantId, 50), getTenantMetrics(tenantId)]);
  const interactions = interactionsResult.data.items;
  const linkedin = interactions.filter((interaction) => interaction.channel === 'linkedin').length;
  const email = interactions.filter((interaction) => interaction.channel === 'email').length;
  const backlogTotal = metricsResult.data.channel_backlog.reduce((sum, item) => sum + item.pending, 0);

  return (
    <Shell offline={interactionsResult.offline || metricsResult.offline} title="Interações por canal" subtitle="Fila separada por LinkedIn e e-mail. Não existe bloqueio operacional por score ou canal alternativo.">
      <section className="stagger grid gap-4 md:grid-cols-3">
        <MetricCard label="Fila total" value={backlogTotal} accent="amber" />
        <MetricCard label="LinkedIn" value={linkedin} detail="interações" accent="blue" />
        <MetricCard label="E-mail" value={email} detail="interações" accent="green" />
      </section>

      <ContextPanel tenantId={tenantId} principal={principal.data} offline={interactionsResult.offline || metricsResult.offline || principal.offline} />

      <DataTable<Interaction>
        eyebrow="Cadência"
        title="Fila operacional"
        rows={interactions}
        columns={[
          { key: 'candidate', label: 'Candidato', render: (row) => row.candidate_name ?? row.candidate_id },
          { key: 'channel', label: 'Canal', render: (row) => <StatusBadge value={row.channel} /> },
          { key: 'interaction', label: 'Interação', render: (row) => <StatusBadge value={row.interaction_status} /> },
          { key: 'next', label: 'Próxima ação', render: (row) => <StatusBadge value={row.next_action} /> },
          { key: 'sent', label: 'Mensagem', render: (row) => row.message_sent ?? '-' },
          { key: 'response', label: 'Resposta', render: (row) => row.response_received ?? '-' },
        ]}
      />
    </Shell>
  );
}
