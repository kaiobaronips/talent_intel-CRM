import { StatusBadge } from './StatusBadge';
import type { Principal } from '@/lib/session';

type ContextPanelProps = {
  tenantId: string;
  principal: Principal;
  offline?: boolean;
};

export function ContextPanel({ tenantId, principal, offline = false }: ContextPanelProps) {
  return (
    <section className="rounded-[2rem] border border-stone-200 bg-white/82 p-5 shadow-[0_24px_70px_rgba(41,37,36,0.08)] backdrop-blur">
      <p className="text-xs font-bold uppercase tracking-[0.24em] text-amber-700">Contexto de acesso</p>
      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <div className="rounded-2xl bg-stone-50 p-4">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-stone-500">Tenant ativo</p>
          <p className="mt-2 break-all font-monoish text-sm font-black text-stone-950">{tenantId}</p>
        </div>
        <div className="rounded-2xl bg-stone-50 p-4">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-stone-500">Role</p>
          <div className="mt-2"><StatusBadge value={principal.role} /></div>
        </div>
        <div className="rounded-2xl bg-stone-50 p-4">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-stone-500">API key scope</p>
          <p className="mt-2 font-bold text-stone-950">{principal.is_admin ? 'admin global' : 'tenant scoped'}</p>
        </div>
        <div className="rounded-2xl bg-stone-50 p-4">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-stone-500">Modo</p>
          <div className="mt-2"><StatusBadge value={offline ? 'erro' : 'active'} label={offline ? 'Fallback' : 'Real'} /></div>
        </div>
      </div>
    </section>
  );
}
