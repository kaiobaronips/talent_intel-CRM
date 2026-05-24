'use client';

import { useActionState } from 'react';
import { deleteMembershipAction, upsertMembershipAction, type ActionState } from '@/app/actions';

const initialState: ActionState = { ok: false, message: '' };

function Feedback({ state }: { state: ActionState }) {
  if (!state.message) return null;
  return <p className={`rounded-2xl border px-4 py-3 text-sm font-bold ${state.ok ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-rose-200 bg-rose-50 text-rose-900'}`}>{state.message}</p>;
}

export function MembershipUpsertForm({ tenantId }: { tenantId: string }) {
  const [state, action] = useActionState(upsertMembershipAction, initialState);

  return (
    <form action={action} className="rounded-[2rem] border border-stone-200 bg-white/82 p-5 shadow-[0_24px_70px_rgba(41,37,36,0.08)] backdrop-blur">
      <input type="hidden" name="tenant_id" value={tenantId} />
      <p className="text-xs font-bold uppercase tracking-[0.24em] text-amber-700">Acesso</p>
      <h2 className="mt-2 font-display text-2xl font-black tracking-[-0.04em]">Adicionar membro</h2>
      <div className="mt-5 grid gap-4 md:grid-cols-4 md:items-end">
        <label className="grid gap-2 text-sm font-bold text-stone-700">
          E-mail
          <input name="email" type="email" required placeholder="user@empresa.com" className="rounded-2xl border border-stone-200 bg-white px-4 py-3 font-medium outline-none focus:border-amber-500 focus:ring-4 focus:ring-amber-100" />
        </label>
        <label className="grid gap-2 text-sm font-bold text-stone-700">
          ID do usuário
          <input name="user_id" placeholder="opcional" className="rounded-2xl border border-stone-200 bg-white px-4 py-3 font-medium outline-none focus:border-amber-500 focus:ring-4 focus:ring-amber-100" />
        </label>
        <label className="grid gap-2 text-sm font-bold text-stone-700">
          Papel
          <select name="role" defaultValue="viewer" className="rounded-2xl border border-stone-200 bg-white px-4 py-3 font-medium outline-none focus:border-amber-500 focus:ring-4 focus:ring-amber-100">
            <option value="owner">proprietário</option>
            <option value="admin">administrador</option>
            <option value="recruiter">recrutador</option>
            <option value="viewer">leitor</option>
          </select>
        </label>
        <button type="submit" className="rounded-full bg-stone-950 px-5 py-3 text-sm font-black text-stone-50 transition hover:bg-amber-700">Salvar membro</button>
      </div>
      <div className="mt-4"><Feedback state={state} /></div>
    </form>
  );
}

export function MembershipRemoveButton({ tenantId, membershipId, label }: { tenantId: string; membershipId: string; label: string }) {
  const [state, action, pending] = useActionState(deleteMembershipAction, initialState);

  return (
    <form action={action} className="grid min-w-28 gap-2">
      <input type="hidden" name="tenant_id" value={tenantId} />
      <input type="hidden" name="membership_id" value={membershipId} />
      <button
        type="submit"
        disabled={pending}
        aria-label={`Remover ${label}`}
        className="rounded-full border border-rose-200 bg-white px-3 py-2 text-xs font-black text-rose-700 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {pending ? 'Removendo...' : 'Remover'}
      </button>
      {state.message ? <Feedback state={state} /> : null}
    </form>
  );
}
