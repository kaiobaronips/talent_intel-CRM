import Link from 'next/link';
import { InteractionReviewForm } from '@/components/InteractionReviewForm';
import { InteractionStatusForms } from '@/components/InteractionStatusForms';
import { PrepareEmailFollowUpForm } from '@/components/PrepareEmailFollowUpForm';
import { StatusBadge } from '@/components/StatusBadge';
import { formatDateTime } from '@/lib/format';
import type { Interaction } from '@/lib/types';

type InteractionContactCardsProps = {
  interactions: Interaction[];
  tenantId: string;
  showCandidateLink?: boolean;
};

function channelLabel(channel: string) {
  return channel === 'linkedin' ? 'LinkedIn' : channel === 'email' ? 'E-mail' : channel;
}

function cleanValue(value?: string | null) {
  return value && value.trim().length > 0 ? value : 'Não informado';
}

function messageTypeLabel(value?: string | null) {
  if (value === 'initial') return 'Contato inicial';
  if (value === 'follow_up') return 'Follow-up';
  return cleanValue(value);
}

function cadenceLabel(value?: string | null) {
  if (value === 'follow_up_1') return 'Follow-up 1';
  if (value === 'follow_up_2') return 'Follow-up 2';
  if (value === 'follow_up_3') return 'Follow-up 3 - despedida';
  return '';
}

export function InteractionContactCards({ interactions, tenantId, showCandidateLink = false }: InteractionContactCardsProps) {
  return (
    <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase text-amber-700">Plano de abordagem</p>
          <h2 className="mt-2 font-display text-2xl font-black text-stone-950">Contatos que precisam de ação</h2>
        </div>
        <span className="rounded-full bg-stone-950 px-3 py-1 text-xs font-bold text-stone-50">{interactions.length} contatos</span>
      </div>

      {interactions.length === 0 ? (
        <div className="mt-5 rounded-lg border border-stone-200 bg-stone-50 p-5 text-sm font-bold text-stone-600">
          Nenhum contato preparado para acompanhamento.
        </div>
      ) : (
        <div className="mt-5 grid gap-4 xl:grid-cols-2">
          {interactions.map((interaction) => (
            <article key={interaction.id} className="rounded-lg border border-stone-200 bg-stone-50 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge value={interaction.channel} label={channelLabel(interaction.channel)} />
                    <StatusBadge value={interaction.status ?? interaction.interaction_status} />
                  </div>
                  {showCandidateLink ? (
                    <Link href={`/candidates/${interaction.candidate_id}`} className="mt-3 block font-black text-stone-950 underline decoration-amber-400 decoration-2 underline-offset-4">
                      {interaction.candidate_name ?? interaction.candidate_id}
                    </Link>
                  ) : null}
                </div>
                <p className="text-right text-xs font-bold text-stone-500">{formatDateTime(interaction.created_at)}</p>
              </div>

              <div className="mt-4 grid gap-3">
                <div className="rounded-lg bg-white p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-xs font-bold uppercase text-stone-500">Mensagem preparada</p>
                    <span className="rounded-full bg-stone-100 px-2 py-1 text-[11px] font-black text-stone-600">
                      {cadenceLabel(interaction.cadence_step) || messageTypeLabel(interaction.message_type)}
                    </span>
                  </div>
                  {interaction.email_subject ? <p className="mt-2 text-sm font-black text-stone-950">{interaction.email_subject}</p> : null}
                  <p className="mt-2 text-sm font-medium leading-6 text-stone-700">{cleanValue(interaction.message_sent)}</p>
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  <div className="rounded-lg bg-white p-4">
                    <p className="text-xs font-bold uppercase text-stone-500">Próxima ação</p>
                    <p className="mt-2 text-sm font-bold text-stone-950">{cleanValue(interaction.next_action)}</p>
                  </div>
                  <div className="rounded-lg bg-white p-4">
                    <p className="text-xs font-bold uppercase text-stone-500">Destino</p>
                    <p className="mt-2 break-words text-sm font-bold text-stone-950">{cleanValue(interaction.email_sent_to ?? (interaction.payload_json?.email as string | undefined))}</p>
                  </div>
                  <div className="rounded-lg bg-white p-4">
                    <p className="text-xs font-bold uppercase text-stone-500">Resposta</p>
                    <p className="mt-2 text-sm font-bold text-stone-950">{cleanValue(interaction.response_received)}</p>
                  </div>
                </div>
                {interaction.provider_message_id ? (
                  <div className="rounded-lg bg-emerald-50 p-4">
                    <p className="text-xs font-bold uppercase text-emerald-700">Envio confirmado</p>
                    <p className="mt-2 break-all text-sm font-bold text-emerald-950">Resend ID: {interaction.provider_message_id}</p>
                  </div>
                ) : null}
              </div>

              <div className="mt-4 border-t border-stone-200 pt-4">
                <InteractionReviewForm interaction={interaction} tenantId={tenantId} />
              </div>

              <div className="mt-3 flex flex-wrap gap-2 border-t border-stone-200 pt-4">
                <InteractionStatusForms interaction={interaction} tenantId={tenantId} />
                <PrepareEmailFollowUpForm interaction={interaction} tenantId={tenantId} />
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
