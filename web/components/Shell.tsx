import type { ReactNode } from 'react';
import Link from 'next/link';
import clsx from 'clsx';
import { getDefaultTenantId } from '@/lib/api';

const navItems = [
  { href: '/', label: 'Control Tower' },
  { href: `/tenants/${getDefaultTenantId()}`, label: 'Tenant' },
  { href: '/candidates', label: 'Candidatos' },
  { href: '/interactions', label: 'Interacoes' },
];

type ShellProps = {
  children: ReactNode;
  offline?: boolean;
  title?: string;
  subtitle?: string;
};

export function Shell({ children, offline = false, title = 'Talent Intel CRM', subtitle }: ShellProps) {
  return (
    <div className="min-h-screen overflow-hidden bg-[var(--surface)] text-stone-950">
      <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(circle_at_15%_15%,rgba(250,204,21,0.22),transparent_28%),radial-gradient(circle_at_80%_0%,rgba(45,212,191,0.18),transparent_26%),linear-gradient(135deg,#fff7ed_0%,#f8fafc_48%,#ecfeff_100%)]" />
      <div className="pointer-events-none fixed inset-0 -z-10 opacity-[0.18] [background-image:linear-gradient(#292524_1px,transparent_1px),linear-gradient(90deg,#292524_1px,transparent_1px)] [background-size:42px_42px]" />

      <aside className="fixed left-4 top-4 z-20 hidden h-[calc(100vh-2rem)] w-72 rounded-[2.2rem] border border-stone-200 bg-white/72 p-5 shadow-[0_24px_80px_rgba(41,37,36,0.1)] backdrop-blur-xl lg:block">
        <Link href="/" className="block rounded-[1.6rem] bg-stone-950 p-5 text-stone-50">
          <p className="text-xs font-bold uppercase tracking-[0.26em] text-amber-200">SaaS Ops</p>
          <h1 className="mt-4 font-display text-3xl font-black leading-none tracking-[-0.06em]">Talent Intel CRM</h1>
        </Link>

        <nav className="mt-6 space-y-2">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center justify-between rounded-2xl px-4 py-3 text-sm font-bold text-stone-700 transition hover:bg-amber-100 hover:text-stone-950"
            >
              {item.label}
              <span className="h-2 w-2 rounded-full bg-stone-300" />
            </Link>
          ))}
        </nav>

        <div className="absolute bottom-5 left-5 right-5 rounded-[1.5rem] border border-stone-200 bg-stone-50 p-4">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-stone-500">API</p>
          <div className="mt-2 flex items-center gap-2 text-sm font-bold">
            <span className={clsx('h-2.5 w-2.5 rounded-full', offline ? 'bg-amber-500' : 'bg-emerald-500')} />
            {offline ? 'Modo demonstracao' : 'Conectada'}
          </div>
        </div>
      </aside>

      <main className="px-4 py-4 lg:ml-80 lg:px-8 lg:py-8">
        <header className="reveal mb-8 rounded-[2.4rem] border border-stone-200 bg-white/70 p-5 shadow-[0_24px_80px_rgba(41,37,36,0.08)] backdrop-blur-xl lg:p-8">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-amber-700">Commercial HR Intelligence</p>
              <h1 className="mt-3 max-w-4xl font-display text-4xl font-black leading-[0.95] tracking-[-0.07em] text-stone-950 lg:text-6xl">{title}</h1>
              {subtitle ? <p className="mt-4 max-w-2xl text-base font-medium leading-7 text-stone-600">{subtitle}</p> : null}
            </div>
            <div className="rounded-full border border-stone-200 bg-stone-50 px-4 py-2 text-sm font-bold text-stone-700">
              {offline ? 'Dados locais/fallback' : 'Dados reais da API'}
            </div>
          </div>
        </header>

        <div className="space-y-6">{children}</div>
      </main>
    </div>
  );
}
