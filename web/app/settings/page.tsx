import { ConnectorStackPanel } from '@/components/ConnectorStackPanel';
import { Shell } from '@/components/Shell';
import { TenantMessageTemplateForm } from '@/components/TenantMessageTemplateForm';
import { TenantPreferenceForms } from '@/components/TenantPreferenceForms';
import { getTenant } from '@/lib/api';
import { resolveActiveTenantId } from '@/lib/session';

export const dynamic = 'force-dynamic';

export default async function SettingsPage() {
  const { tenantId, authOptions } = await resolveActiveTenantId();
  const tenantResult = await getTenant(tenantId, authOptions);
  const tenant = tenantResult.data;

  return (
    <Shell
      offline={tenantResult.offline}
      title="Configurações operacionais"
      subtitle="Configure a stack de conectores, o perfil ideal, os limites do MVP e as mensagens base que serão usadas nas automações."
    >
      <ConnectorStackPanel />
      <TenantPreferenceForms tenant={tenant} />
      <TenantMessageTemplateForm tenant={tenant} />
    </Shell>
  );
}
