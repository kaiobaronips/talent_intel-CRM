'use client';

import { useActionState } from 'react';
import { updateTenantMessageTemplatesAction, type ActionState } from '@/app/actions';
import type { Tenant } from '@/lib/types';

const initialState: ActionState = { ok: false, message: '' };

type TenantMessageTemplateFormProps = {
  tenant: Tenant;
};

function valueOf(value: unknown, fallback: string) {
  return typeof value === 'string' && value.trim().length > 0 ? value : fallback;
}

export function TenantMessageTemplateForm({ tenant }: TenantMessageTemplateFormProps) {
  const [state, action, pending] = useActionState(updateTenantMessageTemplatesAction, initialState);
  const templates = (tenant.metadata_json ?? tenant.metadata ?? {}).message_templates ?? {};

  return (
    <form action={action} className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
      <input type="hidden" name="tenant_id" value={tenant.id} />
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase text-amber-700">Biblioteca de mensagens</p>
          <h2 className="mt-2 font-display text-2xl font-black text-stone-950">Mensagens prontas para as automações</h2>
          <p className="mt-2 max-w-3xl text-sm font-medium leading-6 text-stone-600">
            Defina os textos base que os agentes poderão usar para e-mail e LinkedIn. Antes do envio real, cada mensagem continua passando por aprovação humana.
          </p>
        </div>
        <button type="submit" disabled={pending} className="rounded-lg bg-stone-950 px-5 py-3 text-sm font-black text-white transition hover:bg-stone-800 disabled:opacity-50">
          {pending ? 'Salvando...' : 'Salvar mensagens'}
        </button>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        <section className="rounded-lg bg-stone-50 p-4">
          <p className="text-xs font-bold uppercase text-stone-500">E-mail</p>
          <div className="mt-4 grid gap-3">
            <label className="grid gap-2 text-sm font-bold text-stone-700">
              Assunto inicial
              <input name="email_initial_subject" defaultValue={valueOf(templates.email_initial_subject, 'Convite para uma conversa rápida')} className="rounded-lg border border-stone-200 px-4 py-3" />
            </label>
            <label className="grid gap-2 text-sm font-bold text-stone-700">
              Mensagem inicial
              <textarea name="email_initial_body" rows={7} defaultValue={valueOf(templates.email_initial_body, 'Olá {{nome}}, tudo bem? Vi seu perfil e acredito que sua experiência em {{cargo}} pode ter aderência com uma oportunidade que estamos avaliando. Faz sentido conversarmos rapidamente esta semana?')} className="rounded-lg border border-stone-200 px-4 py-3 leading-6" />
            </label>
            <label className="grid gap-2 text-sm font-bold text-stone-700">
              Assunto follow-up 1
              <input name="email_follow_up_1_subject" defaultValue={valueOf(templates.email_follow_up_1_subject, 'Retomando meu contato')} className="rounded-lg border border-stone-200 px-4 py-3" />
            </label>
            <label className="grid gap-2 text-sm font-bold text-stone-700">
              Follow-up 1
              <textarea name="email_follow_up_1_body" rows={5} defaultValue={valueOf(templates.email_follow_up_1_body, 'Olá {{nome}}, passando para retomar meu contato anterior. Se fizer sentido para você, posso compartilhar mais contexto sobre a oportunidade.')} className="rounded-lg border border-stone-200 px-4 py-3 leading-6" />
            </label>
            <label className="grid gap-2 text-sm font-bold text-stone-700">
              Assunto follow-up 2
              <input name="email_follow_up_2_subject" defaultValue={valueOf(templates.email_follow_up_2_subject, 'Ainda faz sentido conversarmos?')} className="rounded-lg border border-stone-200 px-4 py-3" />
            </label>
            <label className="grid gap-2 text-sm font-bold text-stone-700">
              Follow-up 2
              <textarea name="email_follow_up_2_body" rows={5} defaultValue={valueOf(templates.email_follow_up_2_body, 'Olá {{nome}}, sei que a agenda pode estar corrida. Caso este tema faça sentido, posso te enviar um resumo objetivo da oportunidade.')} className="rounded-lg border border-stone-200 px-4 py-3 leading-6" />
            </label>
            <label className="grid gap-2 text-sm font-bold text-stone-700">
              Assunto follow-up 3
              <input name="email_follow_up_3_subject" defaultValue={valueOf(templates.email_follow_up_3_subject, 'Encerrando meu contato por enquanto')} className="rounded-lg border border-stone-200 px-4 py-3" />
            </label>
            <label className="grid gap-2 text-sm font-bold text-stone-700">
              Follow-up 3 despedida
              <textarea name="email_follow_up_3_body" rows={5} defaultValue={valueOf(templates.email_follow_up_3_body, 'Olá {{nome}}, este será meu último contato por enquanto. Se a conversa fizer sentido no futuro, fico à disposição para retomarmos. Obrigado.')} className="rounded-lg border border-stone-200 px-4 py-3 leading-6" />
            </label>
          </div>
        </section>

        <section className="rounded-lg bg-stone-50 p-4">
          <p className="text-xs font-bold uppercase text-stone-500">LinkedIn</p>
          <div className="mt-4 grid gap-3">
            <label className="grid gap-2 text-sm font-bold text-stone-700">
              Convite de conexão
              <textarea name="linkedin_connection_note" rows={4} defaultValue={valueOf(templates.linkedin_connection_note, 'Olá {{nome}}, vi sua trajetória em {{cargo}} e gostaria de me conectar.')} className="rounded-lg border border-stone-200 px-4 py-3 leading-6" />
            </label>
            <label className="grid gap-2 text-sm font-bold text-stone-700">
              Mensagem inicial LinkedIn
              <textarea name="linkedin_initial_message" rows={7} defaultValue={valueOf(templates.linkedin_initial_message, 'Olá {{nome}}, obrigado por conectar. Seu perfil chamou atenção pela experiência em {{cargo}}. Estou conduzindo uma busca que pode fazer sentido para seu momento. Podemos conversar rapidamente?')} className="rounded-lg border border-stone-200 px-4 py-3 leading-6" />
            </label>
            <label className="grid gap-2 text-sm font-bold text-stone-700">
              Follow-up LinkedIn
              <textarea name="linkedin_follow_up_message" rows={5} defaultValue={valueOf(templates.linkedin_follow_up_message, 'Olá {{nome}}, passando só para retomar minha mensagem. Se preferir, posso enviar um resumo da oportunidade por aqui.')} className="rounded-lg border border-stone-200 px-4 py-3 leading-6" />
            </label>
            <label className="grid gap-2 text-sm font-bold text-stone-700">
              Resposta quando houver interesse
              <textarea name="response_follow_up_message" rows={5} defaultValue={valueOf(templates.response_follow_up_message, 'Perfeito, {{nome}}. Obrigado pelo retorno. Vou te enviar mais contexto e sugerir alguns horários para conversarmos.')} className="rounded-lg border border-stone-200 px-4 py-3 leading-6" />
            </label>
          </div>
        </section>
      </div>

      <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm font-bold leading-6 text-amber-950">
        Variáveis disponíveis: {'{{nome}}'}, {'{{cargo}}'}, {'{{empresa}}'}, {'{{cidade}}'}, {'{{perfil_alvo}}'}.
      </div>

      {state.message ? (
        <p className={`mt-4 rounded-lg border px-3 py-2 text-sm font-bold ${state.ok ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-rose-200 bg-rose-50 text-rose-900'}`}>
          {state.message}
        </p>
      ) : null}
    </form>
  );
}
