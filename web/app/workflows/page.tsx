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
    <Shell offline={workflowResult.offline || principal.offline} title="Workflow runs" subtitle="Observabilidade dos workflows Temporal por tenant.">
      <section className="stagger grid gap-4 md:grid-cols-3">
        <MetricCard label="Runs" value={workflowResult.data.pagination.total} accent="ink" />
        <MetricCard label="Completed" value={completed} accent="green" />
        <MetricCard label="Running" value={running} accent="blue" />
      </section>

      <ContextPanel tenantId={tenantId} principal={principal.data} offline={workflowResult.offline || principal.offline} />

      <DataTable<WorkflowRun>
        eyebrow="Temporal"
        title="Execucoes recentes"
        rows={runs}
        columns={[
          { key: 'workflow', label: 'Workflow', render: (row) => row.workflow_name },
          { key: 'status', label: 'Status', render: (row) => <StatusBadge value={row.status} /> },
          { key: 'candidate', label: 'Candidato', render: (row) => row.candidate_id ?? '-' },
          { key: 'workflow_id', label: 'Workflow ID', render: (row) => row.workflow_id },
          { key: 'started', label: 'Inicio', render: (row) => row.started_at ?? '-' },
        ]}
      />
    </Shell>
  );
}
