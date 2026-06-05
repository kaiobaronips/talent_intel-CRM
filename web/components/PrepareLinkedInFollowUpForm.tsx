'use client';

import { useActionState } from 'react';
import { prepareLinkedInFollowUpAction, type ActionState } from '@/app/actions';
import type { Interaction } from '@/lib/types';

const initialState: ActionState = { ok: false, message: '' };

type PrepareLinkedInFollowUpFormProps = {
  interaction: Interaction;
  tenantId: string;
};

function canPrepareFollowUp(interaction: Interaction) {
  const status = interaction.status ?? interaction.interaction_status;
  return interaction.channel === 'linkedin' && interaction.message_type !== 'follow_up' && status === 'sent';
}

export function PrepareLinkedInFollowUpForm({ interaction, tenantId }: PrepareLinkedInFollowUpFormProps) {
  const [state, action, pending] = useActionState(prepareLinkedInFollowUpAction, initialState);

  if (!canPrepareFollowUp(interaction)) {
    return null;
  }

  return (
    <form action={action} className="grid gap-2">
      <input type="hidden" name="tenant_id" value={tenantId} />
      <input type="hidden" name="candidate_id" value={interaction.candidate_id} />
      <button
        type="submit"
        disabled={pending}
        className="rounded-lg border border-sky-300 bg-sky-50 px-3 py-2 text-xs font-black text-sky-900 transition hover:bg-sky-100 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {pending ? 'Preparando...' : 'Preparar follow-up LinkedIn'}
      </button>
      {state.message ? (
        <p className={`max-w-64 rounded-lg border px-3 py-2 text-xs font-bold ${state.ok ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-rose-200 bg-rose-50 text-rose-900'}`}>
          {state.message}
        </p>
      ) : null}
    </form>
  );
}
