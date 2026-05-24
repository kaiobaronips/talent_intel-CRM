'use client';

import { useActionState } from 'react';
import type { ActionState } from '@/app/actions';
import { createApiKeyAction, createCandidateAction, createTenantAction, revokeApiKeyAction, rotateApiKeyAction } from '@/app/actions';

const initialState: ActionState = { ok: false, message: '' };

function SubmitButton({ children }: { children: React.ReactNode }) {
  return (
    <button type="submit" className="rounded-full bg-stone-950 px-5 py-3 text-sm font-black text-stone-50 transition hover:-translate-y-0.5 hover:bg-amber-700">
      {children}
    </button>
  );
}

function Field({ label, name, placeholder, type = 'text', required = false, defaultValue }: { label: string; name: string; placeholder?: string; type?: string; required?: boolean; defaultValue?: string }) {
  return (
    <label className="grid gap-2 text-sm font-bold text-stone-700">
      {label}
      <input
        name={name}
        type={type}
        required={required}
        defaultValue={defaultValue}
        placeholder={placeholder}
        className="rounded-2xl border border-stone-200 bg-white px-4 py-3 font-medium text-stone-950 outline-none transition placeholder:text-stone-400 focus:border-amber-500 focus:ring-4 focus:ring-amber-100"
      />
    </label>
  );
}

function ActionFeedback({ state }: { state: ActionState }) {
  if (!state.message) {
    return null;
  }

  return (
    <div className={`rounded-2xl border p-4 text-sm font-bold ${state.ok ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-rose-200 bg-rose-50 text-rose-900'}`}>
      <p>{state.message}</p>
      {state.secret ? <code className="mt-3 block overflow-x-auto rounded-xl bg-stone-950 p-3 font-monoish text-xs text-stone-50">{state.secret}</code> : null}
    </div>
  );
}

export function TenantCreateForm() {
  const [state, action] = useActionState(createTenantAction, initialState);

  return (
    <form action={action} className="rounded-[2rem] border border-stone-200 bg-white/82 p-5 shadow-[0_24px_70px_rgba(41,37,36,0.08)] backdrop-blur">
      <p className="text-xs font-bold uppercase tracking-[0.24em] text-amber-700">Administração</p>
      <h2 className="mt-2 font-display text-2xl font-black tracking-[-0.04em]">Criar empresa</h2>
      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <Field label="ID da empresa" name="tenant_id" placeholder="empresa-acme" required />
        <Field label="Empresa" name="company_name" placeholder="ACME Talent" required />
        <label className="grid gap-2 text-sm font-bold text-stone-700">
          Plano
          <select name="tier" defaultValue="starter" className="rounded-2xl border border-stone-200 bg-white px-4 py-3 font-medium text-stone-950 outline-none focus:border-amber-500 focus:ring-4 focus:ring-amber-100">
            <option value="starter">inicial</option>
            <option value="growth">crescimento</option>
            <option value="scale">escala</option>
          </select>
        </label>
        <Field label="Fuso horário" name="timezone" defaultValue="America/Sao_Paulo" />
        <Field label="Domínio principal" name="primary_domain" placeholder="empresa.com.br" />
      </div>
      <div className="mt-5 flex flex-wrap items-center gap-3">
        <SubmitButton>Criar empresa</SubmitButton>
        <ActionFeedback state={state} />
      </div>
    </form>
  );
}

export function CandidateCreateForm({ tenantId }: { tenantId: string }) {
  const [state, action] = useActionState(createCandidateAction, initialState);

  return (
    <form action={action} className="rounded-[2rem] border border-stone-200 bg-white/82 p-5 shadow-[0_24px_70px_rgba(41,37,36,0.08)] backdrop-blur">
      <input type="hidden" name="tenant_id" value={tenantId} />
      <p className="text-xs font-bold uppercase tracking-[0.24em] text-amber-700">Operação</p>
      <h2 className="mt-2 font-display text-2xl font-black tracking-[-0.04em]">Adicionar candidato</h2>
      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Field label="Nome" name="name" placeholder="Nome Sobrenome" required />
        <Field label="ID do candidato opcional" name="candidate_id" placeholder="candidate-empresa-001" />
        <Field label="Cidade" name="city" placeholder="Sao Paulo" />
        <Field label="E-mail" name="email" type="email" placeholder="talento@email.com" />
        <Field label="URL do LinkedIn" name="linkedin_url" placeholder="https://linkedin.com/in/..." />
      </div>
      <div className="mt-5 flex flex-wrap items-center gap-3">
        <SubmitButton>Enviar para o fluxo de vida</SubmitButton>
        <ActionFeedback state={state} />
      </div>
    </form>
  );
}

export function ApiKeyCreateForm({ tenantId }: { tenantId: string }) {
  const [state, action] = useActionState(createApiKeyAction, initialState);

  return (
    <form action={action} className="rounded-[2rem] border border-stone-200 bg-white/82 p-5 shadow-[0_24px_70px_rgba(41,37,36,0.08)] backdrop-blur">
      <input type="hidden" name="tenant_id" value={tenantId} />
      <p className="text-xs font-bold uppercase tracking-[0.24em] text-amber-700">Credenciais</p>
      <h2 className="mt-2 font-display text-2xl font-black tracking-[-0.04em]">Criar chave de API</h2>
      <div className="mt-5 grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
        <Field label="Rótulo" name="label" placeholder="producao-recrutador" defaultValue="default" />
        <SubmitButton>Criar chave</SubmitButton>
      </div>
      <div className="mt-4">
        <ActionFeedback state={state} />
      </div>
    </form>
  );
}

export function ApiKeyLifecycleForm({ tenantId }: { tenantId: string }) {
  const [revokeState, revokeAction] = useActionState(revokeApiKeyAction, initialState);
  const [rotateState, rotateAction] = useActionState(rotateApiKeyAction, initialState);

  return (
    <section className="grid gap-4 xl:grid-cols-2">
      <form action={revokeAction} className="rounded-[2rem] border border-stone-200 bg-white/82 p-5 shadow-[0_24px_70px_rgba(41,37,36,0.08)] backdrop-blur">
        <input type="hidden" name="tenant_id" value={tenantId} />
        <p className="text-xs font-bold uppercase tracking-[0.24em] text-rose-700">Revogar</p>
        <h2 className="mt-2 font-display text-2xl font-black tracking-[-0.04em]">Revogar chave de API</h2>
        <div className="mt-5 grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
          <Field label="ID da chave de API" name="api_key_id" placeholder="uuid-da-chave" required />
          <SubmitButton>Revogar</SubmitButton>
        </div>
        <div className="mt-4">
          <ActionFeedback state={revokeState} />
        </div>
      </form>

      <form action={rotateAction} className="rounded-[2rem] border border-stone-200 bg-white/82 p-5 shadow-[0_24px_70px_rgba(41,37,36,0.08)] backdrop-blur">
        <input type="hidden" name="tenant_id" value={tenantId} />
        <p className="text-xs font-bold uppercase tracking-[0.24em] text-amber-700">Rotacionar</p>
        <h2 className="mt-2 font-display text-2xl font-black tracking-[-0.04em]">Rotacionar chave de API</h2>
        <div className="mt-5 grid gap-4 md:grid-cols-3 md:items-end">
          <Field label="ID da chave de API" name="api_key_id" placeholder="uuid-da-chave" required />
          <Field label="Novo rótulo" name="label" placeholder="rotated" defaultValue="rotated" />
          <SubmitButton>Rotacionar</SubmitButton>
        </div>
        <div className="mt-4">
          <ActionFeedback state={rotateState} />
        </div>
      </form>
    </section>
  );
}
