import { ContextPanel } from '@/components/ContextPanel';
import { DataTable } from '@/components/DataTable';
import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getAuditEvents } from '@/lib/api';
import { resolveActiveTenantId } from '@/lib/session';
import type { AuditEvent } from '@/lib/types';

export const dynamic = 'force-dynamic';

export default async function AuditPage() {
  const { tenantId, principal } = await resolveActiveTenantId();
  const auditResult = await getAuditEvents(tenantId, 50);
  const events = auditResult.data.items;
  const candidateEvents = events.filter((event) => event.candidate_id).length;
  const systemEvents = events.filter((event) => event.actor_type === 'system').length;

  return (
    <Shell offline={auditResult.offline || principal.offline} title="Auditoria operacional" subtitle="Trilha de eventos por tenant para diagnosticar workflows, cadencias e acoes automaticas.">
      <section className="stagger grid gap-4 md:grid-cols-3">
        <MetricCard label="Eventos" value={auditResult.data.pagination.total} accent="ink" />
        <MetricCard label="Com candidato" value={candidateEvents} accent="blue" />
        <MetricCard label="Sistema" value={systemEvents} accent="green" />
      </section>

      <ContextPanel tenantId={tenantId} principal={principal.data} offline={auditResult.offline || principal.offline} />

      <DataTable<AuditEvent>
        eyebrow="Audit trail"
        title="Eventos recentes"
        rows={events}
        columns={[
          { key: 'event', label: 'Evento', render: (row) => <StatusBadge value={row.event_type} /> },
          { key: 'candidate', label: 'Candidato', render: (row) => row.candidate_id ?? '-' },
          { key: 'actor', label: 'Ator', render: (row) => `${row.actor_type ?? 'system'} / ${row.actor_id ?? '-'}` },
          { key: 'created', label: 'Criado em', render: (row) => row.created_at ?? '-' },
        ]}
      />
    </Shell>
  );
}
