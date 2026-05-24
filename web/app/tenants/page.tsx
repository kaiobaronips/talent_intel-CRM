import Link from 'next/link';
import { DataTable } from '@/components/DataTable';
import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getTenants } from '@/lib/api';
import { requireAuthenticatedPrincipal, getSessionToken } from '@/lib/session';
import type { Tenant } from '@/lib/types';

export const dynamic = 'force-dynamic';

export default async function TenantsPage() {
  await requireAuthenticatedPrincipal();
  const token = await getSessionToken();
  const tenantsResult = await getTenants(50, token ? { bearerToken: token } : {});
  const tenants = tenantsResult.data.items;
  const scale = tenants.filter((tenant) => tenant.tier === 'scale').length;
  const growth = tenants.filter((tenant) => tenant.tier === 'growth').length;

  return (
    <Shell offline={tenantsResult.offline} title="Empresas" subtitle="Administração multiempresa do Talent Intel CRM.">
      <section className="stagger grid gap-4 md:grid-cols-3">
        <MetricCard label="Total" value={tenantsResult.data.pagination.total} accent="ink" />
        <MetricCard label="Escala" value={scale} accent="blue" />
        <MetricCard label="Crescimento" value={growth} accent="green" />
      </section>

      <DataTable<Tenant>
        eyebrow="SaaS"
        title="Empresas cadastradas"
        rows={tenants}
        columns={[
          { key: 'company', label: 'Empresa', render: (row) => <Link href={`/tenants/${row.id}`} className="font-black text-stone-950 underline decoration-amber-400 decoration-2 underline-offset-4">{row.company_name}</Link> },
          { key: 'id', label: 'ID da empresa', render: (row) => row.id },
          { key: 'tier', label: 'Plano', render: (row) => <StatusBadge value={row.tier} /> },
          { key: 'timezone', label: 'Fuso horário', render: (row) => row.timezone ?? '-' },
          { key: 'created', label: 'Criado em', render: (row) => row.created_at ?? '-' },
        ]}
      />
    </Shell>
  );
}
