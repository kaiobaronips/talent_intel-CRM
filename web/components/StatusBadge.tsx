import clsx from 'clsx';
import { formatStatus } from '@/lib/format';

const toneByValue: Record<string, string> = {
  active: 'border-emerald-300 bg-emerald-50 text-emerald-800',
  operational: 'border-emerald-300 bg-emerald-50 text-emerald-800',
  online: 'border-emerald-300 bg-emerald-50 text-emerald-800',
  connected: 'border-emerald-300 bg-emerald-50 text-emerald-800',
  ready: 'border-emerald-300 bg-emerald-50 text-emerald-800',
  pending: 'border-amber-300 bg-amber-50 text-amber-900',
  sent: 'border-blue-300 bg-blue-50 text-blue-800',
  replied: 'border-emerald-300 bg-emerald-50 text-emerald-800',
  closed: 'border-stone-300 bg-stone-100 text-stone-800',
  contacted: 'border-blue-300 bg-blue-50 text-blue-800',
  enriched: 'border-amber-300 bg-amber-50 text-amber-900',
  completed: 'border-emerald-300 bg-emerald-50 text-emerald-800',
  queued: 'border-sky-300 bg-sky-50 text-sky-800',
  enfileirado: 'border-sky-300 bg-sky-50 text-sky-800',
  running: 'border-sky-300 bg-sky-50 text-sky-800',
  failed: 'border-rose-300 bg-rose-50 text-rose-800',
  erro: 'border-rose-300 bg-rose-50 text-rose-800',
  offline: 'border-rose-300 bg-rose-50 text-rose-800',
};

const labelByValue: Record<string, string> = {
  active: 'Ativo',
  operational: 'Operacional',
  online: 'Online',
  connected: 'Conectado',
  ready: 'Pronto',
  pending: 'Pendente',
  sent: 'Mensagem enviada',
  replied: 'Resposta recebida',
  closed: 'Encerrado',
  starter: 'Inicial',
  growth: 'Crescimento',
  scale: 'Escala',
  owner: 'Proprietário',
  admin: 'Administrador',
  recruiter: 'Recrutador',
  viewer: 'Leitor',
  contacted: 'Contatado',
  enriched: 'Enriquecido',
  completed: 'Concluído',
  complete: 'Concluído',
  running: 'Em execução',
  'in progress': 'Em execução',
  queued: 'Na fila',
  enfileirado: 'Enfileirado',
  failed: 'Falhou',
  erro: 'Erro',
  offline: 'Offline',
};

type StatusBadgeProps = {
  value?: string | number | null;
  label?: string;
  className?: string;
};

export function StatusBadge({ value, label, className }: StatusBadgeProps) {
  const text = label ?? String(value ?? 'Sem informação');
  const key = text.toLowerCase();
  const translated = label ?? labelByValue[key] ?? formatStatus(text);

  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold',
        toneByValue[key] ?? 'border-stone-300 bg-stone-100 text-stone-800',
        className,
      )}
    >
      {translated}
    </span>
  );
}
