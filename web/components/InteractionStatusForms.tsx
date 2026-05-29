'use client';

import { useActionState } from 'react';
import { updateInteractionStatusAction, type ActionState } from '@/app/actions';
import type { Interaction, InteractionStatus } from '@/lib/types';

const initialState: ActionState = { ok: false, message: '' };

type InteractionStatusFormsProps = {
  interaction: Interaction;
  tenantId: string;
};

function StatusButton({
  interaction,
  tenantId,
  status,
  label,
}: InteractionStatusFormsProps & { status: InteractionStatus; label: string }) {
  const [state, action, pending] = useActionState(updateInteractionStatusAction, initialState);
  const disabled = pending || interaction.status === status || interaction.interaction_status === status;

  return (
    <form action={action} className="grid gap-2">
      <input type="hidden" name="tenant_id" value={tenantId} />
      <input type="hidden" name="candidate_id" value={interaction.candidate_id} />
      <input type="hidden" name="interaction_id" value={interaction.id} />
      <input type="hidden" name="status" value={status} />
      {status === 'replied' ? <input type="hidden" name="response_received" value="Resposta recebida e registrada manualmente." /> : null}
      <button
        type="submit"
        disabled={disabled}
        className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-xs font-black text-stone-700 transition hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {pending ? 'Salvando...' : label}
      </button>
      {state.message ? (
        <p className={`max-w-48 rounded-lg border px-3 py-2 text-xs font-bold ${state.ok ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-rose-200 bg-rose-50 text-rose-900'}`}>
          {state.message}
        </p>
      ) : null}
    </form>
  );
}

export function InteractionStatusForms({ interaction, tenantId }: InteractionStatusFormsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <StatusButton interaction={interaction} tenantId={tenantId} status="sent" label="Marcar enviada" />
      <StatusButton interaction={interaction} tenantId={tenantId} status="replied" label="Registrar resposta" />
    </div>
  );
}
