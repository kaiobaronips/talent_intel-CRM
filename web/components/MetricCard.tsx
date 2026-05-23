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
    <article className="group relative overflow-hidden rounded-[2rem] border border-stone-200 bg-white/78 p-5 shadow-[0_24px_60px_rgba(41,37,36,0.08)] backdrop-blur">
      <div className={`absolute -right-8 -top-10 h-28 w-28 rounded-full bg-gradient-to-br ${accentMap[accent]} opacity-25 blur-2xl transition group-hover:scale-125`} />
      <p className="text-xs font-bold uppercase tracking-[0.22em] text-stone-500">{label}</p>
      <div className="mt-4 flex items-end justify-between gap-3">
        <strong className="font-display text-4xl tracking-[-0.05em] text-stone-950">{value}</strong>
        {detail ? <span className="pb-1 text-right text-xs font-medium text-stone-500">{detail}</span> : null}
      </div>
    </article>
  );
}
