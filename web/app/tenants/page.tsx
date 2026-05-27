import Link from 'next/link';
import { DataTable } from '@/components/DataTable';
import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getTenants } from '@/lib/api';
import { formatDateTime } from '@/lib/format';
import { requireAuthenticatedPrincipal, getSessionToken } from '@/lib/session';
import type { Tenant } from '@/lib/types';

export const dynamic = 'force-dynamic';

export default async function TenantsPage() {
  await requireAuthenticatedPrincipal();
  const token = await getSessionToken();
  const tenantsResult = await getTenants(50, token ? { bearerToken: token, apiKeyFallback: false } : { apiKeyFallback: false });
  const tenants = tenantsResult.data.items;
  const scale = tenants.filter((tenant) => tenant.tier === 'scale').length;
  const growth = tenants.filter((tenant) => tenant.tier === 'growth').length;

  return (
    <Shell offline={tenantsResult.offline} title="Empresas clientes" subtitle="Gerencie as empresas que usam a plataforma e acesse o painel de cada operação.">
      <section className="stagger grid gap-4 md:grid-cols-3">
        <MetricCard label="Empresas" value={tenants.length} accent="ink" />
        <MetricCard label="Escala" value={scale} accent="blue" />
        <MetricCard label="Crescimento" value={growth} accent="green" />
      </section>

      <DataTable<Tenant>
        eyebrow="Clientes"
        title="Empresas cadastradas"
        rows={tenants}
        columns={[
          { key: 'company', label: 'Empresa', render: (row) => <Link href={`/tenants/${row.id}`} className="font-black text-stone-950 underline decoration-amber-400 decoration-2 underline-offset-4">{row.company_name}</Link> },
          { key: 'id', label: 'Código da empresa', render: (row) => row.id },
          { key: 'tier', label: 'Plano', render: (row) => <StatusBadge value={row.tier} /> },
          { key: 'timezone', label: 'Fuso horário', render: (row) => row.timezone ?? '-' },
          { key: 'created', label: 'Criado em', render: (row) => formatDateTime(row.created_at) },
        ]}
      />
    </Shell>
  );
}
