import { ContextPanel } from '@/components/ContextPanel';
import { DataTable } from '@/components/DataTable';
import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getWorkflowRuns } from '@/lib/api';
import { formatDateTime, formatWorkflowName, shortId } from '@/lib/format';
import { resolveActiveTenantId } from '@/lib/session';
import type { WorkflowRun } from '@/lib/types';

export const dynamic = 'force-dynamic';

export default async function WorkflowsPage() {
  const { tenantId, principal, authOptions } = await resolveActiveTenantId();
  const workflowResult = await getWorkflowRuns(tenantId, 50, authOptions);
  const runs = workflowResult.data.items;
  const completed = runs.filter((run) => run.status === 'Completed').length;
  const running = runs.filter((run) => run.status === 'Running').length;

  return (
    <Shell offline={workflowResult.offline || principal.offline} title="Automações de IA" subtitle="Acompanhe as rotinas que analisam candidatos, calculam aderência e preparam contatos por e-mail e LinkedIn.">
      <section className="stagger grid gap-4 md:grid-cols-3">
        <MetricCard label="Automações" value={runs.length} accent="ink" />
        <MetricCard label="Concluídas" value={completed} accent="green" />
        <MetricCard label="Em andamento" value={running} accent="blue" />
      </section>

      <ContextPanel tenantId={tenantId} principal={principal.data} offline={workflowResult.offline || principal.offline} />

      <DataTable<WorkflowRun>
        eyebrow="Processamento"
        title="Atividades recentes"
        rows={runs}
        columns={[
          { key: 'workflow', label: 'Automação', render: (row) => formatWorkflowName(row.workflow_name) },
          { key: 'status', label: 'Situação', render: (row) => <StatusBadge value={row.status} /> },
          { key: 'candidate', label: 'Candidato', render: (row) => row.candidate_id ?? '-' },
          { key: 'workflow_id', label: 'Referência', render: (row) => shortId(row.workflow_id) },
          { key: 'started', label: 'Início', render: (row) => formatDateTime(row.started_at) },
        ]}
      />
    </Shell>
  );
}
