import { ContextPanel } from '@/components/ContextPanel';
import { DataTable } from '@/components/DataTable';
import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getAuditEvents } from '@/lib/api';
import { formatDateTime, formatEventName, shortId } from '@/lib/format';
import { resolveActiveTenantId } from '@/lib/session';
import type { AuditEvent } from '@/lib/types';

export const dynamic = 'force-dynamic';

export default async function AuditPage() {
  const { tenantId, principal, authOptions } = await resolveActiveTenantId();
  const auditResult = await getAuditEvents(tenantId, 50, authOptions);
  const events = auditResult.data.items;
  const candidateEvents = events.filter((event) => event.candidate_id).length;
  const systemEvents = events.filter((event) => event.actor_type === 'system').length;

  return (
    <Shell offline={auditResult.offline || principal.offline} title="Histórico de atividades" subtitle="Registro das principais ações realizadas pela plataforma, pelos agentes de IA e pelos usuários da empresa.">
      <section className="stagger grid gap-4 md:grid-cols-3">
        <MetricCard label="Eventos" value={auditResult.data.pagination.total} accent="ink" />
        <MetricCard label="Com candidato" value={candidateEvents} accent="blue" />
        <MetricCard label="Sistema" value={systemEvents} accent="green" />
      </section>

      <ContextPanel tenantId={tenantId} principal={principal.data} offline={auditResult.offline || principal.offline} />

      <DataTable<AuditEvent>
        eyebrow="Trilha de auditoria"
        title="Eventos recentes"
        rows={events}
        columns={[
          { key: 'event', label: 'Evento', render: (row) => <StatusBadge value={row.event_type} label={formatEventName(row.event_type)} /> },
          { key: 'candidate', label: 'Candidato', render: (row) => row.candidate_id ?? '-' },
          { key: 'actor', label: 'Origem', render: (row) => row.actor_type === 'system' ? 'Automação da plataforma' : shortId(row.actor_id ?? row.actor_type) },
          { key: 'created', label: 'Data', render: (row) => formatDateTime(row.created_at) },
        ]}
      />
    </Shell>
  );
}
