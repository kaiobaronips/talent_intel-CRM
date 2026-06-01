'use client';

import { useActionState } from 'react';
import { updateTenantPreferencesAction, type ActionState } from '@/app/actions';
import type { Tenant } from '@/lib/types';

const initialState: ActionState = { ok: false, message: '' };

type TenantPreferenceFormsProps = {
  tenant: Tenant;
};

function fieldValue(value: unknown, fallback = '') {
  return typeof value === 'string' ? value : fallback;
}

function numberValue(value: unknown, fallback: number) {
  return typeof value === 'number' ? value : fallback;
}

export function TenantPreferenceForms({ tenant }: TenantPreferenceFormsProps) {
  const [state, action, pending] = useActionState(updateTenantPreferencesAction, initialState);
  const metadata = tenant.metadata_json ?? tenant.metadata ?? {};
  const idealProfile = metadata.ideal_profile ?? {};
  const limits = metadata.mvp_limits ?? {};
  const allowedChannels = Array.isArray(idealProfile.allowed_channels) ? idealProfile.allowed_channels : ['email', 'linkedin'];

  return (
    <form action={action} className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
      <input type="hidden" name="tenant_id" value={tenant.id} />
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase text-amber-700">Preferências da empresa</p>
          <h2 className="mt-2 font-display text-2xl font-black text-stone-950">Perfil ideal e limites do MVP</h2>
          <p className="mt-2 max-w-3xl text-sm font-medium leading-6 text-stone-600">
            Use estes campos para orientar os agentes antes de conectar provedores reais de busca, enriquecimento e envio.
          </p>
        </div>
        <button type="submit" disabled={pending} className="rounded-lg bg-stone-950 px-5 py-3 text-sm font-black text-white transition hover:bg-stone-800 disabled:opacity-50">
          {pending ? 'Salvando...' : 'Salvar preferências'}
        </button>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        <section className="rounded-lg bg-stone-50 p-4">
          <p className="text-xs font-bold uppercase text-stone-500">Perfil ideal</p>
          <div className="mt-4 grid gap-3">
            <label className="grid gap-2 text-sm font-bold text-stone-700">Cargos buscados<input name="target_roles" defaultValue={fieldValue(idealProfile.target_roles)} placeholder="Executivo de contas, SDR, assessor..." className="rounded-lg border border-stone-200 px-4 py-3" /></label>
            <label className="grid gap-2 text-sm font-bold text-stone-700">Senioridade<input name="seniority" defaultValue={fieldValue(idealProfile.seniority)} placeholder="Pleno, senior, liderança" className="rounded-lg border border-stone-200 px-4 py-3" /></label>
            <label className="grid gap-2 text-sm font-bold text-stone-700">Cidades ou regiões<input name="locations" defaultValue={fieldValue(idealProfile.locations)} placeholder="São Paulo, remoto, Sul..." className="rounded-lg border border-stone-200 px-4 py-3" /></label>
            <label className="grid gap-2 text-sm font-bold text-stone-700">Palavras-chave<input name="keywords" defaultValue={fieldValue(idealProfile.keywords)} placeholder="B2B, financeiro, SaaS, hunter..." className="rounded-lg border border-stone-200 px-4 py-3" /></label>
            <label className="grid gap-2 text-sm font-bold text-stone-700">Tom da abordagem<input name="outreach_tone" defaultValue={fieldValue(idealProfile.outreach_tone)} placeholder="Consultivo, curto e direto" className="rounded-lg border border-stone-200 px-4 py-3" /></label>
            <div className="flex flex-wrap gap-3 text-sm font-bold text-stone-700">
              <label className="flex items-center gap-2"><input type="checkbox" name="allowed_email" defaultChecked={allowedChannels.includes('email')} /> Permitir e-mail</label>
              <label className="flex items-center gap-2"><input type="checkbox" name="allowed_linkedin" defaultChecked={allowedChannels.includes('linkedin')} /> Permitir LinkedIn</label>
            </div>
          </div>
        </section>

        <section className="rounded-lg bg-stone-50 p-4">
          <p className="text-xs font-bold uppercase text-stone-500">Limites do MVP</p>
          <div className="mt-4 grid gap-3">
            <label className="grid gap-2 text-sm font-bold text-stone-700">Contatos por dia<input type="number" min="0" name="daily_contact_limit" defaultValue={numberValue(limits.daily_contact_limit, 20)} className="rounded-lg border border-stone-200 px-4 py-3" /></label>
            <label className="grid gap-2 text-sm font-bold text-stone-700">Tentativas por candidato<input type="number" min="0" name="max_attempts_per_candidate" defaultValue={numberValue(limits.max_attempts_per_candidate, 3)} className="rounded-lg border border-stone-200 px-4 py-3" /></label>
            <label className="grid gap-2 text-sm font-bold text-stone-700">Intervalo de follow-up em dias<input type="number" min="0" name="follow_up_interval_days" defaultValue={numberValue(limits.follow_up_interval_days, 5)} className="rounded-lg border border-stone-200 px-4 py-3" /></label>
            <div className="grid gap-3 text-sm font-bold text-stone-700">
              <label className="flex items-center gap-2"><input type="checkbox" name="require_manual_approval" defaultChecked={limits.require_manual_approval !== false} /> Exigir aprovação manual antes de enviar</label>
              <label className="flex items-center gap-2"><input type="checkbox" name="email_enabled" defaultChecked={limits.email_enabled !== false} /> E-mail habilitado</label>
              <label className="flex items-center gap-2"><input type="checkbox" name="linkedin_enabled" defaultChecked={limits.linkedin_enabled !== false} /> LinkedIn habilitado</label>
            </div>
          </div>
        </section>
      </div>

      {state.message ? (
        <p className={`mt-4 rounded-lg border px-3 py-2 text-sm font-bold ${state.ok ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-rose-200 bg-rose-50 text-rose-900'}`}>
          {state.message}
        </p>
      ) : null}
    </form>
  );
}
