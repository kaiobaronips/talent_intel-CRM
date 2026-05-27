import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { requireAuthenticatedPrincipal } from '@/lib/session';
import { getHealthStatus, getReadinessStatus } from '@/lib/system';

export const dynamic = 'force-dynamic';

export default async function SystemPage() {
  await requireAuthenticatedPrincipal();
  const [healthResult, readinessResult] = await Promise.all([getHealthStatus(), getReadinessStatus()]);
  const offline = healthResult.offline || readinessResult.offline;
  const health = healthResult.data;
  const readiness = readinessResult.data;

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
    </Shell>
  );
}
