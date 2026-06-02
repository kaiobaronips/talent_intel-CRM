'use client';

import { useActionState } from 'react';
import type { ActionState } from '@/app/actions';
import { createApiKeyAction, createCandidateAction, createTenantAction, revokeApiKeyAction, rotateApiKeyAction, searchApolloCandidatesAction } from '@/app/actions';

const initialState: ActionState = { ok: false, message: '' };

function SubmitButton({ children }: { children: React.ReactNode }) {
  return (
    <button type="submit" className="rounded-lg bg-stone-950 px-5 py-3 text-sm font-black text-stone-50 transition hover:bg-amber-700">
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
        className="rounded-lg border border-stone-200 bg-white px-4 py-3 font-medium text-stone-950 outline-none transition placeholder:text-stone-400 focus:border-amber-500 focus:ring-4 focus:ring-amber-100"
      />
    </label>
  );
}

function ActionFeedback({ state }: { state: ActionState }) {
  if (!state.message) {
    return null;
  }

  return (
    <div className={`rounded-lg border p-4 text-sm font-bold ${state.ok ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-rose-200 bg-rose-50 text-rose-900'}`}>
      <p>{state.message}</p>
      {state.secret ? <code className="mt-3 block overflow-x-auto rounded-lg bg-stone-950 p-3 font-monoish text-xs text-stone-50">{state.secret}</code> : null}
    </div>
  );
}

export function TenantCreateForm() {
  const [state, action] = useActionState(createTenantAction, initialState);

  return (
    <form action={action} className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-bold uppercase text-amber-700">Administração</p>
      <h2 className="mt-2 font-display text-2xl font-black">Cadastrar empresa cliente</h2>
      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <Field label="ID da empresa" name="tenant_id" placeholder="empresa-acme" required />
        <Field label="Empresa" name="company_name" placeholder="ACME Talent" required />
        <label className="grid gap-2 text-sm font-bold text-stone-700">
          Plano
          <select name="tier" defaultValue="starter" className="rounded-lg border border-stone-200 bg-white px-4 py-3 font-medium text-stone-950 outline-none focus:border-amber-500 focus:ring-4 focus:ring-amber-100">
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
    <form action={action} className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
      <input type="hidden" name="tenant_id" value={tenantId} />
      <p className="text-xs font-bold uppercase text-amber-700">Novo candidato</p>
      <h2 className="mt-2 font-display text-2xl font-black">Enviar perfil para análise dos agentes</h2>
      <p className="mt-2 max-w-3xl text-sm font-medium leading-6 text-stone-600">
        Informe os dados disponíveis. Os agentes avaliam aderência, preparam mensagens de abordagem e criam os próximos contatos por canal.
      </p>
      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Field label="Nome do candidato" name="name" placeholder="Nome Sobrenome" required />
        <Field label="Código interno opcional" name="candidate_id" placeholder="joao-silva-001" />
        <Field label="Cidade" name="city" placeholder="Sao Paulo" />
        <Field label="Estado" name="state" placeholder="SP" />
        <Field label="E-mail" name="email" type="email" placeholder="talento@email.com" />
        <Field label="Perfil do LinkedIn" name="linkedin_url" placeholder="https://linkedin.com/in/..." />
        <Field label="Cargo atual" name="current_role" placeholder="Executivo de contas" />
        <Field label="Empresa atual" name="current_company" placeholder="Empresa atual" />
        <Field label="Senioridade" name="seniority" placeholder="Pleno, senior, liderança" />
        <Field label="Perfil alvo" name="target_profile" placeholder="Vendas B2B, tecnologia, financeiro" />
      </div>
      <div className="mt-5 flex flex-wrap items-center gap-3">
        <SubmitButton>Iniciar análise dos agentes</SubmitButton>
        <ActionFeedback state={state} />
      </div>
    </form>
  );
}

export function ApolloCandidateSearchForm({ tenantId }: { tenantId: string }) {
  const [state, action] = useActionState(searchApolloCandidatesAction, initialState);

  return (
    <form action={action} className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
      <input type="hidden" name="tenant_id" value={tenantId} />
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase text-amber-700">Busca automática</p>
          <h2 className="mt-2 font-display text-2xl font-black">Buscar candidatos no Apollo.io</h2>
          <p className="mt-2 max-w-3xl text-sm font-medium leading-6 text-stone-600">
            Use esta busca para encontrar candidatos reais por cargo, região e palavras-chave. Os perfis encontrados entram na fila dos agentes para classificação e mensagens.
          </p>
        </div>
        <SubmitButton>Buscar no Apollo</SubmitButton>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Field label="Cargos buscados" name="target_roles" placeholder="Account Executive, SDR, Head Comercial" required />
        <Field label="Localização" name="locations" placeholder="São Paulo, Brasil, remoto" />
        <Field label="Senioridade" name="seniority" placeholder="Pleno, senior, liderança" />
        <Field label="Palavras-chave" name="keywords" placeholder="SaaS, outbound, enterprise, B2B" />
        <Field label="Setores" name="industries" placeholder="Software, serviços financeiros" />
        <Field label="Máximo de candidatos" name="max_candidates" type="number" defaultValue="10" />
      </div>
      <div className="mt-4">
        <ActionFeedback state={state} />
      </div>
    </form>
  );
}

export function ApiKeyCreateForm({ tenantId }: { tenantId: string }) {
  const [state, action] = useActionState(createApiKeyAction, initialState);

  return (
    <form action={action} className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
      <input type="hidden" name="tenant_id" value={tenantId} />
      <p className="text-xs font-bold uppercase text-amber-700">Integrações</p>
      <h2 className="mt-2 font-display text-2xl font-black">Criar chave de integração</h2>
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
      <form action={revokeAction} className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
        <input type="hidden" name="tenant_id" value={tenantId} />
        <p className="text-xs font-bold uppercase text-rose-700">Bloquear acesso</p>
        <h2 className="mt-2 font-display text-2xl font-black">Revogar chave de integração</h2>
        <div className="mt-5 grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
          <Field label="ID da chave de integração" name="api_key_id" placeholder="uuid-da-chave" required />
          <SubmitButton>Revogar</SubmitButton>
        </div>
        <div className="mt-4">
          <ActionFeedback state={revokeState} />
        </div>
      </form>

      <form action={rotateAction} className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
        <input type="hidden" name="tenant_id" value={tenantId} />
        <p className="text-xs font-bold uppercase text-amber-700">Renovar acesso</p>
        <h2 className="mt-2 font-display text-2xl font-black">Trocar chave de integração</h2>
        <div className="mt-5 grid gap-4 md:grid-cols-3 md:items-end">
          <Field label="ID da chave de integração" name="api_key_id" placeholder="uuid-da-chave" required />
          <Field label="Novo rótulo" name="label" placeholder="rotated" defaultValue="rotated" />
          <SubmitButton>Trocar chave</SubmitButton>
        </div>
        <div className="mt-4">
          <ActionFeedback state={rotateState} />
        </div>
      </form>
    </section>
  );
}
