import { ContextPanel } from '@/components/ContextPanel';
import { DataTable } from '@/components/DataTable';
import { MembershipDeleteForm, MembershipUpsertForm } from '@/components/MembershipForms';
import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getMemberships } from '@/lib/api';
import { resolveActiveTenantId } from '@/lib/session';
import type { TenantMembership } from '@/lib/types';

export const dynamic = 'force-dynamic';

export default async function MembersPage() {
  const { tenantId, principal } = await resolveActiveTenantId();
  const membershipsResult = await getMemberships(tenantId);
  const memberships = membershipsResult.data;
  const admins = memberships.filter((membership) => ['owner', 'admin'].includes(membership.role)).length;

  return (
    <Shell offline={membershipsResult.offline || principal.offline} title="Membros da empresa" subtitle="Controle inicial de acesso SaaS por empresa. O login humano será conectado a estas associações.">
      <section className="stagger grid gap-4 md:grid-cols-3">
        <MetricCard label="Membros" value={memberships.length} accent="ink" />
        <MetricCard label="Administradores" value={admins} accent="amber" />
        <MetricCard label="Empresa" value={tenantId} accent="blue" />
      </section>

      <ContextPanel tenantId={tenantId} principal={principal.data} offline={membershipsResult.offline || principal.offline} />

      <section className="grid gap-6 xl:grid-cols-2">
        <MembershipUpsertForm tenantId={tenantId} />
        <MembershipDeleteForm tenantId={tenantId} />
      </section>

      <DataTable<TenantMembership>
        eyebrow="Acesso"
        title="Membros cadastrados"
        rows={memberships}
        columns={[
          { key: 'id', label: 'ID', render: (row) => row.id },
          { key: 'user', label: 'ID do usuário', render: (row) => row.user_id },
          { key: 'email', label: 'E-mail', render: (row) => row.email ?? '-' },
          { key: 'role', label: 'Papel', render: (row) => <StatusBadge value={row.role} /> },
        ]}
      />
    </Shell>
  );
}
