import clsx from 'clsx';
import { formatStatus } from '@/lib/format';
import type { Candidate, Interaction } from '@/lib/types';

type CandidateJourneyProps = {
  candidate: Candidate;
  interactions: Interaction[];
};

function statusOf(interaction: Interaction) {
  return (interaction.status ?? interaction.interaction_status ?? 'pending').toLowerCase();
}

function hasStatus(interactions: Interaction[], statuses: string[]) {
  return interactions.some((interaction) => statuses.includes(statusOf(interaction)));
}

export function CandidateJourney({ candidate, interactions }: CandidateJourneyProps) {
  const hasPreparedContact = interactions.length > 0;
  const hasSentContact = hasStatus(interactions, ['sent', 'replied', 'closed']);
  const hasReply = hasStatus(interactions, ['replied', 'closed']);
  const hasAgentScore = candidate.score_overall !== null && candidate.score_overall !== undefined;
  const currentStage = hasReply ? 4 : hasSentContact ? 3 : hasPreparedContact ? 2 : hasAgentScore ? 1 : 0;

  const steps = [
    {
      title: 'Candidato identificado',
      description: 'O perfil entrou na base da empresa e ficou disponível para avaliação.',
    },
    {
      title: 'Avaliado pelos agentes',
      description: `Aderência: ${candidate.score_overall ?? 'sem nota'} de 100. Prioridade: ${formatStatus(candidate.classification)}.`,
    },
    {
      title: 'Mensagens preparadas',
      description: hasPreparedContact ? `${interactions.length} contato(s) pronto(s) para abordagem.` : 'Ainda não há mensagens preparadas para este candidato.',
    },
    {
      title: 'Contato enviado',
      description: hasSentContact ? 'Ao menos uma abordagem já foi marcada como enviada.' : 'Marque o contato como enviado depois de acionar o candidato.',
    },
    {
      title: 'Resposta acompanhada',
      description: hasReply ? 'Existe resposta registrada para orientar a próxima ação.' : 'Quando houver retorno, registre a resposta no contato correspondente.',
    },
  ];

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase text-amber-700">Jornada do candidato</p>
          <h2 className="mt-2 font-display text-2xl font-black text-stone-950">Próximo passo claro para o time</h2>
        </div>
        <span className="rounded-full border border-stone-200 bg-stone-50 px-3 py-1 text-xs font-black text-stone-700">
          Etapa {Math.min(currentStage + 1, steps.length)} de {steps.length}
        </span>
      </div>

      <div className="mt-6 grid gap-3 lg:grid-cols-5">
        {steps.map((step, index) => {
          const state = index < currentStage ? 'done' : index === currentStage ? 'current' : 'waiting';
          return (
            <article
              key={step.title}
              className={clsx(
                'rounded-lg border p-4',
                state === 'done' && 'border-emerald-200 bg-emerald-50',
                state === 'current' && 'border-amber-300 bg-amber-50',
                state === 'waiting' && 'border-stone-200 bg-stone-50',
              )}
            >
              <div className="flex items-center gap-3">
                <span
                  className={clsx(
                    'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-black',
                    state === 'done' && 'bg-emerald-600 text-white',
                    state === 'current' && 'bg-amber-500 text-stone-950',
                    state === 'waiting' && 'bg-white text-stone-500',
                  )}
                >
                  {index + 1}
                </span>
                <h3 className="text-sm font-black text-stone-950">{step.title}</h3>
              </div>
              <p className="mt-3 text-sm font-medium leading-6 text-stone-600">{step.description}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
