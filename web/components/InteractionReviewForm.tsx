'use client';

import { useActionState } from 'react';
import { reviewInteractionMessageAction, type ActionState } from '@/app/actions';
import type { Interaction } from '@/lib/types';

const initialState: ActionState = { ok: false, message: '' };

type InteractionReviewFormProps = {
  interaction: Interaction;
  tenantId: string;
};

export function InteractionReviewForm({ interaction, tenantId }: InteractionReviewFormProps) {
  const [state, action, pending] = useActionState(reviewInteractionMessageAction, initialState);
  const currentMessage = interaction.message_sent ?? '';
  const approved = (interaction.status ?? interaction.interaction_status) === 'approved';

  return (
    <form action={action} className="rounded-lg border border-stone-200 bg-white p-4">
      <input type="hidden" name="tenant_id" value={tenantId} />
      <input type="hidden" name="candidate_id" value={interaction.candidate_id} />
      <input type="hidden" name="interaction_id" value={interaction.id} />
      <p className="text-xs font-bold uppercase text-stone-500">Revisão humana</p>
      <label className="mt-3 grid gap-2 text-sm font-bold text-stone-700">
        Mensagem final
        <textarea
          name="message_sent"
          defaultValue={currentMessage}
          rows={5}
          className="min-h-32 rounded-lg border border-stone-200 bg-white px-4 py-3 text-sm font-medium leading-6 text-stone-950 outline-none transition focus:border-amber-500 focus:ring-4 focus:ring-amber-100"
        />
      </label>
      <label className="mt-3 grid gap-2 text-sm font-bold text-stone-700">
        Observação da decisão
        <input
          name="decision_note"
          placeholder="Ex.: abordagem aprovada para primeiro contato."
          className="rounded-lg border border-stone-200 bg-white px-4 py-3 font-medium text-stone-950 outline-none transition placeholder:text-stone-400 focus:border-amber-500 focus:ring-4 focus:ring-amber-100"
        />
      </label>
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="submit"
          name="status"
          value="approved"
          disabled={pending || approved}
          className="rounded-lg bg-stone-950 px-4 py-2 text-sm font-black text-white transition hover:bg-stone-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {approved ? 'Mensagem aprovada' : pending ? 'Salvando...' : 'Aprovar mensagem'}
        </button>
        <button
          type="submit"
          name="status"
          value="draft"
          disabled={pending}
          className="rounded-lg border border-stone-200 bg-white px-4 py-2 text-sm font-black text-stone-800 transition hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Salvar rascunho
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
