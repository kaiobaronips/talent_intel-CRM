import { ContextPanel } from '@/components/ContextPanel';
import { DataTable } from '@/components/DataTable';
import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getWorkflowRuns } from '@/lib/api';
import { resolveActiveTenantId } from '@/lib/session';
import type { WorkflowRun } from '@/lib/types';

export const dynamic = 'force-dynamic';

export default async function WorkflowsPage() {
  const { tenantId, principal } = await resolveActiveTenantId();
  const workflowResult = await getWorkflowRuns(tenantId, 50);
  const runs = workflowResult.data.items;
  const completed = runs.filter((run) => run.status === 'Completed').length;
  const running = runs.filter((run) => run.status === 'Running').length;

  return (
    <Shell offline={workflowResult.offline || principal.offline} title="Execuções de fluxo" subtitle="Observabilidade dos fluxos Temporal por empresa.">
      <section className="stagger grid gap-4 md:grid-cols-3">
        <MetricCard label="Execuções" value={workflowResult.data.pagination.total} accent="ink" />
        <MetricCard label="Concluídas" value={completed} accent="green" />
        <MetricCard label="Em execução" value={running} accent="blue" />
      </section>

      <ContextPanel tenantId={tenantId} principal={principal.data} offline={workflowResult.offline || principal.offline} />

      <DataTable<WorkflowRun>
        eyebrow="Temporal"
        title="Execuções recentes"
        rows={runs}
        columns={[
          { key: 'workflow', label: 'Fluxo', render: (row) => row.workflow_name },
          { key: 'status', label: 'Status', render: (row) => <StatusBadge value={row.status} /> },
          { key: 'candidate', label: 'Candidato', render: (row) => row.candidate_id ?? '-' },
          { key: 'workflow_id', label: 'ID do fluxo', render: (row) => row.workflow_id },
          { key: 'started', label: 'Início', render: (row) => row.started_at ?? '-' },
        ]}
      />
    </Shell>
  );
}
