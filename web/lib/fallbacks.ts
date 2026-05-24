import type { ApiKey, AuditEvent, Candidate, Interaction, Paginated, Tenant, TenantMembership, TenantMetrics, WorkflowRun } from './types';

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
      current_company: 'XPTO Assessoria',
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
      current_role: 'Consultor Financeiro',
      current_company: 'Escritório Privado',
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
      next_action: 'Aguardando execução',
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
  { id: 'sample-key-readonly', name: 'Chave de leitura da demonstração', status: 'active' },
];

export const fallbackAuditEvents: Paginated<AuditEvent> = {
  items: [
    {
      id: 'audit-sample-001',
      tenant_id: defaultTenantId,
      candidate_id: 'candidate-sample-001',
      event_type: 'candidate.lifecycle_completed',
      actor_type: 'system',
      actor_id: 'temporal-worker',
    },
  ],
  pagination: { page: 1, limit: 20, total: 1, pages: 1 },
};

export const fallbackMemberships: TenantMembership[] = [
  { id: 'member-sample-001', tenant_id: defaultTenantId, user_id: 'owner-demo', email: 'owner@example.com', role: 'owner' },
];

export const fallbackWorkflowRuns: Paginated<WorkflowRun> = {
  items: [
    {
      id: 'workflow-sample-001',
      tenant_id: defaultTenantId,
      candidate_id: 'candidate-sample-001',
      workflow_name: 'Fluxo de vida do candidato',
      workflow_id: 'candidate-lifecycle::demo',
      run_id: 'run-sample-001',
      status: 'Completed',
    },
  ],
  pagination: { page: 1, limit: 20, total: 1, pages: 1 },
};

export const fallbackTenants: Paginated<Tenant> = {
  items: [fallbackTenant],
  pagination: { page: 1, limit: 20, total: 1, pages: 1 },
};
