import Link from 'next/link';
import { StatusBadge } from '@/components/StatusBadge';
import { formatScore, formatStatus } from '@/lib/format';
import type { Candidate } from '@/lib/types';

type CandidateTalentCardsProps = {
  candidates: Candidate[];
};

function cleanValue(value?: string | null) {
  return value && value.trim().length > 0 ? value : 'Não informado';
}

function locationLabel(candidate: Candidate) {
  return [candidate.city, candidate.state].filter(Boolean).join(' / ') || 'Não informado';
}

function availableChannels(candidate: Candidate) {
  const channels = [
    candidate.email ? 'E-mail' : null,
    candidate.linkedin_url ? 'LinkedIn' : null,
  ].filter(Boolean);
  return channels.length > 0 ? channels : ['Sem canal informado'];
}

function priorityLabel(candidate: Candidate) {
  const score = candidate.score_overall ?? 0;
  const classification = (candidate.classification ?? '').toLowerCase();
  if (classification === 'a' || score >= 80) return 'Alta prioridade';
  if (classification === 'b' || score >= 60) return 'Boa aderência';
  return formatStatus(candidate.classification) === 'Sem informação' ? 'Acompanhar' : formatStatus(candidate.classification);
}

export function CandidateTalentCards({ candidates }: CandidateTalentCardsProps) {
  return (
    <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase text-amber-700">Central de talentos</p>
          <h2 className="mt-2 font-display text-2xl font-black text-stone-950">Candidatos prontos para decisão</h2>
        </div>
        <span className="rounded-full bg-stone-950 px-3 py-1 text-xs font-bold text-stone-50">{candidates.length} candidatos</span>
      </div>

      {candidates.length === 0 ? (
        <div className="mt-5 rounded-lg border border-stone-200 bg-stone-50 p-5 text-sm font-bold text-stone-600">
          Nenhum candidato cadastrado ainda. Envie o primeiro perfil para iniciar a análise dos agentes.
        </div>
      ) : (
        <div className="mt-5 grid gap-4 xl:grid-cols-2">
          {candidates.map((candidate) => (
            <article key={candidate.id} className="rounded-lg border border-stone-200 bg-stone-50 p-4">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <Link href={`/candidates/${candidate.id}`} className="font-display text-2xl font-black text-stone-950 underline decoration-amber-400 decoration-2 underline-offset-4">
                    {candidate.name}
                  </Link>
                  <p className="mt-2 text-sm font-bold text-stone-700">{cleanValue(candidate.current_role)}</p>
                  <p className="mt-1 text-sm font-medium text-stone-500">{cleanValue(candidate.current_company)} · {locationLabel(candidate)}</p>
                </div>
                <StatusBadge value={candidate.classification} label={priorityLabel(candidate)} />
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <div className="rounded-lg bg-white p-4">
                  <p className="text-xs font-bold uppercase text-stone-500">Aderência</p>
                  <p className="mt-2 font-display text-2xl font-black text-stone-950">{formatScore(candidate.score_overall)}</p>
                </div>
                <div className="rounded-lg bg-white p-4">
                  <p className="text-xs font-bold uppercase text-stone-500">Senioridade</p>
                  <p className="mt-2 text-sm font-black text-stone-950">{cleanValue(candidate.seniority)}</p>
                </div>
                <div className="rounded-lg bg-white p-4">
                  <p className="text-xs font-bold uppercase text-stone-500">Canais</p>
                  <p className="mt-2 text-sm font-black text-stone-950">{availableChannels(candidate).join(' + ')}</p>
                </div>
              </div>

              <div className="mt-3 rounded-lg bg-white p-4">
                <p className="text-xs font-bold uppercase text-stone-500">Leitura dos agentes</p>
                <p className="mt-2 text-sm font-medium leading-6 text-stone-700">{cleanValue(candidate.profile_summary ?? candidate.classification_reason)}</p>
              </div>

              <div className="mt-4 flex flex-wrap gap-3">
                <Link href={`/candidates/${candidate.id}`} className="rounded-lg bg-stone-950 px-5 py-3 text-sm font-black text-white transition hover:bg-stone-800">
                  Ver análise
                </Link>
                {candidate.linkedin_url ? (
                  <a href={candidate.linkedin_url} target="_blank" rel="noreferrer" className="rounded-lg border border-stone-200 bg-white px-5 py-3 text-sm font-black text-stone-800 transition hover:bg-stone-50">
                    Abrir LinkedIn
                  </a>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
