import clsx from 'clsx';

const toneByValue: Record<string, string> = {
  active: 'border-emerald-300 bg-emerald-50 text-emerald-800',
  operational: 'border-emerald-300 bg-emerald-50 text-emerald-800',
  contacted: 'border-blue-300 bg-blue-50 text-blue-800',
  enriched: 'border-amber-300 bg-amber-50 text-amber-900',
  queued: 'border-sky-300 bg-sky-50 text-sky-800',
  enfileirado: 'border-sky-300 bg-sky-50 text-sky-800',
  failed: 'border-rose-300 bg-rose-50 text-rose-800',
  erro: 'border-rose-300 bg-rose-50 text-rose-800',
};

type StatusBadgeProps = {
  value?: string | number | null;
  label?: string;
  className?: string;
};

export function StatusBadge({ value, label, className }: StatusBadgeProps) {
  const text = label ?? String(value ?? 'sem status');
  const key = text.toLowerCase();

  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold tracking-[0.02em]',
        toneByValue[key] ?? 'border-stone-300 bg-stone-100 text-stone-800',
        className,
      )}
    >
      {text}
    </span>
  );
}
