const statusLabels: Record<string, string> = {
  active: 'Ativo',
  operational: 'Operacional',
  online: 'Online',
  connected: 'Conectado',
  ready: 'Pronto',
  pending: 'Aguardando contato',
  draft: 'Rascunho',
  approved: 'Aprovado para envio',
  sent: 'Mensagem enviada',
  replied: 'Resposta recebida',
  starter: 'Inicial',
  growth: 'Crescimento',
  scale: 'Escala',
  owner: 'Proprietário',
  admin: 'Administrador',
  recruiter: 'Recrutador',
  viewer: 'Leitor',
  contacted: 'Contato iniciado',
  enriched: 'Perfil enriquecido',
  qualified: 'Qualificado',
  closed: 'Encerrado',
  completed: 'Concluído',
  complete: 'Concluído',
  running: 'Em andamento',
  queued: 'Na fila',
  enfileirado: 'Na fila',
  failed: 'Falhou',
  erro: 'Erro',
  offline: 'Offline',
  paused: 'Pausado',
  discarded: 'Descartado',
  email: 'E-mail',
  linkedin: 'LinkedIn',
  a: 'Alta prioridade',
  b: 'Boa aderência',
  c: 'Baixa prioridade',
};

const workflowLabels: Record<string, string> = {
  CandidateLifecycle: 'Análise e contato do candidato',
  TenantOnboarding: 'Configuração da empresa',
};

const eventLabels: Record<string, string> = {
  'candidate.create_requested': 'Candidato enviado para analise',
  'candidate.lifecycle_completed': 'Análise do candidato concluída',
  'candidate_lifecycle.completed': 'Análise do candidato concluída',
  'tenant.onboarded': 'Empresa configurada',
  'tenant_api_key.created': 'Chave de integracao criada',
  'tenant_api_key.revoked': 'Chave de integracao revogada',
  'tenant_api_key.rotated': 'Chave de integracao renovada',
};

export function formatStatus(value?: string | number | null) {
  if (value === null || value === undefined || value === '') return 'Sem informação';
  const raw = String(value);
  return statusLabels[raw.toLowerCase()] ?? raw;
}

export function formatWorkflowName(value?: string | null) {
  if (!value) return 'Fluxo operacional';
  return workflowLabels[value] ?? value;
}

export function formatEventName(value?: string | null) {
  if (!value) return 'Evento registrado';
  return eventLabels[value] ?? value.replaceAll('_', ' ').replaceAll('.', ' ');
}

export function formatDateTime(value?: string | null) {
  if (!value) return 'Não informado';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: 'America/Sao_Paulo',
  }).format(date);
}

export function formatScore(value?: number | null) {
  if (value === null || value === undefined) return 'Sem nota';
  return `${value}/100`;
}

export function shortId(value?: string | null) {
  if (!value) return 'Não informado';
  if (value.length <= 18) return value;
  return `${value.slice(0, 8)}...${value.slice(-6)}`;
}
