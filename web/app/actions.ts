'use server';

import { revalidatePath } from 'next/cache';
import { apiMutation, getDefaultTenantId } from '@/lib/api';

export type ActionState = {
  ok: boolean;
  message: string;
  secret?: string;
};

const initialError: ActionState = { ok: false, message: 'Formulario invalido.' };

function text(formData: FormData, key: string): string {
  return String(formData.get(key) ?? '').trim();
}

function revalidateTenantViews(tenantId: string) {
  revalidatePath('/');
  revalidatePath('/candidates');
  revalidatePath('/interactions');
  revalidatePath(`/tenants/${tenantId}`);
}

export async function createTenantAction(_previousState: ActionState, formData: FormData): Promise<ActionState> {
  const tenantId = text(formData, 'tenant_id');
  const companyName = text(formData, 'company_name');
  const tier = text(formData, 'tier') || 'starter';
  const primaryDomain = text(formData, 'primary_domain');
  const timezone = text(formData, 'timezone') || 'America/Sao_Paulo';

  if (!tenantId || !companyName) {
    return { ...initialError, message: 'Tenant ID e empresa sao obrigatorios.' };
  }

  const result = await apiMutation<{ workflow_id: string; tenant_id: string }>('/v1/tenants', 'POST', {
    tenant_id: tenantId,
    company_name: companyName,
    tier,
    primary_domain: primaryDomain,
    timezone,
  });

  if (!result.ok) {
    return { ok: false, message: result.message };
  }

  revalidateTenantViews(tenantId);
  return { ok: true, message: `Tenant ${tenantId} enviado para onboarding.` };
}

export async function createCandidateAction(_previousState: ActionState, formData: FormData): Promise<ActionState> {
  const tenantId = text(formData, 'tenant_id') || getDefaultTenantId();
  const name = text(formData, 'name');
  const email = text(formData, 'email');
  const linkedinUrl = text(formData, 'linkedin_url');
  const city = text(formData, 'city');
  const candidateId = text(formData, 'candidate_id');

  if (!name) {
    return { ...initialError, message: 'Nome do candidato e obrigatorio.' };
  }

  if (!email && !linkedinUrl) {
    return { ...initialError, message: 'Informe e-mail ou LinkedIn para iniciar cadencia.' };
  }

  const result = await apiMutation<{ workflow_id: string; candidate_id: string; channels: string[] }>('/v1/candidates', 'POST', {
    tenant_id: tenantId,
    candidate_id: candidateId || undefined,
    name,
    city,
    email,
    linkedin_url: linkedinUrl,
  });

  if (!result.ok) {
    return { ok: false, message: result.message };
  }

  revalidateTenantViews(tenantId);
  return { ok: true, message: `Candidato ${result.data?.candidate_id ?? name} enviado para lifecycle.` };
}

export async function createApiKeyAction(_previousState: ActionState, formData: FormData): Promise<ActionState> {
  const tenantId = text(formData, 'tenant_id') || getDefaultTenantId();
  const label = text(formData, 'label') || 'default';

  const result = await apiMutation<{ api_key: string; key: { id: string; label?: string } }>(`/v1/tenants/${tenantId}/api-keys`, 'POST', { label });

  if (!result.ok) {
    return { ok: false, message: result.message };
  }

  revalidateTenantViews(tenantId);
  return {
    ok: true,
    message: `Chave ${result.data?.key?.id ?? label} criada. Copie agora: ela nao sera exibida novamente.`,
    secret: result.data?.api_key,
  };
}

export async function revokeApiKeyAction(_previousState: ActionState, formData: FormData): Promise<ActionState> {
  const tenantId = text(formData, 'tenant_id') || getDefaultTenantId();
  const keyId = text(formData, 'api_key_id');

  if (!keyId) {
    return { ...initialError, message: 'API key ID obrigatoria.' };
  }

  const result = await apiMutation<{ tenant_id: string }>(`/v1/tenants/${tenantId}/api-keys/${keyId}`, 'DELETE');

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
    return { ...initialError, message: 'API key ID obrigatoria.' };
  }

  const result = await apiMutation<{ api_key: string; key: { id: string } }>(`/v1/tenants/${tenantId}/api-keys/${keyId}/rotate`, 'POST', { label });

  if (!result.ok) {
    return { ok: false, message: result.message };
  }

  revalidateTenantViews(tenantId);
  return {
    ok: true,
    message: `Chave ${keyId} rotacionada. Copie a nova chave agora.`,
    secret: result.data?.api_key,
  };
}
