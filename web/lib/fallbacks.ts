import type { ApiKey, Candidate, Interaction, Paginated, Tenant, TenantMetrics } from './types';

export const defaultTenantId = process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID ?? 'api-controlled-003';

export const fallbackTenant: Tenant = {
  id: defaultTenantId,
  company_name: 'Talent Intel CRM',
  slug: 'controlled-demo',
  tier: 'scale',
  timezone: 'America/Sao_Paulo',
  status: 'operational',
};

export const fallbackCandidates: Paginated<Candidate> = {
  items: [
    {
      id: 'candidate-sample-001',
      name: 'Adalberto Neto',
      email: 'adalberto@example.com',
      linkedin_url: 'https://linkedin.com/in/adalberto',
      city: 'Sao Paulo',
      state: 'SP',
      current_role: 'Assessor de Investimentos',
      current_company: 'XPTO Advisory',
      target_profile: 'Financeiro comercial',
      seniority: 'Senior',
      classification: 'A',
      score_overall: 86,
      stage: 'contacted',
    },
    {
      id: 'candidate-sample-002',
      name: 'Mariana Costa',
      email: null,
      linkedin_url: 'https://linkedin.com/in/mariana',
      city: 'Curitiba',
      state: 'PR',
      current_role: 'Financial Advisor',
      current_company: 'Private Office',
      target_profile: 'Hunter financeiro',
      seniority: 'Pleno',
      classification: 'B',
      score_overall: 74,
      stage: 'enriched',
    },
  ],
  pagination: { page: 1, limit: 20, total: 2, pages: 1 },
};

export const fallbackInteractions: Paginated<Interaction> = {
  items: [
    {
      id: 'interaction-sample-001',
      candidate_id: 'candidate-sample-001',
      candidate_name: 'Adalberto Neto',
      channel: 'linkedin',
      interaction_status: 'Enfileirado',
      next_action: 'Aguardando execucao',
      message_sent: 'Convite curto preparado',
    },
    {
      id: 'interaction-sample-002',
      candidate_id: 'candidate-sample-002',
      candidate_name: 'Mariana Costa',
      channel: 'email',
      interaction_status: 'Enfileirado',
      next_action: 'Enviar D0',
      message_sent: 'Mensagem inicial preparada',
    },
  ],
  pagination: { page: 1, limit: 20, total: 2, pages: 1 },
};

export const fallbackMetrics: TenantMetrics = {
  workflow_runs: { completed: 2, running: 0, failed: 0, total: 2 },
  interaction_counts: [
    { channel: 'linkedin', status: 'queued', total: 1 },
    { channel: 'email', status: 'queued', total: 1 },
  ],
  channel_backlog: [
    { channel: 'linkedin', pending: 1 },
    { channel: 'email', pending: 1 },
  ],
};

export const fallbackApiKeys: ApiKey[] = [
  { id: 'sample-key-readonly', name: 'Demo read-only key', status: 'active' },
];
