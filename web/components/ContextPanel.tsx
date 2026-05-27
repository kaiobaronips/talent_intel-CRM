import { StatusBadge } from './StatusBadge';
import type { Principal } from '@/lib/session';

type ContextPanelProps = {
  tenantId: string;
  principal: Principal;
  offline?: boolean;
};

export function ContextPanel({ tenantId, principal, offline = false }: ContextPanelProps) {
  return (
    <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-bold uppercase text-amber-700">Acesso atual</p>
      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <div className="rounded-lg bg-stone-50 p-4">
          <p className="text-xs font-bold uppercase text-stone-500">Empresa em análise</p>
          <p className="mt-2 break-all font-monoish text-sm font-black text-stone-950">{tenantId}</p>
        </div>
        <div className="rounded-lg bg-stone-50 p-4">
          <p className="text-xs font-bold uppercase text-stone-500">Permissão</p>
          <div className="mt-2"><StatusBadge value={principal.role} /></div>
        </div>
        <div className="rounded-lg bg-stone-50 p-4">
          <p className="text-xs font-bold uppercase text-stone-500">Área liberada</p>
          <p className="mt-2 font-bold text-stone-950">{principal.is_admin ? 'Todas as empresas' : 'Somente esta empresa'}</p>
        </div>
        <div className="rounded-lg bg-stone-50 p-4">
          <p className="text-xs font-bold uppercase text-stone-500">Fonte dos dados</p>
          <div className="mt-2"><StatusBadge value={offline ? 'erro' : 'active'} label={offline ? 'Dados de apoio' : 'Produção'} /></div>
        </div>
      </div>
    </section>
  );
}
