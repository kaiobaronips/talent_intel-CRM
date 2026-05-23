import { MetricCard } from '@/components/MetricCard';
import { Shell } from '@/components/Shell';
import { StatusBadge } from '@/components/StatusBadge';
import { getHealthStatus, getReadinessStatus } from '@/lib/system';

export const dynamic = 'force-dynamic';

export default async function SystemPage() {
  const [healthResult, readinessResult] = await Promise.all([getHealthStatus(), getReadinessStatus()]);
  const offline = healthResult.offline || readinessResult.offline;
  const health = healthResult.data;
  const readiness = readinessResult.data;

  return (
    <Shell
      offline={offline}
      title="System Readiness"
      subtitle="Painel tecnico para validar API, Postgres/Supabase e alvo Temporal antes de operar cadencias reais."
    >
      <section className="stagger grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="API" value={offline ? 'offline' : 'online'} detail={health.service ?? 'service'} accent={offline ? 'amber' : 'green'} />
        <MetricCard label="Postgres" value={readiness.postgres ? 'ready' : 'not ready'} detail="/ready" accent={readiness.postgres ? 'green' : 'amber'} />
        <MetricCard label="Temporal namespace" value={health.temporal_namespace ?? 'unknown'} accent="blue" />
        <MetricCard label="Temporal host" value={health.temporal_target_host ?? 'unknown'} accent="ink" />
      </section>

      <section className="rounded-[2rem] border border-stone-200 bg-white/82 p-5 shadow-[0_24px_70px_rgba(41,37,36,0.08)] backdrop-blur">
        <p className="text-xs font-bold uppercase tracking-[0.24em] text-amber-700">Gates</p>
        <h2 className="mt-2 font-display text-2xl font-black tracking-[-0.04em]">Criterios para operar</h2>
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl bg-stone-50 p-4">
            <p className="font-bold text-stone-950">API acessivel</p>
            <div className="mt-2"><StatusBadge value={offline ? 'erro' : 'active'} label={offline ? 'Falhou' : 'OK'} /></div>
          </div>
          <div className="rounded-2xl bg-stone-50 p-4">
            <p className="font-bold text-stone-950">Banco pronto</p>
            <div className="mt-2"><StatusBadge value={readiness.postgres ? 'active' : 'erro'} label={readiness.postgres ? 'OK' : 'Falhou'} /></div>
          </div>
          <div className="rounded-2xl bg-stone-50 p-4">
            <p className="font-bold text-stone-950">Temporal configurado</p>
            <div className="mt-2"><StatusBadge value={health.temporal_target_host && health.temporal_target_host !== 'unknown' ? 'active' : 'erro'} label={health.temporal_target_host && health.temporal_target_host !== 'unknown' ? 'OK' : 'Falhou'} /></div>
          </div>
        </div>
      </section>
    </Shell>
  );
}
