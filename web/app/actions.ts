'use server';

import { cookies } from 'next/headers';
import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { apiMutation, getDefaultTenantId, reviewInteractionMessage, updateCandidateDecision, updateInteractionStatus, updateTenantMessageTemplates, updateTenantPreferences } from '@/lib/api';
import type { InteractionStatus } from '@/lib/types';
import { getSessionToken, refreshCookieName, sessionCookieName } from '@/lib/session';
import { authErrorMessage, requireSupabaseAuthConfig, revokeSupabaseSession, setSessionCookie, type SupabaseTokenPayload } from '@/lib/supabase-auth';

export type ActionState = {
  ok: boolean;
  message: string;
  secret?: string;
};

const initialError: ActionState = { ok: false, message: 'Formulário inválido.' };

function text(formData: FormData, key: string): string {
  return String(formData.get(key) ?? '').trim();
}

function revalidateTenantViews(tenantId: string) {
  revalidatePath('/');
  revalidatePath('/candidates');
  revalidatePath('/interactions');
  revalidatePath(`/tenants/${tenantId}`);
  revalidatePath('/settings');
}

function revalidateInteractionViews(tenantId: string, candidateId: string) {
  revalidateTenantViews(tenantId);
  revalidatePath(`/candidates/${candidateId}`);
}

async function authOptions() {
  const bearerToken = await getSessionToken();
  return bearerToken ? { bearerToken, apiKeyFallback: false } : { apiKeyFallback: false };
}

export async function loginAction(_previousState: ActionState, formData: FormData): Promise<ActionState> {
  const email = text(formData, 'email');
  const password = text(formData, 'password');
  const authConfig = requireSupabaseAuthConfig();

  if (!email || !password) {
    return { ...initialError, message: 'E-mail e senha são obrigatórios.' };
  }

  if (!authConfig.ok) {
    return { ok: false, message: authConfig.message };
  }

  const response = await fetch(`${authConfig.config.url}/auth/v1/token?grant_type=password`, {
    method: 'POST',
    headers: {
      apikey: authConfig.config.anonKey,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
    cache: 'no-store',
  });

  const payload = (await response.json().catch(() => ({}))) as SupabaseTokenPayload;
  if (!response.ok || !payload.access_token) {
    return { ok: false, message: authErrorMessage(payload) };
  }

  await setSessionCookie(payload);

  redirect('/');
}

export async function logoutAction(): Promise<void> {
  const token = await getSessionToken();
  await revokeSupabaseSession(token);
  const cookieStore = await cookies();
  cookieStore.delete(sessionCookieName);
  cookieStore.delete(refreshCookieName);
  redirect('/login');
}

export async function createTenantAction(_previousState: ActionState, formData: FormData): Promise<ActionState> {
  const tenantId = text(formData, 'tenant_id');
  const companyName = text(formData, 'company_name');
  const tier = text(formData, 'tier') || 'starter';
  const primaryDomain = text(formData, 'primary_domain');
  const timezone = text(formData, 'timezone') || 'America/Sao_Paulo';

  if (!tenantId || !companyName) {
    return { ...initialError, message: 'ID da empresa e nome da empresa são obrigatórios.' };
  }

  const result = await apiMutation<{ workflow_id: string; tenant_id: string }>('/v1/tenants', 'POST', {
    tenant_id: tenantId,
    company_name: companyName,
    tier,
    primary_domain: primaryDomain,
    timezone,
  }, await authOptions());

  if (!result.ok) {
    return { ok: false, message: result.message };
  }

  revalidateTenantViews(tenantId);
  return { ok: true, message: `Empresa ${tenantId} cadastrada e enviada para configuração inicial.` };
}

export async function createCandidateAction(_previousState: ActionState, formData: FormData): Promise<ActionState> {
  const tenantId = text(formData, 'tenant_id') || getDefaultTenantId();
  const name = text(formData, 'name');
  const email = text(formData, 'email');
  const linkedinUrl = text(formData, 'linkedin_url');
  const city = text(formData, 'city');
  const candidateId = text(formData, 'candidate_id');
  const currentRole = text(formData, 'current_role');
  const currentCompany = text(formData, 'current_company');
  const seniority = text(formData, 'seniority');
  const targetProfile = text(formData, 'target_profile');
  const state = text(formData, 'state');

  if (!name) {
    return { ...initialError, message: 'O nome do candidato é obrigatório.' };
  }

  if (!email && !linkedinUrl) {
    return { ...initialError, message: 'Informe e-mail ou LinkedIn para iniciar o contato.' };
  }

  const result = await apiMutation<{ workflow_id: string; candidate_id: string; channels: string[] }>('/v1/candidates', 'POST', {
    tenant_id: tenantId,
    candidate_id: candidateId || undefined,
    name,
    city,
    email,
    linkedin_url: linkedinUrl,
    current_role: currentRole,
    current_company: currentCompany,
    seniority,
    target_profile: targetProfile,
    state,
  }, await authOptions());

  if (!result.ok) {
    return { ok: false, message: result.message };
  }

  revalidateTenantViews(tenantId);
  return { ok: true, message: `Candidato ${result.data?.candidate_id ?? name} enviado para análise dos agentes.` };
}

export async function searchApolloCandidatesAction(_previousState: ActionState, formData: FormData): Promise<ActionState> {
  const tenantId = text(formData, 'tenant_id') || getDefaultTenantId();
  const maxCandidates = Number(text(formData, 'max_candidates') || 10);

  const result = await apiMutation<{
    configured: boolean;
    created: { candidate_id: string }[];
    duplicates: string[];
    skipped: { name: string; reason: string }[];
    message: string;
  }>(
    `/v1/tenants/${tenantId}/sourcing/apollo/search`,
    'POST',
    {
      target_roles: text(formData, 'target_roles'),
      locations: text(formData, 'locations'),
      seniority: text(formData, 'seniority'),
      keywords: text(formData, 'keywords'),
      industries: text(formData, 'industries'),
      max_candidates: Number.isFinite(maxCandidates) ? maxCandidates : 10,
    },
    await authOptions(),
  );

  if (!result.ok) {
    return { ok: false, message: result.message };
  }

  revalidateTenantViews(tenantId);
  if (result.data?.configured === false) {
    return { ok: false, message: result.data.message };
  }

  const created = result.data?.created.length ?? 0;
  const duplicates = result.data?.duplicates.length ?? 0;
  const skipped = result.data?.skipped.length ?? 0;
  return {
    ok: true,
    message: `Apollo retornou ${created} candidato(s) enviados aos agentes. Duplicados: ${duplicates}. Sem canal útil: ${skipped}.`,
  };
}

export async function createApiKeyAction(_previousState: ActionState, formData: FormData): Promise<ActionState> {
  const tenantId = text(formData, 'tenant_id') || getDefaultTenantId();
  const label = text(formData, 'label') || 'default';

  const result = await apiMutation<{ api_key: string; key: { id: string; label?: string } }>(`/v1/tenants/${tenantId}/api-keys`, 'POST', { label }, await authOptions());

  if (!result.ok) {
    return { ok: false, message: result.message };
  }

  revalidateTenantViews(tenantId);
  return {
    ok: true,
    message: `Chave ${result.data?.key?.id ?? label} criada. Guarde agora: ela não será exibida novamente.`,
    secret: result.data?.api_key,
  };
}

export async function revokeApiKeyAction(_previousState: ActionState, formData: FormData): Promise<ActionState> {
  const tenantId = text(formData, 'tenant_id') || getDefaultTenantId();
  const keyId = text(formData, 'api_key_id');

  if (!keyId) {
    return { ...initialError, message: 'O ID da chave de integração é obrigatório.' };
  }

  const result = await apiMutation<{ tenant_id: string }>(`/v1/tenants/${tenantId}/api-keys/${keyId}`, 'DELETE', undefined, await authOptions());

  if (!result.ok) {
    return { ok: false, message: result.message };
  }

  revalidateTenantViews(tenantId);
  return { ok: true, message: `Chave ${keyId} revogada.` };
}

export async function rotateApiKeyAction(_previousState: ActionState, formData: FormData): Promise<ActionState> {
  const tenantId = text(formData, 'tenant_id') || getDefaultTenantId();
  const keyId = text(formData, 'api_key_id');
  const label = text(formData, 'label') || 'rotated';

  if (!keyId) {
    return { ...initialError, message: 'O ID da chave de integração é obrigatório.' };
  }

  const result = await apiMutation<{ api_key: string; key: { id: string } }>(`/v1/tenants/${tenantId}/api-keys/${keyId}/rotate`, 'POST', { label }, await authOptions());

  if (!result.ok) {
    return { ok: false, message: result.message };
  }

  revalidateTenantViews(tenantId);
  return {
    ok: true,
    message: `Chave ${keyId} trocada. Guarde a nova chave agora.`,
    secret: result.data?.api_key,
  };
}


export async function upsertMembershipAction(_previousState: ActionState, formData: FormData): Promise<ActionState> {
  const tenantId = text(formData, 'tenant_id') || getDefaultTenantId();
  const userId = text(formData, 'user_id');
  const email = text(formData, 'email');
  const role = text(formData, 'role') || 'viewer';

  if (!userId && !email) {
    return { ...initialError, message: 'Informe o e-mail ou o ID do usuário.' };
  }

  const result = await apiMutation<{ membership: { id: string; role: string } }>(`/v1/tenants/${tenantId}/memberships`, 'POST', {
    user_id: userId,
    email,
    role,
  }, await authOptions());

  if (!result.ok) {
    return { ok: false, message: result.message };
  }

  revalidatePath('/members');
  revalidatePath(`/tenants/${tenantId}`);
  return { ok: true, message: `Membro ${email || userId} salvo como ${result.data?.membership?.role ?? role}.` };
}

export async function deleteMembershipAction(_previousState: ActionState, formData: FormData): Promise<ActionState> {
  const tenantId = text(formData, 'tenant_id') || getDefaultTenantId();
  const membershipId = text(formData, 'membership_id');

  if (!membershipId) {
    return { ...initialError, message: 'O ID da associação é obrigatório.' };
  }

  const result = await apiMutation<{ membership: { id: string } }>(`/v1/tenants/${tenantId}/memberships/${membershipId}`, 'DELETE', undefined, await authOptions());

  if (!result.ok) {
    return { ok: false, message: result.message };
  }

  revalidatePath('/members');
  revalidatePath(`/tenants/${tenantId}`);
  return { ok: true, message: `Membro ${membershipId} removido.` };
}

export async function updateInteractionStatusAction(_previousState: ActionState, formData: FormData): Promise<ActionState> {
  const tenantId = text(formData, 'tenant_id') || getDefaultTenantId();
  const candidateId = text(formData, 'candidate_id');
  const interactionId = text(formData, 'interaction_id');
  const status = text(formData, 'status') as InteractionStatus;
  const responseReceived = text(formData, 'response_received');

  if (!interactionId || !candidateId || !status) {
    return { ...initialError, message: 'Contato inválido para atualização.' };
  }

  const result = await updateInteractionStatus(interactionId, status, responseReceived, await authOptions());
  if (!result.ok) {
    return { ok: false, message: result.message };
  }

  revalidateInteractionViews(tenantId, candidateId);
  const label = status === 'sent' ? 'Mensagem marcada como enviada.' : status === 'replied' ? 'Resposta registrada.' : 'Contato atualizado.';
  return { ok: true, message: label };
}

export async function reviewInteractionMessageAction(_previousState: ActionState, formData: FormData): Promise<ActionState> {
  const tenantId = text(formData, 'tenant_id') || getDefaultTenantId();
  const candidateId = text(formData, 'candidate_id');
  const interactionId = text(formData, 'interaction_id');
  const messageSent = text(formData, 'message_sent');
  const decisionNote = text(formData, 'decision_note');
  const status = (text(formData, 'status') || 'approved') as 'draft' | 'pending' | 'approved';

  if (!interactionId || !candidateId || !messageSent) {
    return { ...initialError, message: 'Informe a mensagem revisada antes de aprovar.' };
  }

  const result = await reviewInteractionMessage(interactionId, status, messageSent, decisionNote, await authOptions());
  if (!result.ok) {
    return { ok: false, message: result.message };
  }

  revalidateInteractionViews(tenantId, candidateId);
  return { ok: true, message: status === 'approved' ? 'Mensagem aprovada para envio.' : 'Mensagem salva como rascunho.' };
}

export async function updateCandidateDecisionAction(_previousState: ActionState, formData: FormData): Promise<ActionState> {
  const tenantId = text(formData, 'tenant_id') || getDefaultTenantId();
  const candidateId = text(formData, 'candidate_id');
  const decision = text(formData, 'decision') as 'active' | 'paused' | 'discarded';
  const decisionNote = text(formData, 'decision_note');

  if (!candidateId || !decision) {
    return { ...initialError, message: 'Decisão inválida para o candidato.' };
  }

  const result = await updateCandidateDecision(candidateId, decision, decisionNote, await authOptions());
  if (!result.ok) {
    return { ok: false, message: result.message };
  }

  revalidateTenantViews(tenantId);
  revalidatePath(`/candidates/${candidateId}`);
  const label = decision === 'paused' ? 'Candidato pausado.' : decision === 'discarded' ? 'Candidato descartado.' : 'Candidato reativado.';
  return { ok: true, message: label };
}

export async function updateTenantPreferencesAction(_previousState: ActionState, formData: FormData): Promise<ActionState> {
  const tenantId = text(formData, 'tenant_id') || getDefaultTenantId();
  const allowedChannels = ['email', 'linkedin'].filter((channel) => formData.get(`allowed_${channel}`) === 'on');
  const result = await updateTenantPreferences(
    tenantId,
    {
      target_roles: text(formData, 'target_roles'),
      seniority: text(formData, 'seniority'),
      locations: text(formData, 'locations'),
      keywords: text(formData, 'keywords'),
      allowed_channels: allowedChannels,
      outreach_tone: text(formData, 'outreach_tone'),
      daily_contact_limit: Number(text(formData, 'daily_contact_limit') || 20),
      max_attempts_per_candidate: Number(text(formData, 'max_attempts_per_candidate') || 3),
      follow_up_interval_days: Number(text(formData, 'follow_up_interval_days') || 5),
      require_manual_approval: formData.get('require_manual_approval') === 'on',
      linkedin_enabled: formData.get('linkedin_enabled') === 'on',
      email_enabled: formData.get('email_enabled') === 'on',
    },
    await authOptions(),
  );

  if (!result.ok) {
    return { ok: false, message: result.message };
  }

  revalidateTenantViews(tenantId);
  return { ok: true, message: 'Preferências da empresa salvas.' };
}

export async function updateTenantMessageTemplatesAction(_previousState: ActionState, formData: FormData): Promise<ActionState> {
  const tenantId = text(formData, 'tenant_id') || getDefaultTenantId();
  const result = await updateTenantMessageTemplates(
    tenantId,
    {
      email_initial_subject: text(formData, 'email_initial_subject'),
      email_initial_body: text(formData, 'email_initial_body'),
      email_follow_up_1_subject: text(formData, 'email_follow_up_1_subject'),
      email_follow_up_1_body: text(formData, 'email_follow_up_1_body'),
      email_follow_up_2_subject: text(formData, 'email_follow_up_2_subject'),
      email_follow_up_2_body: text(formData, 'email_follow_up_2_body'),
      email_follow_up_3_subject: text(formData, 'email_follow_up_3_subject'),
      email_follow_up_3_body: text(formData, 'email_follow_up_3_body'),
      linkedin_connection_note: text(formData, 'linkedin_connection_note'),
      linkedin_initial_message: text(formData, 'linkedin_initial_message'),
      linkedin_follow_up_message: text(formData, 'linkedin_follow_up_message'),
      response_follow_up_message: text(formData, 'response_follow_up_message'),
    },
    await authOptions(),
  );

  if (!result.ok) {
    return { ok: false, message: result.message };
  }

  revalidateTenantViews(tenantId);
  return { ok: true, message: 'Mensagens da automação salvas.' };
}
