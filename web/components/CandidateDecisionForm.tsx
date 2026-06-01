'use client';

import { useActionState } from 'react';
import { updateCandidateDecisionAction, type ActionState } from '@/app/actions';
import type { Candidate } from '@/lib/types';

const initialState: ActionState = { ok: false, message: '' };

type CandidateDecisionFormProps = {
  candidate: Candidate;
  tenantId: string;
};

export function CandidateDecisionForm({ candidate, tenantId }: CandidateDecisionFormProps) {
  const [state, action, pending] = useActionState(updateCandidateDecisionAction, initialState);

  return (
    <form action={action} className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
      <input type="hidden" name="tenant_id" value={tenantId} />
      <input type="hidden" name="candidate_id" value={candidate.id} />
      <p className="text-xs font-bold uppercase text-amber-700">Decisão do recrutador</p>
      <h2 className="mt-2 font-display text-2xl font-black text-stone-950">Controlar cadência do candidato</h2>
      <label className="mt-4 grid gap-2 text-sm font-bold text-stone-700">
        Motivo da decisão
        <input
          name="decision_note"
          defaultValue={candidate.manual_decision_note ?? ''}
          placeholder="Ex.: perfil bom, mas aguardar novo momento."
          className="rounded-lg border border-stone-200 bg-white px-4 py-3 font-medium text-stone-950 outline-none transition placeholder:text-stone-400 focus:border-amber-500 focus:ring-4 focus:ring-amber-100"
        />
      </label>
      <div className="mt-4 flex flex-wrap gap-2">
        <button type="submit" name="decision" value="active" disabled={pending} className="rounded-lg bg-stone-950 px-4 py-2 text-sm font-black text-white transition hover:bg-stone-800 disabled:opacity-50">
          Reativar
        </button>
        <button type="submit" name="decision" value="paused" disabled={pending} className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm font-black text-amber-900 transition hover:bg-amber-100 disabled:opacity-50">
          Pausar candidato
        </button>
        <button type="submit" name="decision" value="discarded" disabled={pending} className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-black text-rose-900 transition hover:bg-rose-100 disabled:opacity-50">
          Descartar
        </button>
      </div>
      {state.message ? (
        <p className={`mt-3 rounded-lg border px-3 py-2 text-xs font-bold ${state.ok ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-rose-200 bg-rose-50 text-rose-900'}`}>
          {state.message}
        </p>
      ) : null}
    </form>
  );
}
