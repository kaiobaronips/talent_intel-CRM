import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { resolveActiveTenantId } from '@/lib/session';
import { getConnectorStatus, getHealthStatus, getReadinessStatus } from '@/lib/system';

export const dynamic = 'force-dynamic';

export default async function SystemPage() {
  const { tenantId, authOptions } = await resolveActiveTenantId();
  const [healthResult, readinessResult, connectorResult] = await Promise.all([getHealthStatus(), getReadinessStatus(), getConnectorStatus(tenantId, authOptions)]);
  const offline = healthResult.offline || readinessResult.offline || connectorResult.offline;
  const health = healthResult.data;
  const readiness = readinessResult.data;
  const connectors = connectorResult.data.items;

  return (
    <Shell
      offline={offline}
      title="Saúde do sistema"
      subtitle="Confirme se os serviços principais estão disponíveis para cadastrar candidatos e executar as automações de IA."
    >
      <section className="stagger grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Aplicação" value={offline ? 'offline' : 'online'} detail={health.service ?? 'serviço'} accent={offline ? 'amber' : 'green'} />
        <MetricCard label="Banco de dados" value={readiness.postgres ? 'pronto' : 'não pronto'} detail="Supabase" accent={readiness.postgres ? 'green' : 'amber'} />
        <MetricCard label="Automações" value={health.temporal_namespace ? 'ativas' : 'verificar'} detail="orquestrador" accent="blue" />
        <MetricCard label="Destino dos fluxos" value={health.temporal_target_host ?? 'desconhecido'} accent="ink" />
      </section>

      <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
        <p className="text-xs font-bold uppercase text-amber-700">Critérios</p>
        <h2 className="mt-2 font-display text-2xl font-black">Critérios para operar</h2>
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <div className="rounded-lg bg-stone-50 p-4">
            <p className="font-bold text-stone-950">Aplicação acessível</p>
            <div className="mt-2"><StatusBadge value={offline ? 'erro' : 'active'} label={offline ? 'Falhou' : 'OK'} /></div>
          </div>
          <div className="rounded-lg bg-stone-50 p-4">
            <p className="font-bold text-stone-950">Banco pronto</p>
            <div className="mt-2"><StatusBadge value={readiness.postgres ? 'active' : 'erro'} label={readiness.postgres ? 'OK' : 'Falhou'} /></div>
          </div>
          <div className="rounded-lg bg-stone-50 p-4">
            <p className="font-bold text-stone-950">Automações configuradas</p>
            <div className="mt-2"><StatusBadge value={health.temporal_target_host && health.temporal_target_host !== 'unknown' ? 'active' : 'erro'} label={health.temporal_target_host && health.temporal_target_host !== 'unknown' ? 'OK' : 'Falhou'} /></div>
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase text-amber-700">Conectores</p>
            <h2 className="mt-2 font-display text-2xl font-black">Status operacional dos conectores</h2>
            <p className="mt-2 max-w-3xl text-sm font-medium leading-6 text-stone-600">
              Veja quais integrações estão prontas, quais precisam de atenção e qual é o próximo passo operacional.
            </p>
          </div>
          <StatusBadge value={connectorResult.offline ? 'offline' : 'active'} label={connectorResult.offline ? 'Falhou' : 'Atualizado'} />
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-2">
          {connectors.map((connector) => (
            <article key={connector.key} className="rounded-lg border border-stone-200 bg-stone-50 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-display text-xl font-black text-stone-950">{connector.name}</h3>
                  <p className="mt-1 text-sm font-medium leading-6 text-stone-600">{connector.summary}</p>
                </div>
                <StatusBadge value={connector.status} />
              </div>
              <dl className="mt-4 grid gap-3">
                <div>
                  <dt className="text-xs font-bold uppercase tracking-[0.18em] text-stone-500">Último resultado</dt>
                  <dd className="mt-1 text-sm font-bold text-stone-950">{connector.last_result}</dd>
                </div>
                <div>
                  <dt className="text-xs font-bold uppercase tracking-[0.18em] text-stone-500">Próxima ação</dt>
                  <dd className="mt-1 text-sm font-medium leading-6 text-stone-700">{connector.next_action}</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      </section>
    </Shell>
  );
}
