import { ContextPanel } from '@/components/ContextPanel';
import { DataTable } from '@/components/DataTable';
import { MembershipRemoveButton, MembershipUpsertForm } from '@/components/MembershipForms';
import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getMemberships } from '@/lib/api';
import { shortId } from '@/lib/format';
import { resolveActiveTenantId } from '@/lib/session';
import type { TenantMembership } from '@/lib/types';

export const dynamic = 'force-dynamic';

export default async function MembersPage() {
  const { tenantId, principal, authOptions } = await resolveActiveTenantId();
  const membershipsResult = await getMemberships(tenantId, authOptions);
  const memberships = membershipsResult.data;
  const admins = memberships.filter((membership) => ['owner', 'admin'].includes(membership.role)).length;

  return (
    <Shell offline={membershipsResult.offline || principal.offline} title="Equipe e permissões" subtitle="Controle quem pode acessar os dados da empresa e qual nível de permissão cada pessoa possui.">
      <section className="stagger grid gap-4 md:grid-cols-3">
        <MetricCard label="Membros" value={memberships.length} accent="ink" />
        <MetricCard label="Administradores" value={admins} accent="amber" />
        <MetricCard label="Empresa" value={tenantId} accent="blue" />
      </section>

      <ContextPanel tenantId={tenantId} principal={principal.data} offline={membershipsResult.offline || principal.offline} />

      <section className="grid gap-6">
        <MembershipUpsertForm tenantId={tenantId} />
      </section>

      <DataTable<TenantMembership>
        eyebrow="Acesso"
        title="Membros cadastrados"
        rows={memberships}
        columns={[
          { key: 'id', label: 'Referência', render: (row) => shortId(row.id) },
          { key: 'user', label: 'Usuário', render: (row) => shortId(row.user_id) },
          { key: 'email', label: 'E-mail', render: (row) => row.email ?? '-' },
          { key: 'role', label: 'Papel', render: (row) => <StatusBadge value={row.role} /> },
          { key: 'actions', label: 'Ações', render: (row) => <MembershipRemoveButton tenantId={tenantId} membershipId={row.id} label={row.email || row.user_id} /> },
        ]}
      />
    </Shell>
  );
}
