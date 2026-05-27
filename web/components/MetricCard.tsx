type MetricCardProps = {
  label: string;
  value: string | number;
  detail?: string;
  accent?: 'green' | 'blue' | 'amber' | 'ink';
};

const accentMap = {
  green: 'from-emerald-400 to-lime-200',
  blue: 'from-sky-400 to-cyan-200',
  amber: 'from-amber-400 to-orange-200',
  ink: 'from-stone-900 to-stone-500',
};

export function MetricCard({ label, value, detail, accent = 'ink' }: MetricCardProps) {
  return (
    <article className="relative overflow-hidden rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
      <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${accentMap[accent]}`} />
      <p className="text-xs font-bold uppercase text-stone-500">{label}</p>
      <div className="mt-3 flex items-end justify-between gap-3">
        <strong className="font-display text-3xl font-black text-stone-950">{value}</strong>
        {detail ? <span className="pb-1 text-right text-xs font-medium leading-5 text-stone-500">{detail}</span> : null}
      </div>
    </article>
  );
}
